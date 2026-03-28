"""
Three-agent pipeline: Rewriter → RAG → Critique.
Each agent has its own system prompt, tools, and tool-use loop.
"""

import anthropic
import rag
import store

_client = None
MODEL = "claude-haiku-4-5-20251001"


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _extract_text(response) -> str:
    return "".join(b.text for b in response.content if hasattr(b, "text"))


# ── Agent 1: Rewriter ────────────────────────────────────────────────────────

REWRITER_SYSTEM = """You are a query rewriting agent for a RAG system. Your goal is to produce the best possible search query for retrieving relevant document chunks.

You have a tool called `expand_query` that generates multiple search query variations from a seed query. Use it to explore different angles of the user's question.

Workflow:
1. Analyze the user's question
2. Call expand_query with an initial seed based on the user's question
3. Review the variations returned
4. Either call expand_query again with a refined seed if the variations aren't good enough, or stop and output your final chosen search query

When you're satisfied, respond with ONLY the final search query text — nothing else."""

REWRITER_TOOLS = [
    {
        "name": "expand_query",
        "description": (
            "Generate multiple search query variations from a seed query. "
            "Returns 3-5 alternative phrasings optimized for semantic search."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "seed": {
                    "type": "string",
                    "description": "The seed query to expand into variations",
                }
            },
            "required": ["seed"],
        },
    }
]


def _expand_query_tool(seed: str) -> str:
    """Generate query variations via a lightweight LLM call."""
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=200,
        system=(
            "Generate 3-5 semantically diverse search query variations for a RAG system. "
            "Each variation should approach the topic from a different angle. "
            "Return one variation per line, nothing else."
        ),
        messages=[{"role": "user", "content": seed}],
    )
    return response.content[0].text.strip()


def rewrite_query(user_message: str) -> str:
    """Rewriter agent with expand_query tool loop."""
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):  # max iterations
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=300,
            system=REWRITER_SYSTEM,
            tools=REWRITER_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return _extract_text(response).strip()

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use" or block.name != "expand_query":
                    continue
                variations = _expand_query_tool(block.input["seed"])
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     variations,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    # Fallback: return original message if loop exits unexpectedly
    return user_message


# ── Agent 2: RAG ──────────────────────────────────────────────────────────────

RAG_SYSTEM_TEMPLATE = """Du är en research-assistent som hjälper användaren att söka i och förstå uppladdade dokument. Dokumenten kan handla om vad som helst — teknik, matematik, vetenskap, historia, eller annat.

Svara på samma språk som användaren skriver på. Var kortfattad och tydlig.

VIKTIGT: Användaren har följande dokument uppladdade:
{doc_list}

Du MÅSTE alltid anropa search_documents när användaren ställer en fråga. Gör ALDRIG antaganden om att dokument saknas — anropa verktyget först.
Citera alltid källan i svaret: "(sida X i [filnamn])".
Om sökningen inte hittar något relevant — säg det direkt."""

RAG_TOOLS = [
    {
        "name": "search_documents",
        "description": (
            "Sök i uppladdade dokument efter relevant information. "
            "Anropa alltid när användaren ställer en fråga som kan besvaras från dokumenten."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Sökfråga baserad på användarens fråga",
                }
            },
            "required": ["query"],
        },
    }
]


def _build_rag_system(session_id: str) -> str:
    docs = store.get_all_documents(session_id)
    if docs:
        doc_list = "\n".join(f"- {d['filename']} ({d['n_chunks']} chunks)" for d in docs)
    else:
        doc_list = "(inga dokument uppladdade)"
    return RAG_SYSTEM_TEMPLATE.format(doc_list=doc_list)


