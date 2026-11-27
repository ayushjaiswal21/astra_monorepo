"""
In-process RAG vector store, used instead of MongoDB so /rag/index and
/rag/query work even when Mongo is down (RAG never actually needed Mongo's
query/transaction features - it was just reusing the same client that chat
history uses). An in-memory dict is the fast path; a local SQLite file
(rag_store.sqlite, stdlib sqlite3, no new dependency) persists chunks so
indexed documents survive a backend restart.

Shape mirrors what was previously inserted into database.get_rag_collection():
one record per chunk: document_id, chunk_index, chunk_text, embedding_type,
embedding (list[float] or None), tokens (list[str] or None).
"""
import json
import os
import sqlite3
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_store.sqlite")

_lock = threading.Lock()
_store = {}  # document_id -> list[dict]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding_type TEXT NOT NULL,
            embedding TEXT,
            tokens TEXT,
            PRIMARY KEY (document_id, chunk_index)
        )
    """)
    return conn


def _load_from_disk():
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT document_id, chunk_index, chunk_text, embedding_type, embedding, tokens FROM rag_chunks"
        ).fetchall()
    finally:
        conn.close()
    loaded = {}
    for document_id, chunk_index, chunk_text, embedding_type, embedding_json, tokens_json in rows:
        loaded.setdefault(document_id, []).append({
            "document_id": document_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "embedding_type": embedding_type,
            "embedding": json.loads(embedding_json) if embedding_json else None,
            "tokens": json.loads(tokens_json) if tokens_json else None,
        })
    for doc_chunks in loaded.values():
        doc_chunks.sort(key=lambda d: d["chunk_index"])
    return loaded


_store = _load_from_disk()


def replace_document(document_id, docs):
    """Replace all chunks stored for document_id with `docs` (a list of the
    chunk dicts described above). Writes through to SQLite immediately."""
    with _lock:
        if docs:
            _store[document_id] = docs
        else:
            _store.pop(document_id, None)

        conn = _connect()
        try:
            conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
            for doc in docs:
                conn.execute(
                    "INSERT INTO rag_chunks (document_id, chunk_index, chunk_text, embedding_type, embedding, tokens) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        doc["document_id"],
                        doc["chunk_index"],
                        doc["chunk_text"],
                        doc["embedding_type"],
                        json.dumps(doc["embedding"]) if doc.get("embedding") is not None else None,
                        json.dumps(doc["tokens"]) if doc.get("tokens") is not None else None,
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def get_document_chunks(document_id):
    return list(_store.get(document_id, []))


def get_all_chunks():
    """All chunks across every indexed document - used by /chat to search
    for relevant context without knowing a document_id in advance."""
    all_chunks = []
    for chunks in _store.values():
        all_chunks.extend(chunks)
    return all_chunks


def delete_document(document_id):
    replace_document(document_id, [])
