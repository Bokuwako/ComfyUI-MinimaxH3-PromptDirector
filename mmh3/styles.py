# -*- coding: utf-8 -*-
"""Style dictionary loader. Edit mmh3/styles.json to add your own styles."""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "styles.json")

_CACHE = {"mtime": None, "data": None}


def _load():
    try:
        mtime = os.path.getmtime(_PATH)
    except OSError:
        return {}
    if _CACHE["mtime"] == mtime and _CACHE["data"] is not None:
        return _CACHE["data"]
    with open(_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    data = {k: v for k, v in raw.items()
            if not k.startswith("_") and isinstance(v, dict)}
    _CACHE["mtime"] = mtime
    _CACHE["data"] = data
    return data


def style_labels():
    """Dropdown entries, in file order, plus a custom slot."""
    data = _load()
    labels = [v.get("label", k) for k, v in data.items()]
    labels.append("99. Custom (아래 custom_style 텍스트 사용)")
    return labels


def by_label(label):
    """Return (key, style_dict). Unknown label -> ('auto', auto-entry)."""
    data = _load()
    for k, v in data.items():
        if v.get("label", k) == label:
            return k, v
    return "auto", data.get("auto", {})


def custom_style(text):
    return {
        "label": "custom",
        "style_line": (text or "").strip().split("\n")[0].strip(),
        "render": (text or "").strip(),
        "lighting": "", "camera": "", "motion": "",
        "soundscape": "", "music": "", "avoid": "",
    }


def all_styles():
    return _load()
