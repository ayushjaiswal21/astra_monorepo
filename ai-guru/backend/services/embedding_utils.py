"""
Shared embedding/scoring primitives used by both rag_service.py (document
grounding) and career_gps_service.py (career-profile matching), so there is
exactly one embedding implementation in the codebase rather than two
independently-written ones.

Dual path, same as before: real Gemini embeddings when a key is configured,
otherwise a deterministic lexical bag-of-words vector scored with the same
cosine_similarity. See rag_service.py's original module docstring for the
embedding API details (genai.embed_content, task_type, etc.) - unchanged
here, just relocated.
"""
import math
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import config

EMBEDDING_MODEL = "models/embedding-001"


def embeddings_available():
    return not config.USE_MOCK and bool(config.GEMINI_API_KEY)


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _lexical_vector(text, vocabulary):
    """A word-count vector over a fixed, shared vocabulary so every vector
    in a comparison has matching dimensions."""
    counts = {}
    for tok in _tokenize(text):
        counts[tok] = counts.get(tok, 0) + 1
    return [counts.get(word, 0) for word in vocabulary]


def embed_text(text, task_type):
    if embeddings_available():
        result = genai.embed_content(model=EMBEDDING_MODEL, content=text, task_type=task_type)
        return {"vector": result["embedding"], "type": "gemini"}
    # Fallback path: the vocabulary is just this text's own tokens; real
    # ranking happens later, where callers rebuild a shared vocabulary
    # across every text being compared.
    return {"vector": None, "type": "lexical", "tokens": _tokenize(text)}


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def rank_by_similarity(query_text, candidates, get_embedding_type, get_vector, get_tokens):
    """Shared ranking helper: embed `query_text` and score it against
    `candidates` (any list), using real embeddings if the first candidate
    has them, else the lexical fallback with a shared vocabulary built from
    the query + every candidate's tokens.

    get_embedding_type/get_vector/get_tokens are accessors (candidate -> value)
    so this works whether candidates are dicts, objects, etc.

    Returns a list of (score, candidate) sorted descending by score.
    """
    if not candidates:
        return []

    if embeddings_available() and get_embedding_type(candidates[0]) == "gemini":
        query_vector = embed_text(query_text, task_type="retrieval_query")["vector"]
        return sorted(
            ((cosine_similarity(query_vector, get_vector(c)), c) for c in candidates),
            key=lambda pair: pair[0],
            reverse=True,
        )

    query_tokens = _tokenize(query_text)
    vocabulary = sorted(set(query_tokens) | {t for c in candidates for t in (get_tokens(c) or [])})
    query_vector = _lexical_vector(query_text, vocabulary)
    return sorted(
        (
            (cosine_similarity(query_vector, _lexical_vector(" ".join(get_tokens(c) or []), vocabulary)), c)
            for c in candidates
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
