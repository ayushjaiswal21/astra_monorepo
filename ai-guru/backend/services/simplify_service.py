"""
Free, local text simplification using a small encoder-decoder Transformer.

Why this exists: Gemini-based simplification (used elsewhere in this app)
needs an API key and a live quota; this gives the astra lesson page's
"Simplify" tab a fallback that runs fully offline, on CPU, for free.

Model: started from the pretrained google/t5-efficient-tiny checkpoint
(T5 encoder-decoder, d_model=256, 4 heads, d_ff=1024, vocab=32128) and then
made two real architecture changes:
  1. Depth-pruned both the encoder and decoder from 4 transformer blocks to
     2 each (kept blocks 0 and 2 of each stack - "every-other" pruning,
     which keeps one early + one late block rather than truncating to the
     first N, since adjacent early blocks tend to be the most redundant).
     This drops total transformer-block parameters by ~50% while keeping
     one block per stack that has seen the "late" learned representations.
  2. Fine-tuned the pruned model (60 epochs over 15 example pairs, CPU,
     AdamW) on a deterministic, rule-based simplification task (see
     build_model.py used to produce this checkpoint), because
     t5-efficient-tiny is only pretrained (span-corruption) and produces
     unusable output on a downstream task with zero fine-tuning.

Loaded lazily on first request so importing this module (and therefore
main.py) never requires torch/transformers to be installed in every
environment that imports main.py for other reasons.
"""
import os
import time

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "simplify_model")

_model = None
_tokenizer = None
_param_count = None
_load_error = None


def _lazy_load():
    global _model, _tokenizer, _param_count, _load_error
    if _model is not None or _load_error is not None:
        return
    try:
        import torch
        from transformers import T5TokenizerFast, T5ForConditionalGeneration
        # Tokenizer/vocab is untouched by the architecture surgery (only the
        # encoder/decoder block counts changed), so load the original
        # t5-efficient-tiny tokenizer rather than re-saving+reloading it
        # (the locally re-saved tokenizer_config.json hits an unrelated
        # transformers-version quirk with `extra_special_tokens`).
        try:
            tok = T5TokenizerFast.from_pretrained("google/t5-efficient-tiny", local_files_only=True)
        except Exception:
            tok = T5TokenizerFast.from_pretrained("google/t5-efficient-tiny")
        model = T5ForConditionalGeneration.from_pretrained(MODEL_DIR)
        model.eval()
        _tokenizer = tok
        _model = model
        _param_count = sum(p.numel() for p in model.parameters())
    except Exception as e:
        _load_error = str(e)


def is_available() -> bool:
    _lazy_load()
    return _model is not None


def get_param_count():
    _lazy_load()
    return _param_count


def simplify(text: str, max_new_tokens: int = 60):
    """Returns (simplified_text, latency_seconds). Raises RuntimeError if the
    model failed to load (e.g. torch/transformers not installed)."""
    _lazy_load()
    if _model is None:
        raise RuntimeError(f"small-transformer model unavailable: {_load_error}")

    import torch
    t0 = time.time()
    inputs = _tokenizer("simplify: " + text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        # no_repeat_ngram_size/repetition_penalty: the retrained model (see
        # simplify_model/model_card.json) occasionally loops on a short
        # phrase under plain greedy decoding; this suppresses that without
        # changing latency.
        out_ids = _model.generate(
            **inputs, max_new_tokens=max_new_tokens, num_beams=1,
            no_repeat_ngram_size=3, repetition_penalty=1.3,
        )
    simplified = _tokenizer.decode(out_ids[0], skip_special_tokens=True)
    latency = time.time() - t0
    return simplified, latency
