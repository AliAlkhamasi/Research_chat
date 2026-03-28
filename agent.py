"""
Three-agent pipeline: Rewriter, RAG, Critique.
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

When you're satisfied, respond with ONLY the final search query text, nothing else."""

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
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):
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
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     _expand_query_tool(block.input["seed"]),
                })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return user_message


# ── Agent 2: RAG ──────────────────────────────────────────────────────────────

RAG_SYSTEM_TEMPLATE = """You are a research assistant that helps users search and understand uploaded documents. The documents can be about any topic.

Respond in the same language the user writes in. Be concise and clear.

IMPORTANT: The user has the following documents uploaded:
{doc_list}

You MUST always call search_documents when the user asks a question. NEVER assume documents are missing, call the tool first.
Always cite sources in your answer: "(page X in [filename])".
If the search finds nothing relevant, say so directly."""

RAG_TOOLS = [
    {
        "name": "search_documents",
        "description": (
            "Search uploaded documents for relevant information. "
            "Always call this when the user asks a question that can be answered from the documents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query based on the user's question",
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
        doc_list = "(no documents uploaded)"
    return RAG_SYSTEM_TEMPLATE.format(doc_list=doc_list)


def run_rag(message: str, history: list, session_id: str, search_query: str,
            system: str, extra_context: str | None = None):
    messages = [{"role": h["role"], "content": h["content"]} for h in history]

    if extra_context:
        messages.append({"role": "user", "content": (
            f"{message}\n\n[CRITIQUE FEEDBACK — improve your answer based on this]\n{extra_context}"
        )})
    else:
        messages.append({"role": "user", "content": message})

    sources_used = []
    source_context = ""

    for _ in range(10):
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
                    f"[{r['filename']}, page {r['page']}]\n{r['text']}"
                    for r in results
                ) or "No relevant documents found."

                source_context = context
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     context,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "[Unexpected error in agent loop]", sources_used, source_context


# ── Agent 3: Critique ─────────────────────────────────────────────────────────

CRITIQUE_SYSTEM = """You are a critique agent for a RAG system. Your job is to evaluate whether an answer is well-supported by the provided source chunks.

You have a tool called `verify_claim` that lets you search the document chunks for evidence supporting or contradicting a specific claim. Use it to fact-check claims that seem uncertain or potentially hallucinated.

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
            "Search the document chunks for evidence supporting or contradicting a specific claim. "
            "Returns relevant excerpts from the sources."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The specific claim to verify against the source chunks",
                }
            },
            "required": ["claim"],
        },
    }
]


def _verify_claim_tool(claim: str, session_id: str) -> str:
    results = rag.search(claim, session_id, top_k=3)
    if not results:
        return "No relevant evidence found in source chunks for this claim."
    return "Relevant evidence found:\n\n" + "\n\n---\n\n".join(
        f"[{r['filename']}, page {r['page']}]\n{r['text']}" for r in results
    )


def run_critique(question: str, answer: str, source_context: str, session_id: str) -> str | None:
    messages = [{"role": "user", "content": (
        f"USER QUESTION:\n{question}\n\n"
        f"SOURCE CHUNKS:\n{source_context}\n\n"
        f"GENERATED ANSWER:\n{answer}"
    )}]

    for _ in range(10):
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
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     _verify_claim_tool(block.input["claim"], session_id),
                })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return None


# ── Pipeline ──────────────────────────────────────────────────────────────────

def chat(message: str, history: list, session_id: str) -> dict:
    search_query = rewrite_query(message)

    system = _build_rag_system(session_id)
    answer, sources, source_context = run_rag(
        message, history, session_id, search_query, system
    )

    if source_context:
        feedback = run_critique(message, answer, source_context, session_id)
        if feedback:
            answer, sources, _ = run_rag(
                message, history, session_id, search_query, system,
                extra_context=feedback,
            )

    return {"response": answer, "sources": sources}
