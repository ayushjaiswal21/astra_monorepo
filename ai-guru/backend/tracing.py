"""LLM call tracing: wraps a Gemini call, records a trimmed trace document to
MongoDB's `llm_traces` collection. Tracing failures must never break the
actual chat response (same is_db_available()/try-except no-op pattern as the
rest of the app) -- shortcut: no retry/backoff on the trace write itself.
"""
import functools
import time
import traceback
from datetime import datetime, timezone

import database

EXCERPT_LEN = 200


def _excerpt(value):
    text = value if isinstance(value, str) else str(value)
    return text[:EXCERPT_LEN]


def _write_trace(doc):
    if not database.is_db_available():
        return
    try:
        database.db.llm_traces.insert_one(doc)
    except Exception:
        # Tracing must never break the real response.
        pass


def trace_llm_call(call_type="chat"):
    """Decorator for an async Gemini-call function. Records timestamp,
    call_type, prompt/response excerpts (first 200 chars, not full text),
    latency_ms, a rough token_estimate (len(prompt)//4), success and error.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # First positional/keyword arg is the user text/prompt for both
            # generate_text_response(text, ...) and generate_image_response(pil_image, text, ...).
            prompt_source = kwargs.get("text")
            if prompt_source is None and args:
                prompt_source = args[0] if isinstance(args[0], str) else (args[1] if len(args) > 1 else "")
            prompt_source = prompt_source or ""

            start = time.monotonic()
            success = True
            error = None
            result = None
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = f"{type(e).__name__}: {e}"
                raise
            finally:
                latency_ms = (time.monotonic() - start) * 1000
                _write_trace({
                    "timestamp": datetime.now(timezone.utc),
                    "call_type": call_type,
                    "prompt_excerpt": _excerpt(prompt_source),
                    "response_excerpt": _excerpt(result) if success and result is not None else None,
                    "latency_ms": latency_ms,
                    "token_estimate": len(prompt_source) // 4,
                    "success": success,
                    "error": error,
                })
        return wrapper
    return decorator
