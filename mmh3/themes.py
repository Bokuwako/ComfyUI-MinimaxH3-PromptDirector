# -*- coding: utf-8 -*-
"""Theme — 장르 이름 하나. `styles.json` 이 매체를 정하듯 이쪽은 장르를 정합니다.

    스타일 (styles.json)  매체 — 실사 / 2D 애니 / 3D CG / 클레이 …
    테마   (themes.json)  장르 — 그라비아 / 호러 / 사이버펑크 …

둘은 안 싸웁니다. "2D 애니" + "그라비아 화보" 는 애니 화보입니다.

여기에는 조명·구도·의상 표가 없습니다. 예전에는 있었는데, 실제로 재보니 모델이
그 표보다 훨씬 많이 알고 있었습니다 — 장르 설명을 시켰더니 역광과 림라이트, 프레임
인 프레임, 반사 구도, 렌즈와 조리개, 계절별 경향, 소품 목록까지 스스로 말했고,
장소·의상·빛이 서로 어울리는 컨셉도 한 번에 만들었습니다. 표는 그 지식을 대체하는
게 아니라 덮고 있었습니다.

그래서 이 모듈이 하는 일은 장르 이름을 브리프 앞부분에 한 줄 얹는 것뿐입니다.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "themes.json")

_CACHE = {"mtime": None, "data": None}

NONE_LABEL = "없음"


def _load():
    try:
        mtime = os.path.getmtime(_PATH)
    except OSError:
        return {}
    if _CACHE["mtime"] == mtime and _CACHE["data"] is not None:
        return _CACHE["data"]
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}
    data = {k: v for k, v in raw.items()
            if not k.startswith("_") and isinstance(v, dict)}
    _CACHE["mtime"] = mtime
    _CACHE["data"] = data
    return data


def labels():
    """드롭다운 항목. 첫 줄은 '없음'."""
    return [NONE_LABEL] + [v.get("label") or k for k, v in _load().items()]


def get(label):
    if not label or label == NONE_LABEL:
        return {}
    for k, v in _load().items():
        if (v.get("label") or k) == label:
            return v
    return {}


def block(label):
    """브리프에 들어갈 테마 줄. 장르 이름 하나와, 필요할 때만 한 줄."""
    theme = get(label)
    genre = (theme.get("genre") or "").strip()
    if not genre:
        return ""
    out = ["테마: {} ({}). 이 장르가 무엇인지는 네가 안다 — 조명, 구도, 렌즈, 의상, "
           "장소, 인물이 카메라를 대하는 태도를 그 지식대로 골라라. 고른 것들이 서로 "
           "어울려야 한다: 장소에 맞는 의상, 그 시간대에 맞는 빛, 그 공간에서 자연스러운 "
           "자세. 아래 '내용' 과 '카메라' 가 정한 것은 그대로 두고, 그것들이 말하지 않은 "
           "부분만 이 장르답게 채워라.".format(theme.get("label") or label, genre)]
    note = (theme.get("note") or "").strip()
    if note:
        out.append("  " + note)
    return "\n".join(out)
