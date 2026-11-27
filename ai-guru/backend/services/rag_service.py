"""
Retrieval-Augmented Generation (RAG) for grounding answers in a specific
document (e.g. a lesson's text), instead of Gemini's general knowledge.

Pipeline: chunk text -> embed each chunk (Gemini embeddings) -> store in
an in-process vector store (services/vector_store.py, SQLite-backed so it
survives restarts; MongoDB is NOT involved - RAG never needed Mongo's
query features) -> on query, embed the question, cosine-rank the stored
chunks for that document_id in plain Python, and feed the top matches to
Gemini as grounding context.

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
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import config
from services import vector_store
from services.embedding_utils import (
    embeddings_available,
    embed_text,
    cosine_similarity,
    _tokenize,
    _lexical_vector,
)

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


def index_document(document_id, text):
    """Chunk + embed `text` and (re)store it under `document_id`, replacing
    any chunks already stored for that id so re-indexing doesn't duplicate.
    Stores real Gemini embeddings when a key is configured, or the chunk's
    own token list (for the lexical fallback) otherwise - either way,
    nothing is refused at index time."""
    chunks = chunk_text(text)
    docs = []
    for i, chunk in enumerate(chunks):
        embedded = embed_text(chunk, task_type="retrieval_document")
        docs.append({
            "document_id": document_id,
            "chunk_index": i,
            "chunk_text": chunk,
            "embedding_type": embedded["type"],
            "embedding": embedded.get("vector"),
            "tokens": embedded.get("tokens"),
        })
    vector_store.replace_document(document_id, docs)
    return len(docs)


def _rank_chunks(stored, question, top_k):
    if not stored:
        return []

    if embeddings_available() and stored[0].get("embedding_type") == "gemini":
        query_embedding = embed_text(question, task_type="retrieval_query")["vector"]
        scored = [
            (cosine_similarity(query_embedding, doc["embedding"]), doc)
            for doc in stored
        ]
    else:
        # Lexical fallback: build one shared vocabulary from the question's
        # tokens + every stored chunk's tokens, so all vectors line up on
        # the same dimensions, then rank by cosine similarity same as the
        # real-embedding path - same ranking math, a weaker feature space.
        question_tokens = _tokenize(question)
        vocabulary = sorted(set(question_tokens) | {t for doc in stored for t in (doc.get("tokens") or [])})
        query_vector = _lexical_vector(question, vocabulary)
        scored = [
            (cosine_similarity(query_vector, _lexical_vector(" ".join(doc.get("tokens") or []), vocabulary)), doc)
            for doc in stored
        ]

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:top_k]


def retrieve_top_chunks(document_id, question, top_k=TOP_K):
    stored = vector_store.get_document_chunks(document_id)
    return [doc for _, doc in _rank_chunks(stored, question, top_k)]


# shortcut: a single fixed threshold per embedding type, not calibrated
# against a real eval set. Lexical bag-of-words cosine scores run much
# lower than dense Gemini embedding scores for the same "this is relevant"
# judgment (sparse count vectors over a big shared vocabulary dilute the
# score), so the two paths need different cutoffs; revisit with real
# retrieval-quality data if false positives/negatives show up.
_MIN_SCORE_BY_MODE = {"gemini": 0.72, "lexical": 0.05}


def retrieve_relevant_chunks_any(question, top_k=TOP_K, min_score=None):
    """Search across every indexed document (no document_id required) -
    used by /chat to ground a plain message in whatever's been indexed via
    /rag/index, without the caller knowing which document_id is relevant.
    Returns [] (not an error) when nothing is indexed or nothing scores
    above min_score, so callers can safely treat this as "no context"."""
    stored = vector_store.get_all_chunks()
    if not stored:
        return []
    if min_score is None:
        mode = "gemini" if (embeddings_available() and stored[0].get("embedding_type") == "gemini") else "lexical"
        min_score = _MIN_SCORE_BY_MODE[mode]
    scored = _rank_chunks(stored, question, top_k)
    return [doc for score, doc in scored if score >= min_score]


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

    if _text_model is None:
        # No real generative model available: return the single best-
        # matching chunk itself as an extractive answer instead of a
        # placeholder string - a real, honest "best effort" answer rather
        # than fake-sounding filler, clearly labeled as extractive so a
        # caller can tell this isn't a generated, synthesized answer.
        answer = chunks[0]["chunk_text"]
        mode = "extractive_fallback"
    else:
        prompt = build_grounded_prompt(chunks, question)
        response = _text_model.generate_content(prompt)
        answer = response.text if response.text else "Sorry, I couldn't generate a response."
        mode = "generative"

    return {
        "answer": answer,
        "sources": [c["chunk_text"] for c in chunks],
        "mode": mode,
    }


if __name__ == "__main__":
    # Self-test. Works in both modes: real Gemini embeddings when a key is
    # configured, the lexical bag-of-words fallback otherwise - either way
    # a cat question should rank the cat paragraph above the solar-system
    # one, so the assertions below hold regardless of which path ran.
    print(f"Embedding mode for this run: {'gemini' if embeddings_available() else 'lexical_fallback'}")

    sample_text = (
        "Cats are small domesticated carnivorous mammals. They are known for "
        "their agility, sharp retractable claws, and independent nature. "
        "Domestic cats have been companions to humans for thousands of years. "
        "Cats communicate through meowing, purring, hissing, and body language "
        "such as tail position and ear movement. A typical house cat sleeps "
        "for twelve to sixteen hours a day and is most active at dawn and dusk.\n\n"
        "The solar system consists of the Sun and the objects that orbit it, "
        "including eight planets, their moons, and countless asteroids and "
        "comets. Jupiter is the largest planet in the solar system, and "
        "Mercury is the smallest and closest to the Sun. The asteroid belt "
        "lies between the orbits of Mars and Jupiter, containing millions of "
        "rocky bodies left over from the formation of the solar system."
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
        vector_store.delete_document(test_document_id)
