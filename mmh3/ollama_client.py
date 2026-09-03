# -*- coding: utf-8 -*-
"""Minimal dependency-free Ollama client (urllib only) + ComfyUI IMAGE helpers."""

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if DEFAULT_URL and not DEFAULT_URL.startswith("http"):
    DEFAULT_URL = "http://" + DEFAULT_URL

_MODEL_CACHE = {"t": 0.0, "models": []}


def _norm(base_url):
    u = (base_url or DEFAULT_URL).strip().rstrip("/")
    if not u.startswith("http"):
        u = "http://" + u
    return u


def list_models(base_url=None, timeout=2.5, use_cache=True):
    """Return installed model tags. Never raises."""
    now = time.time()
    if use_cache and _MODEL_CACHE["models"] and (now - _MODEL_CACHE["t"] < 20):
        return list(_MODEL_CACHE["models"])
    url = _norm(base_url) + "/api/tags"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        models = sorted({m.get("name", "") for m in data.get("models", []) if m.get("name")})
        _MODEL_CACHE["t"] = now
        _MODEL_CACHE["models"] = models
        return list(models)
    except Exception:
        return list(_MODEL_CACHE["models"])


_CAP_CACHE = {}
_VISION_HINTS = ("vl", "vision", "llava", "minicpm-v", "moondream", "bakllava",
                 "gemma3", "gemma4", "pixtral", "internvl", "cogvlm", "janus",
                 "phi-4-multimodal")


def model_capabilities(base_url, model, timeout=4.0):
    """Return Ollama's capability list for a model, or None when unknown."""
    key = (_norm(base_url), model)
    if key in _CAP_CACHE:
        return _CAP_CACHE[key]
    caps = None
    try:
        data = _post_json(_norm(base_url) + "/api/show", {"model": model}, timeout)
        raw = data.get("capabilities")
        if isinstance(raw, list) and raw:
            caps = [str(c).lower() for c in raw]
        else:
            # Older Ollama has no capabilities field; infer from the projector.
            info = data.get("model_info") or {}
            has_proj = any("vision" in str(k).lower() or "clip" in str(k).lower()
                           for k in info)
            fams = [str(x).lower() for x in (data.get("details") or {}).get("families") or []]
            if has_proj or any("clip" in f or "mllama" in f or "vision" in f for f in fams):
                caps = ["completion", "vision"]
    except Exception:
        caps = None
    _CAP_CACHE[key] = caps
    return caps


def supports_vision(base_url, model):
    """True / False / None (unknown)."""
    caps = model_capabilities(base_url, model)
    if caps is None:
        name = (model or "").lower()
        if any(h in name for h in _VISION_HINTS):
            return True
        return None
    return "vision" in caps


def _post_json(url, payload, timeout):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def chat(base_url, model, system, user, images=None, options=None,
         keep_alive="5m", timeout=900, think=False):
    """Non-streaming /api/chat call. Returns the assistant text."""
    url = _norm(base_url) + "/api/chat"
    msg = {"role": "user", "content": user}
    if images:
        msg["images"] = images
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, msg],
        "stream": False,
        "keep_alive": keep_alive,
        "options": options or {},
    }
    # Ollama >= 0.9 supports disabling reasoning output on thinking models.
    if think is False:
        payload["think"] = False
    try:
        data = _post_json(url, payload, timeout)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")[:500]
        except Exception:
            pass
        if e.code == 400 and "think" in detail:
            payload.pop("think", None)
            data = _post_json(url, payload, timeout)
        else:
            raise RuntimeError(
                "Ollama HTTP {} at {}\n{}".format(e.code, url, detail)) from None
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Cannot reach Ollama at {}. Is `ollama serve` running?\n{}".format(url, e.reason)
        ) from None
    # Ollama reports what it actually tokenised. estimate_text_tokens() is len/4 and
    # runs low on structured text, so the real counts are what the caller should judge
    # a context overflow by.
    global LAST_USAGE
    LAST_USAGE = {
        "prompt_tokens": int(data.get("prompt_eval_count") or 0),
        "reply_tokens": int(data.get("eval_count") or 0),
        "done_reason": str(data.get("done_reason") or ""),
    }
    return (data.get("message", {}) or {}).get("content", "") or ""


# Filled in by the most recent chat() call. Read it right after the call.
LAST_USAGE = {"prompt_tokens": 0, "reply_tokens": 0, "done_reason": ""}


