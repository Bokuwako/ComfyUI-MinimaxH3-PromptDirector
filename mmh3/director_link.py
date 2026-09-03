# -*- coding: utf-8 -*-
"""
Read the MiniMaxH3Director node's own widget state straight out of the executing
graph, so the writer node needs no extra wiring.

At execution time ComfyUI hands every node the whole API-format prompt through the
hidden "PROMPT" input. The Director keeps everything we need in its widgets:

    mode           -> "T2VA" / "I2VA" / "FL2VA" / "REF2VA" ...
    duration       -> int seconds
    timeline_data  -> JSON: {"items":[{"type":"image","value":"a.png","slot":0,...}]}
    builder_state  -> JSON: {"mode":..., "duration":..., ...}

So the operator picks the mode and drops the images into the Director exactly as
before, and the prompt writer follows along.
"""

import base64
import io
import json
import os

DIRECTOR_CLASS = "MiniMaxH3Director"

_MEDIA_EXT_IMAGE = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")
_WALK_FILE_BUDGET = 40000


# ----------------------------------------------------------------- graph access

def _widget_value(node, key):
    """Widget values live in node['inputs']; a linked widget is [node_id, slot]."""
    val = (node.get("inputs") or {}).get(key)
    if isinstance(val, (list, tuple)):
        return None          # driven by a link, not a literal we can read
    return val


_JUNK_HINTS = {"", "false", "true", "none", "null", "nan", "auto", "-", "n/a"}


def clean_node_id_hint(raw):
    """A stale/shifted workflow can push a boolean into this string widget. Ignore junk."""
    h = str(raw or "").strip()
    return "" if h.lower() in _JUNK_HINTS else h


def find_directors(prompt_graph):
    if not isinstance(prompt_graph, dict):
        return []
    return [(str(nid), node) for nid, node in prompt_graph.items()
            if isinstance(node, dict) and node.get("class_type") == DIRECTOR_CLASS]


def find_director(prompt_graph, node_id_hint=""):
    """Return (node_id, node_dict, note). Falls back to the sole Director on a bad hint."""
    hits = find_directors(prompt_graph)
    if not hits:
        return None, None, ""
    hint = clean_node_id_hint(node_id_hint)
    if hint:
        for nid, node in hits:
            if nid == hint:
                return nid, node, ""
        if len(hits) == 1:
            return hits[0][0], hits[0][1], (
                "director_node_id '{}' matched nothing — using the only Director in the "
                "graph (#{}). Clear that field.".format(hint, hits[0][0]))
        return None, None, (
            "director_node_id '{}' matched none of the {} Directors ({}).".format(
                hint, len(hits), ", ".join("#" + n for n, _ in hits)))
    if len(hits) > 1:
        return hits[0][0], hits[0][1], (
            "{} Directors in the graph ({}) — using #{}. Set director_node_id to pick "
            "another.".format(len(hits), ", ".join("#" + n for n, _ in hits), hits[0][0]))
    return hits[0][0], hits[0][1], ""


# ----------------------------------------------------------------- media lookup

def _comfy_dirs():
    dirs = []
    try:
        import folder_paths
        for fn in ("get_input_directory", "get_output_directory", "get_temp_directory"):
            try:
                d = getattr(folder_paths, fn)()
                if d and os.path.isdir(d):
                    dirs.append(d)
            except Exception:
                pass
    except Exception:
        pass
    return dirs


def resolve_media_path(name):
    """Filename as stored by the Director -> absolute path on disk, or None."""
    if not name:
        return None
    if os.path.isabs(name) and os.path.isfile(name):
        return name

    try:
        import folder_paths
        p = folder_paths.get_annotated_filepath(name)
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass

    clean = name.split(" [")[0].strip()
    dirs = _comfy_dirs()
    for d in dirs:
        p = os.path.join(d, clean)
        if os.path.isfile(p):
            return p

    base = os.path.basename(clean)
    budget = _WALK_FILE_BUDGET
    for d in dirs:
        for root, _sub, files in os.walk(d):
            if base in files:
                return os.path.join(root, base)
            budget -= len(files)
            if budget <= 0:
                return None
    return None