def run_rag(message: str, history: list, session_id: str, search_query: str,
            system: str, extra_context: str | None = None):
    """RAG agent with search_documents tool loop. Returns (answer, sources, source_context)."""
    messages = [{"role": h["role"], "content": h["content"]} for h in history]

    if extra_context:
        messages.append({"role": "user", "content": (
            f"{message}\n\n[CRITIQUE FEEDBACK — improve your answer based on this]\n{extra_context}"
        )})
    else:
        messages.append({"role": "user", "content": message})

    sources_used = []
    source_context = ""

    for _ in range(10):  # max iterations
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=RAG_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return _extract_text(response), sources_used, source_context

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use" or block.name != "search_documents":
                    continue

                results = rag.search(search_query, session_id)

                for r in results:
                    if not any(
                        s["filename"] == r["filename"] and s["page"] == r["page"]
                        for s in sources_used
                    ):
                        sources_used.append({
                            "filename": r["filename"],
                            "page":     r["page"],
                            "text":     r["text"][:200],
                        })

                context = "\n\n".join(
                    f"[{r['filename']}, sida {r['page']}]\n{r['text']}"
                    for r in results
                ) or "Inga relevanta dokument hittades."

                source_context = context

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     context,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "[Oväntat fel i agent-loopen]", sources_used, source_context


# ── Agent 3: Critique ─────────────────────────────────────────────────────────

CRITIQUE_SYSTEM = """You are a critique agent for a RAG system. Your job is to evaluate whether an answer is well-supported by the provided source chunks.

You have a tool called `verify_claim` that lets you search the source chunks for evidence supporting or contradicting a specific claim. Use it to fact-check claims in the answer that seem uncertain or potentially hallucinated.

Workflow:
1. Read the answer and identify claims that need verification
2. Use verify_claim for each claim you want to check
3. After verifying, deliver your final verdict

When done, respond with EXACTLY one of these formats:

If the answer is good:
PASS

If the answer needs improvement:
FAIL
<feedback explaining what is wrong and how to improve>"""

CRITIQUE_TOOLS = [
    {
        "name": "verify_claim",
        "description": (
            "Search the source chunks for evidence supporting or contradicting a specific claim. "
            "Returns relevant excerpts from the sources."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The specific claim to verify against source chunks",
                }
            },
            "required": ["claim"],
        },
    }
]


def _verify_claim_tool(claim: str, session_id: str) -> str:
    """Semantic search for evidence related to a claim using rag.search()."""
    results = rag.search(claim, session_id, top_k=3)
    if not results:
        return "No relevant evidence found in source chunks for this claim."
    return "Relevant evidence found:\n\n" + "\n\n---\n\n".join(
        f"[{r['filename']}, sida {r['page']}]\n{r['text']}" for r in results
    )


def run_critique(question: str, answer: str, source_context: str, session_id: str) -> str | None:
    """Critique agent with verify_claim tool loop. Returns None if PASS, feedback string if FAIL."""
    messages = [{"role": "user", "content": (
        f"USER QUESTION:\n{question}\n\n"
        f"SOURCE CHUNKS:\n{source_context}\n\n"
        f"GENERATED ANSWER:\n{answer}"
    )}]

    for _ in range(10):  # max iterations
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=500,
            system=CRITIQUE_SYSTEM,
            tools=CRITIQUE_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            result = _extract_text(response).strip()
            if result.startswith("PASS"):
                return None
            return result[4:].strip() if result.startswith("FAIL") else result

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use" or block.name != "verify_claim":
                    continue
                evidence = _verify_claim_tool(block.input["claim"], session_id)
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     evidence,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return None  # If loop exits unexpectedly, let the answer through


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

def chat(message: str, history: list, session_id: str) -> dict:
    """Three-agent pipeline: Rewriter → RAG → Critique. Returns {response, sources}."""

    # 1. Rewriter agent
    search_query = rewrite_query(message)

    # 2. RAG agent
    system = _build_rag_system(session_id)
    answer, sources, source_context = run_rag(
        message, history, session_id, search_query, system
    )

    # 3. Critique agent (skip if no sources found)
    if source_context:
        feedback = run_critique(message, answer, source_context, session_id)

        # If critique fails, retry RAG once with feedback
        if feedback:
            answer, sources, _ = run_rag(
                message, history, session_id, search_query, system,
                extra_context=feedback,
            )

    return {"response": answer, "sources": sources}
