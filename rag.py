"""
RAG module — parse, chunk, embed, search.
Uses sentence-transformers/all-MiniLM-L6-v2 locally.
"""

import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def parse_pdf(path: str) -> list:
    """Returns [{page: int, text: str}]"""
    import PyPDF2
    pages = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page": i + 1, "text": text})
    return pages


def parse_text(path: str) -> list:
    """Returns [{page: 1, text: str}]"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return [{"page": 1, "text": text}]


def chunk_text(pages: list, chunk_size: int = 400, overlap: int = 50) -> list:
    """Returns [{page: int, text: str}]"""
    chunks = []
    for page in pages:
        words = page["text"].split()
        i = 0
        while i < len(words):
            chunk = " ".join(words[i: i + chunk_size])
            chunks.append({"page": page["page"], "text": chunk})
            i += chunk_size - overlap
    return chunks


def embed_texts(texts: list) -> np.ndarray:
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def search(query: str, session_id: str, top_k: int = 5) -> list:
    """Cosine similarity search over chunks for a specific session."""
    import store

    chunks = store.get_all_chunks(session_id)
    if not chunks:
        return []

    query_emb = embed_texts([query])[0]
    norm_q = np.linalg.norm(query_emb)

    results = []
    for chunk in chunks:
        emb = chunk.get("embedding")
        if emb is None:
            continue
        norm_c = np.linalg.norm(emb)
        if norm_q == 0 or norm_c == 0:
            score = 0.0
        else:
            score = float(np.dot(query_emb, emb) / (norm_q * norm_c))
        results.append({
            "text":     chunk["text"],
            "page":     chunk["page"],
            "doc_id":   chunk["doc_id"],
            "filename": chunk["filename"],
            "score":    score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