def _encode_image(path, max_side=1024):
    # No tone or colour adjustment of any kind. The picture is resized and re-encoded,
    # nothing else — what the VLM sees is what the file contains.
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_side:
            s = max_side / float(max(w, h))
            im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ----------------------------------------------------------------- timeline

def parse_timeline(raw):
    """timeline_data JSON -> (image_items, other_items). Sorted by slot then order."""
    if not raw:
        return [], []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return [], []
    items = data.get("items") or []

    def key(it):
        return (int(it.get("slot", 999) or 0), int(it.get("order", 999) or 0))

    live = [it for it in items
            if isinstance(it, dict) and it.get("enabled") is not False]
    live.sort(key=key)

    # SLOT is the reference number, not the insertion order. One slot holds one
    # reference and may carry an audio file alongside its picture (a character and
    # that character's voice). Re-ordering the lane rewrites 'slot' while 'order'
    # keeps the original insertion history — so slot is what H3 counts.
    # The Director has no video type: videos and GIFs are stored as "image".
    imgs, others = [], []
    for it in live:
        try:
            it["_pic"] = int(it.get("slot", 0) or 0) + 1
        except Exception:
            it["_pic"] = 1
        kind = (it.get("type") or "").lower()
        val = it.get("value") or ""
        is_img = kind == "image" or (not kind and val.lower().endswith(_MEDIA_EXT_IMAGE))
        (imgs if is_img else others).append(it)
    return imgs, others


def _norm_mode(raw_mode, n_images):
    """Map the Director's mode widget onto a guideline mode."""
    m = (raw_mode or "").strip().upper().replace("-", "").replace("_", "")
    if not m:
        return ("REF2VA" if n_images > 2 else
                "FL2VA" if n_images == 2 else
                "I2VA" if n_images == 1 else "T2VA"), "mode widget was empty"
    if m.startswith("REF"):
        return "REF2VA", ""
    if m in ("T2VA", "T2V"):
        return "T2VA", ""
    if m in ("I2VA", "I2V"):
        return "I2VA", ""
    if m in ("L2VA", "L2V"):
        return "L2VA", ""
    # FL2VA / FLF2VA is the Director's combined text-or-image branch.
    if m.startswith("FL"):
        if n_images >= 2:
            return "FL2VA", ""
        if n_images == 1:
            return "I2VA", "Director mode '{}' with 1 image -> I2VA".format(raw_mode)
        return "T2VA", "Director mode '{}' with no image -> T2VA".format(raw_mode)
    return "T2VA", "unrecognised Director mode '{}' -> T2VA".format(raw_mode)


def select_for_mode(image_items, mode, max_images=4):
    """Pick which timeline images matter for a resolved guideline mode."""
    imgs = list(image_items or [])
    if mode == "T2VA" or not imgs:
        return []
    if mode == "I2VA":
        return imgs[:1]
    if mode == "L2VA":
        return imgs[-1:]
    if mode == "FL2VA":
        return [imgs[0], imgs[-1]] if len(imgs) >= 2 else imgs[:1]
    return imgs[:max_images]          # REF2VA


def load_items(items, max_side=1024):
    """Timeline item dicts -> (b64 list, name list, media-prompt list, notes).

    Each image is resized to a slightly different maximum side. Ollama/llama.cpp
    silently merge same-size images in one message into 'video frames', so the model
    ends up seeing only one of them (ollama/ollama#17321). Differing dimensions
    defeat that merge.
    """
    b64, names, media_prompts, notes, numbers = [], [], [], [], []
    for idx, it in enumerate(items or []):
        name = it.get("value") or ""
        path = resolve_media_path(name)
        if not path:
            notes.append("Could not locate '{}' in the input/output/temp folders.".format(name))
            continue
        try:
            pic_no = it.get("_pic", idx + 1)
            numbers.append(pic_no)
            side = max(320, max_side - idx * 8)
            b64.append(_encode_image(path, max_side=side))
            try:
                from PIL import Image as _I
                with _I.open(path) as _im:
                    _w, _h = _im.size
                notes.append("<Picture {}> {}x{} -> max side {}".format(
                    pic_no, _w, _h, side))
            except Exception:
                pass
            names.append(name)
            mp = (it.get("prompt") or it.get("media_prompt") or "").strip()
            if mp:
                media_prompts.append("{}: {}".format(name, mp))
        except Exception as e:
            notes.append("Failed to read '{}': {}".format(name, e))
    return b64, names, media_prompts, notes, numbers


