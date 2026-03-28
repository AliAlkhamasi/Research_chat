# Research Chat

Multiagent RAG application that lets you upload any PDF or text file and ask questions about it. Built with a three agent pipeline where each agent has its own tool use loop, not just wrapper calls around an LLM.

## How it works

You upload documents. They get chunked and embedded locally with sentence-transformers. When you ask a question, three agents work together to produce the answer:

**Agent 1: Query Rewriter**
Takes your raw question and rewrites it into a semantically rich search query. Has an `expand_query` tool that generates multiple query variations so it can pick the best one for retrieval.

**Agent 2: RAG Agent**
Searches the document chunks using cosine similarity against the rewritten query. Generates an answer with source citations. Has a `search_documents` tool and runs a full tool use loop.

**Agent 3: Critique Agent**
Evaluates whether the RAG agent's answer is actually grounded in the sources. Has a `verify_claim` tool that does semantic search against the chunks to fact check specific claims. If the answer is vague, hallucinated, or poorly supported, it sends feedback back to the RAG agent which regenerates once.

The user only sees the final answer. All three agents run under the hood.

## Architecture

```
Frontend (React + Vite)
    |
FastAPI server
    |
Redis (session scoped storage, 4h TTL)
    |
sentence-transformers/all-MiniLM-L6-v2 (local embeddings)
    |
Claude Haiku 4.5 (all three agents)
```

Each user gets an isolated session. Documents, chunks, and embeddings are stored in Redis and scoped to that session. Sessions are cleaned up on tab close or expire after 4 hours.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, Vite |
| Backend | FastAPI, Uvicorn |
| Storage | Redis with connection pooling |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, runs locally) |
| LLM | Claude Haiku 4.5 via Anthropic API |
| PDF parsing | PyPDF2 |

## Setup

```bash
# Backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Redis (via Docker)
docker run -d --name redis -p 6379:6379 redis

# Set your API key
echo ANTHROPIC_API_KEY=sk-... > .env

# Start backend
python server.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Features

- Upload multiple PDFs or text files per session
- Multiagent pipeline with query rewriting, retrieval, and critique
- Source citations with page numbers on every answer
- Chat history tied to session, saved chats persist across sessions
- Session isolation via Redis with automatic TTL cleanup
