"""
Retrieval-Augmented Generation (RAG) for grounding answers in a specific
document (e.g. a lesson's text), instead of Gemini's general knowledge.

Pipeline: chunk text -> embed each chunk (Gemini embeddings) -> store in
MongoDB -> on query, embed the question, cosine-rank the stored chunks for
that document_id in plain Python, and feed the top matches to Gemini as
grounding context.

Embedding API: google-generativeai==0.3.0 is the version pinned in
requirements.txt. Its embedding.py (confirmed by inspecting the installed
wheel) exposes a module-level function:

    genai.embed_content(model: str, content: str | Iterable[str],
                         task_type: str | None = None,
                         title: str | None = None) -> dict

For a single string `content`, it returns {"embedding": [float, ...]}.
DEFAULT_EMB_MODEL in that module is "models/embedding-001" -- that is the
model id used below, since it is the one this exact installed SDK version
ships as its own default (text-embedding-004 postdates this SDK release and
isn't guaranteed to be served correctly through it, so we didn't guess it).
task_type is set to "retrieval_document" when embedding chunks and
"retrieval_query" when embedding the question, which is what this API
version's own task-type table (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY) is for.
"""
import math
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import config
import database

EMBEDDING_MODEL = "models/embedding-001"
CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP = 100
TOP_K = 3

# Reuse the same Gemini text model the rest of the app configures, instead of
# creating a second genai.configure()/GenerativeModel() elsewhere.
_text_model = None
if not config.USE_MOCK and config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    _text_model = genai.GenerativeModel('gemini-pro')


def embeddings_available():
    return not config.USE_MOCK and bool(config.GEMINI_API_KEY)


def chunk_text(text, max_chars=CHUNK_MAX_CHARS, overlap=CHUNK_OVERLAP):
    """Split on paragraph boundaries, capping each chunk at ~max_chars with
    a little overlap carried into the next chunk so a fact split across a
    paragraph break isn't lost entirely."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks = []
    current = ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            # carry a small tail of the previous chunk forward for overlap
            current = current[-overlap:] + "\n\n" + para
        else:
            current = para
        # a single paragraph longer than max_chars: hard-split it
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars - overlap:]
    if current:
        chunks.append(current)
    return chunks


def embed_text(text, task_type):
    result = genai.embed_content(model=EMBEDDING_MODEL, content=text, task_type=task_type)
    return result["embedding"]


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def index_document(document_id, text):
    """Chunk + embed `text` and (re)store it under `document_id`, replacing
    any chunks already stored for that id so re-indexing doesn't duplicate."""
    collection = database.get_rag_collection()
    chunks = chunk_text(text)
    docs = []
    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk, task_type="retrieval_document")
        docs.append({
            "document_id": document_id,
            "chunk_index": i,
            "chunk_text": chunk,
            "embedding": embedding,
        })
    collection.delete_many({"document_id": document_id})
    if docs:
        collection.insert_many(docs)
    return len(docs)


def retrieve_top_chunks(document_id, question, top_k=TOP_K):
    collection = database.get_rag_collection()
    stored = list(collection.find({"document_id": document_id}))
    if not stored:
        return []
    query_embedding = embed_text(question, task_type="retrieval_query")
    scored = [
        (cosine_similarity(query_embedding, doc["embedding"]), doc)
        for doc in stored
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def build_grounded_prompt(chunks, question):
    context = "\n\n---\n\n".join(c["chunk_text"] for c in chunks)
    return (
        "Answer ONLY using the context below. If the answer isn't in the "
        "context, say so.\n\nContext:\n" + context + "\n\nQuestion: " + question
    )


def answer_from_document(document_id, question, top_k=TOP_K):
    """Full query path: retrieve top chunks, build a grounded prompt, call
    Gemini, return {"answer": str, "sources": [chunk_text, ...]}."""
    chunks = retrieve_top_chunks(document_id, question, top_k=top_k)
    if not chunks:
        return None  # caller turns this into a 404

    prompt = build_grounded_prompt(chunks, question)
    if _text_model is None:
        answer = "mocked grounded answer"
    else:
        response = _text_model.generate_content(prompt)
        answer = response.text if response.text else "Sorry, I couldn't generate a response."

    return {
        "answer": answer,
        "sources": [c["chunk_text"] for c in chunks],
    }


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # Self-test. NOT executed in this environment: no confirmed live
    # MongoDB connection or Gemini API key here, so this is logically
    # reasoned-through code, not a measured result. Run it for real with
    # `python services/rag_service.py` once MONGODB_URI/GEMINI_API_KEY are
    # live, to actually measure instead of assume.
    #
    # Reasoning for why this should pass: the sample text has one paragraph
    # about cats and one about the solar system. A question about cats
    # should embed closer (higher cosine similarity) to the cat paragraph's
    # embedding than to the solar-system paragraph's embedding, so
    # retrieve_top_chunks should return the cat chunk first.
    # ------------------------------------------------------------------
    assert database.is_db_available(), "MongoDB must be available to run this self-test"
    assert embeddings_available(), "GEMINI_API_KEY must be set (and USE_MOCK off) to run this self-test"

    sample_text = (
        "Cats are small domesticated carnivorous mammals. They are known for "
        "their agility, sharp retractable claws, and independent nature. "
        "Domestic cats have been companions to humans for thousands of years.\n\n"
        "The solar system consists of the Sun and the objects that orbit it, "
        "including eight planets, their moons, and countless asteroids and "
        "comets. Jupiter is the largest planet in the solar system."
    )

    test_document_id = "__rag_self_test__"
    try:
        chunk_count = index_document(test_document_id, sample_text)
        assert chunk_count == 2, f"expected 2 chunks, got {chunk_count}"

        top_chunks = retrieve_top_chunks(test_document_id, "What are cats known for?", top_k=1)
        assert top_chunks, "expected at least one retrieved chunk"
        assert "cats" in top_chunks[0]["chunk_text"].lower(), (
            "expected the cat paragraph to be the top match for a cat question, "
            f"got: {top_chunks[0]['chunk_text'][:60]!r}"
        )

        result = answer_from_document(test_document_id, "What are cats known for?", top_k=1)
        assert result is not None
        assert "answer" in result and "sources" in result

        print("Self-test passed.")
    finally:
        database.get_rag_collection().delete_many({"document_id": test_document_id})