def read_director(prompt_graph, node_id_hint=""):
    """
    Read the Director's state. Images are NOT loaded here — the caller resolves the
    final mode first (a manual override may differ from the Director's) and then calls
    select_for_mode() + load_items().

    Returns: found, node_id, raw_mode, mode, duration, image_items, notes
    """
    out = {"found": False, "node_id": None, "raw_mode": None, "mode": None,
           "duration": None, "image_items": [], "notes": []}

    nid, node, note = find_director(prompt_graph, node_id_hint)
    if note:
        out["notes"].append(note)
    if not node:
        n_found = len(find_directors(prompt_graph))
        out["notes"].append(
            ("No MiniMaxH3Director found in the graph — falling back to this node's own "
             "widgets. (Is the Director bypassed/muted, or not connected to the output?)")
            if n_found == 0 else
            "Director not selected — falling back to this node's own widgets.")
        return out

    out["found"] = True
    out["node_id"] = nid

    raw_mode = _widget_value(node, "mode")
    duration = _widget_value(node, "duration")
    timeline = _widget_value(node, "timeline_data")
    builder = _widget_value(node, "builder_state")

    if (raw_mode is None or duration is None) and builder:
        try:
            bs = json.loads(builder) if isinstance(builder, str) else builder
            raw_mode = raw_mode if raw_mode is not None else bs.get("mode")
            duration = duration if duration is not None else bs.get("duration")
        except Exception:
            pass

    imgs, others = parse_timeline(timeline)
    if not imgs and builder:
        try:
            bs = json.loads(builder) if isinstance(builder, str) else builder
            imgs, others = parse_timeline(bs)
        except Exception:
            pass

    out["raw_mode"] = raw_mode
    mode, note = _norm_mode(raw_mode, len(imgs))
    out["mode"] = mode
    if note:
        out["notes"].append(note)

    try:
        out["duration"] = int(round(float(duration)))
    except Exception:
        out["duration"] = None
        out["notes"].append("Could not read the Director's duration.")

    # Number the non-image items per kind, in timeline order, so the prompt can cite
    # <Video 2> / <Audio 1> and have the number mean the same thing the Director means.
    # An audio file sharing a slot with a picture belongs to that picture.
    pic_slots = {i.get("_pic") for i in imgs}
    other_labels = []
    for o in others:
        kind = (o.get("type") or "").lower() or "asset"
        name = os.path.basename(str(o.get("value") or "")) or "(unnamed)"
        num = o.get("_pic", "?")
        if num in pic_slots:
            other_labels.append(
                "<Picture {}> also carries {} ({}) — attached to that same reference, "
                "NOT shown to you".format(num, name, kind))
        else:
            other_labels.append("<Picture {}> = {}  ({} — NOT shown to you)".format(
                num, name, kind))
    out["other_labels"] = other_labels

    if others:
        kinds = sorted({(o.get("type") or "?") for o in others})
        out["notes"].append(
            "{} non-image item(s) in the Director timeline ({}) were skipped — "
            "only images are sent to the vision model.".format(len(others), ", ".join(kinds)))

    out["image_items"] = imgs
    return out


def fingerprint(prompt_graph, node_id_hint=""):
    """Stable string of the Director state — used for cache invalidation."""
    nid, node, _note = find_director(prompt_graph, node_id_hint)
    if not node:
        return "no-director"
    keys = ("mode", "duration", "timeline_data", "builder_state")
    return json.dumps([nid] + [str(_widget_value(node, k))[:4000] for k in keys],
                      ensure_ascii=False, sort_keys=True)