def usage_note(num_ctx, max_tokens):
    """Judge the last call against the real counts. '' when everything fit."""
    u = LAST_USAGE
    p, r, why = u["prompt_tokens"], u["reply_tokens"], u["done_reason"]
    if not p:
        return ""                                   # older Ollama: no counts reported
    ctx = max(1, int(num_ctx or 0))
    bits = []
    if p + r >= ctx:
        bits.append("CONTEXT FULL — prompt {} + reply {} = {} against num_ctx {}. The "
                    "front of the prompt was dropped; rules go missing at random when "
                    "this happens. Raise num_ctx.".format(p, r, p + r, ctx))
    elif p + max(0, int(max_tokens or 0)) > ctx:
        bits.append("context tight — prompt {} leaves {} for the reply but max_tokens "
                    "is {}. Raise num_ctx or lower max_tokens.".format(
                        p, ctx - p, int(max_tokens or 0)))
    if why == "length":
        bits.append("the reply hit max_tokens ({}) and was cut off mid-sentence. "
                    "Raise max_tokens.".format(int(max_tokens or 0)))
    if not bits:
        bits.append("tokens: prompt {}, reply {}, num_ctx {} ({} free).".format(
            p, r, ctx, ctx - p - r))
    return " ".join(bits)


def loaded_models(base_url, timeout=4.0):
    """/api/ps -> names of models currently resident in VRAM/RAM. [] on failure."""
    try:
        req = urllib.request.Request(_norm(base_url) + "/api/ps",
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def unload(base_url, model, timeout=30, verify_tries=6, verify_delay=0.5):
    """
    Ask Ollama to evict the model right now and confirm it actually left.

    ComfyUI's own 'Clear VRAM' cannot touch this — Ollama is a separate process,
    so the eviction has to be requested over its HTTP API with keep_alive: 0.
    Returns (ok, detail).
    """
    attempts = (
        ("/api/generate", {"model": model, "prompt": "", "keep_alive": 0, "stream": False}),
        ("/api/chat", {"model": model, "messages": [], "keep_alive": 0, "stream": False}),
    )
    errors = []
    for path, payload in attempts:
        try:
            _post_json(_norm(base_url) + path, payload, timeout)
        except Exception as e:
            errors.append("{} -> {}".format(path, e))
            continue
        for _ in range(verify_tries):
            resident = loaded_models(base_url)
            if not resident:
                return True, "evicted (nothing resident)"
            if model not in resident:
                return True, "evicted ({} still resident)".format(", ".join(resident))
            time.sleep(verify_delay)
        errors.append("{} -> still resident after {:.1f}s".format(
            path, verify_tries * verify_delay))
    return False, "; ".join(errors) or "unknown failure"


# ------------------------------------------------------------------ images

def tensor_to_b64_list(image, max_images=4, max_side=1024):
    """ComfyUI IMAGE tensor [B,H,W,C] float 0..1 -> list of base64 PNG strings."""
    if image is None:
        return []
    try:
        import numpy as np
        from PIL import Image
    except Exception as e:
        raise RuntimeError("Pillow/numpy are required for image input: %s" % e)

    arr = image
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    arr = np.asarray(arr)
    if arr.ndim == 3:
        arr = arr[None, ...]

    out = []
    for i in range(min(arr.shape[0], max_images)):
        side = max(320, max_side - i * 8)   # see director_link.load_items
        frame = np.clip(arr[i] * 255.0 + 0.5, 0, 255).astype("uint8")
        if frame.shape[-1] == 4:
            frame = frame[..., :3]
        img = Image.fromarray(frame, "RGB")
        w, h = img.size
        if max(w, h) > side:
            s = side / float(max(w, h))
            img = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        out.append(base64.b64encode(buf.getvalue()).decode("ascii"))
    return out


# ------------------------------------------------- context budget estimation

def estimate_text_tokens(text):
    """Rough token count. English prose runs about 4 characters per token."""
    return max(0, len(text or "")) // 4


def estimate_image_tokens(max_side, n_images):
    """
    Vision models tile the picture and spend a fixed number of tokens per tile.
    Gemma/Qwen-VL style encoders land near 256 tokens for a ~768px tile, so a
    1536px long side on a 4:3 frame is roughly 2x2 tiles.
    """
    if not n_images:
        return 0
    side = max(256, int(max_side or 1024))
    tiles_long = max(1, -(-side // 768))              # ceil
    tiles_short = max(1, -(-int(side * 0.75) // 768))
    return n_images * tiles_long * tiles_short * 256


def check_context_budget(num_ctx, max_tokens, texts, n_images, image_max_side):
    """
    Return a warning string when the prompt cannot fit alongside the reply.

    num_ctx is shared by input AND output. When the input alone eats the window
    the model silently drops the front of the prompt or stops generating early —
    which shows up as a prompt that is simply missing its last sections.
    """
    text_tok = sum(estimate_text_tokens(t) for t in texts)
    img_tok = estimate_image_tokens(image_max_side, n_images)
    needed = text_tok + img_tok + max(0, int(max_tokens or 0))
    ctx = max(1, int(num_ctx or 0))
    if needed <= ctx:
        return ""
    want = ((needed + 2047) // 2048) * 2048
    return (
        "CONTEXT OVERFLOW — the prompt does not fit and the output WILL be cut off.\n"
        "    text {} + images {} + reply {} = about {} tokens, but num_ctx is {}.\n"
        "    Raise num_ctx to {} or more, or reduce the input: turn vision_pass off, "
        "lower image_max_side, or send fewer pictures.".format(
            text_tok, img_tok, int(max_tokens or 0), needed, ctx, want))
