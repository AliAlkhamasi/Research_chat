"""
Redis storage — session-scoped documents + chunks.
Uses redis-py with connection pooling. 4-hour TTL on all session data.
"""

import os
import json
import uuid
import base64
import numpy as np
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL = 4 * 60 * 60  # 4 hours

_pool = redis.ConnectionPool.from_url(REDIS_URL)


def _r():
    return redis.Redis(connection_pool=_pool)


def _refresh_ttl(r, session_id: str):
    for key in r.scan_iter(match=f"sess:{session_id}:*"):
        r.expire(key, SESSION_TTL)


def create_session() -> str:
    session_id = uuid.uuid4().hex
    r = _r()
    r.set(f"sess:{session_id}:next_doc_id", 0, ex=SESSION_TTL)
    return session_id


def delete_session(session_id: str):
    r = _r()
    keys = list(r.scan_iter(match=f"sess:{session_id}:*"))
    if keys:
        r.delete(*keys)


def save_document(session_id: str, filename: str) -> int:
    r = _r()
    doc_id = r.incr(f"sess:{session_id}:next_doc_id")
    r.hset(f"sess:{session_id}:docs", str(doc_id), json.dumps({"filename": filename}))
    _refresh_ttl(r, session_id)
    return doc_id


def save_chunks(session_id: str, doc_id: int, chunks: list):
    """chunks: list of {page, text, embedding} where embedding is np.ndarray"""
    r = _r()
    pipe = r.pipeline()
    key = f"sess:{session_id}:chunks"
    for chunk in chunks:
        emb_b64 = base64.b64encode(chunk["embedding"].astype(np.float32).tobytes()).decode()
        pipe.rpush(key, json.dumps({
            "doc_id": doc_id,
            "page": chunk["page"],
            "text": chunk["text"],
            "embedding": emb_b64,
        }))
    pipe.expire(key, SESSION_TTL)
    pipe.execute()
    _refresh_ttl(r, session_id)


def get_all_documents(session_id: str) -> list:
    r = _r()
    docs_raw = r.hgetall(f"sess:{session_id}:docs")
    chunks_raw = _get_raw_chunks(r, session_id)

    chunk_counts = {}
    for c in chunks_raw:
        chunk_counts[c["doc_id"]] = chunk_counts.get(c["doc_id"], 0) + 1

    docs = []
    for doc_id_bytes, data_bytes in docs_raw.items():
        doc_id = int(doc_id_bytes)
        data = json.loads(data_bytes)
        docs.append({
            "id": doc_id,
            "filename": data["filename"],
            "n_chunks": chunk_counts.get(doc_id, 0),
        })
    return docs


def _get_raw_chunks(r, session_id: str) -> list:
    return [json.loads(entry) for entry in r.lrange(f"sess:{session_id}:chunks", 0, -1)]


def get_all_chunks(session_id: str) -> list:
    r = _r()
    raw_chunks = _get_raw_chunks(r, session_id)
    docs_raw = r.hgetall(f"sess:{session_id}:docs")

    doc_names = {}
    for doc_id_bytes, data_bytes in docs_raw.items():
        doc_names[int(doc_id_bytes)] = json.loads(data_bytes)["filename"]

    result = []
    for chunk in raw_chunks:
        emb = np.frombuffer(base64.b64decode(chunk["embedding"]), dtype=np.float32)
        result.append({
            "doc_id":   chunk["doc_id"],
            "page":     chunk["page"],
            "text":     chunk["text"],
            "embedding": emb,
            "filename": doc_names.get(chunk["doc_id"], "unknown"),
        })
    return result


def delete_document(session_id: str, doc_id: int):
    r = _r()
    r.hdel(f"sess:{session_id}:docs", str(doc_id))

    key = f"sess:{session_id}:chunks"
    raw_chunks = _get_raw_chunks(r, session_id)
    remaining = [json.dumps(c) for c in raw_chunks if c["doc_id"] != doc_id]

    pipe = r.pipeline()
    pipe.delete(key)
    for entry in remaining:
        pipe.rpush(key, entry)
    if remaining:
        pipe.expire(key, SESSION_TTL)
    pipe.execute()
