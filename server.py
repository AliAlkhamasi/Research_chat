"""
Research Chat — FastAPI server
Run: python server.py → http://localhost:8000
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

import store
import rag
import agent

UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Research Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Sessions ──────────────────────────────────────────────────────────────────

@app.post("/session")
def create_session():
    session_id = store.create_session()
    return {"session_id": session_id}


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    store.delete_session(session_id)
    return {"success": True}


@app.post("/session/{session_id}/cleanup")
def cleanup_session(session_id: str):
    """POST endpoint for navigator.sendBeacon cleanup on tab close."""
    store.delete_session(session_id)
    return {"success": True}


# ── Documents ──────────────────────────────────────────────────────────────────

@app.get("/session/{session_id}/documents")
def list_documents(session_id: str):
    return store.get_all_documents(session_id)


@app.post("/session/{session_id}/documents/upload")
async def upload_document(session_id: str, file: UploadFile = File(...)):
    filename = file.filename
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".txt"):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported")

    save_path = UPLOADS_DIR / filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if suffix == ".pdf":
            pages = rag.parse_pdf(str(save_path))
        else:
            pages = rag.parse_text(str(save_path))

        chunks = rag.chunk_text(pages)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text could be extracted from the file")

        texts = [c["text"] for c in chunks]
        embeddings = rag.embed_texts(texts)

        doc_id = store.save_document(session_id, filename)
        db_chunks = [
            {"page": c["page"], "text": c["text"], "embedding": embeddings[i]}
            for i, c in enumerate(chunks)
        ]
        store.save_chunks(session_id, doc_id, db_chunks)

        return {"id": doc_id, "filename": filename, "n_chunks": len(chunks)}

    except HTTPException:
        raise
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}/documents/{doc_id}")
def delete_document(session_id: str, doc_id: int):
    store.delete_document(session_id, doc_id)
    return {"success": True}


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []


@app.post("/session/{session_id}/chat")
def chat(session_id: str, req: ChatRequest):
    try:
        return agent.chat(req.message, req.history, session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
