# -*- coding: utf-8 -*-
"""에셋 라이브러리 — 캐릭터·의상·장소·소품·레이아웃·음성을 폴더에 쌓아 두고
드롭다운으로 다시 꺼내 쓰기 위한 저장소.

파일 배치와 `asset.json` 의 모양은 Director Studio(ai2764/Director-Studio)의
`core/library/store.py` 를 그대로 따릅니다. 남의 포맷을 굳이 따르는 이유는,
그 구조가 이미 한 가지 문제를 풀어 놓았기 때문입니다 — `files` 를 리스트가
아니라 `논리 키 → 파일명` 사전으로 두면, "배우 레퍼런스 하나 줘" 라는 요청에
전신 3면도가 있으면 그걸, 없으면 상반신, 없으면 마스터를 자동으로 고를 수
있습니다. `ROLE_KEYS` 가 그 우선순위입니다.

    output/mmh3_library/
      actors/act_a1b2c3d4e5f6/   asset.json  master.png  fullbody_threeview.png
      costumes/cos_…/            asset.json  master.png
      scenes/scn_…/              asset.json  angle_00.png  angle_01.png  …
      props/prp_…/               asset.json  master.png
      layouts/lay_…/             asset.json  layout.png
      voices/voi_…/              asset.json  source.wav  reference.wav

의상을 배우 밑에 넣지 않고 따로 두는 것도 저쪽을 따른 것입니다. 대신 "이 배우가
이 의상을 입은 그림" 은 `layouts` 에 한 장으로 합성해 넣습니다 — 그러면 의상은
의상대로 재사용되고, 조합은 조합대로 남습니다.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

KINDS = ("actors", "costumes", "scenes", "props", "layouts", "voices")

_PREFIX = {
    "actors": "act",
    "costumes": "cos",
    "scenes": "scn",
    "props": "prp",
    "layouts": "lay",
    "voices": "voi",
}

# 역할별 파일 선택 우선순위. 앞에 있는 키부터 찾아서 처음 있는 것을 씁니다.
ROLE_KEYS = {
    "actors": ("fullbody_threeview", "bust_threeview", "asset_sheet", "master"),
    "scenes": ("angle_00", "angle_0", "plate", "master", "scene", "image"),
    "costumes": ("master", "image", "plate", "asset_sheet"),
    "props": ("master", "image", "plate", "asset_sheet"),
    "layouts": ("layout", "master", "image"),
    "voices": ("reference", "source"),
}

NONE_LABEL = "(없음)"

_LABEL_SEP = "  ·  "
_ID_RE = re.compile(r"^(act|cos|scn|prp|lay|voi)_[0-9a-f]{12}$")


# ------------------------------------------------------------------ 경로

def root():
    """`output/mmh3_library`. ComfyUI 밖(테스트)에서는 현재 폴더 기준."""
    try:
        import folder_paths
        base = folder_paths.get_output_directory()
    except Exception:
        base = os.path.abspath("output")
    return os.path.join(base, "mmh3_library")


def kind_dir(kind):
    return os.path.join(root(), kind)


def asset_dir(kind, asset_id):
    return os.path.join(kind_dir(kind), asset_id)


def new_asset_id(kind):
    return "%s_%s" % (_PREFIX.get(kind, kind[:3]), uuid.uuid4().hex[:12])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ 읽기

def load(kind, asset_id):
    """`asset.json` 을 읽습니다. 없으면 None."""
    path = os.path.join(asset_dir(kind, asset_id), "asset.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("id", asset_id)
    data.setdefault("kind", kind)
    data.setdefault("files", {})
    data.setdefault("meta", {})
    return data


def list_assets(kind):
    """그 종류의 에셋 전부. 즐겨찾기가 앞, 그다음 이름순."""
    out = []
    d = kind_dir(kind)
    if not os.path.isdir(d):
        return out
    for entry in sorted(os.listdir(d)):
        if not _ID_RE.match(entry):
            continue
        a = load(kind, entry)
        if a:
            out.append(a)
    out.sort(key=lambda a: (not (a.get("meta") or {}).get("favorite"),
                            (a.get("name") or "").lower(),
                            a.get("created_at") or ""))
    return out


def labels(kind):
    """드롭다운 항목. 첫 줄은 '(없음)'."""
    return [NONE_LABEL] + ["%s%s%s" % (a.get("name") or a["id"], _LABEL_SEP, a["id"])
                           for a in list_assets(kind)]


def all_labels():
    """종류를 가리지 않는 드롭다운. `actors/유키  ·  act_…` 꼴."""
    out = [NONE_LABEL]
    for kind in KINDS:
        for a in list_assets(kind):
            out.append("%s/%s%s%s" % (kind, a.get("name") or a["id"],
                                      _LABEL_SEP, a["id"]))
    return out


def id_from_label(label):
    """드롭다운 라벨에서 에셋 id 만 떼어 냅니다."""
    if not label or label == NONE_LABEL:
        return None
    tail = label.rsplit(_LABEL_SEP, 1)[-1].strip()
    return tail if _ID_RE.match(tail) else None


def kind_from_label(label):
    if not label or label == NONE_LABEL:
        return None
    head = label.split("/", 1)[0]
    return head if head in KINDS else None


def pick_file(asset, file_key=None):
    """쓸 파일 하나를 고릅니다.

    `file_key` 를 주면 그것을, 없거나 'auto' 면 `ROLE_KEYS` 우선순위대로,
    그래도 없으면 `input_` 으로 시작하지 않는 아무 파일이나.
    반환은 `(논리키, 파일명)` 이고 하나도 없으면 `(None, None)`.
    """
    files = {k: v for k, v in (asset.get("files") or {}).items() if v}
    if not files:
        return None, None
    key = (file_key or "").strip()
    if key and key.lower() != "auto":
        if files.get(key):
            return key, files[key]
        # 한 글자 오타만 조용히 고쳐 줍니다. 두 글자부터는 그냥 실패시킵니다.
        near = [c for c in files
                if len(c) == len(key) and sum(a != b for a, b in zip(c, key)) == 1]
        if len(near) == 1:
            return near[0], files[near[0]]
        return None, None
    for k in ROLE_KEYS.get(asset.get("kind"), ()):
        if files.get(k):
            return k, files[k]
    for k in sorted(files):
        if not k.startswith("input_"):
            return k, files[k]
    return None, None


def file_path(asset, filename):
    return os.path.join(asset_dir(asset["kind"], asset["id"]), filename)


def description(asset):
    """H3 의 `<Subject N>` 정의문으로 나갈 영어 설명."""
    meta = asset.get("meta") or {}
    return (meta.get("description") or asset.get("notes") or "").strip()


def signature(kind):
    """드롭다운 캐시 무효화용. 폴더가 바뀌면 값이 달라집니다."""
    d = kind_dir(kind)
    try:
        parts = [d, str(os.path.getmtime(d))]
        for e in sorted(os.listdir(d)):
            p = os.path.join(d, e, "asset.json")
            if os.path.exists(p):
                parts.append("%s:%s" % (e, os.path.getmtime(p)))
        return "|".join(parts)
    except Exception:
        return str(time.time())


# ------------------------------------------------------------------ 쓰기

def find_by_name(kind, name):
    """같은 종류에서 이름이 정확히 같은 에셋. 여럿이면 가장 오래된 것."""
    name = (name or "").strip()
    if not name:
        return None
    hits = [a for a in list_assets(kind) if (a.get("name") or "").strip() == name]
    hits.sort(key=lambda a: a.get("created_at") or "")
    return hits[0] if hits else None


def save(kind, name, files, description_en="", notes="", tags=(),
         favorite=False, meta_extra=None, asset=None):
    """에셋을 만들거나 갱신합니다.

    `files` 는 `{논리키: (확장자, bytes)}`. 같은 키를 다시 쓰면 덮어씁니다.
    `asset` 을 주면 그 에셋에 파일을 얹고, 없으면 새로 만듭니다.
    """
    if kind not in KINDS:
        raise ValueError("kind must be one of %s, got %r" % (list(KINDS), kind))

    creating = asset is None
    if creating:
        asset = {
            "id": new_asset_id(kind),
            "kind": kind,
            "name": (name or "").strip() or "untitled",
            "notes": "",
            "pipeline_id": "comfyui",
            "job_id": "",
            "seed": None,
            "created_at": _now(),
            "files": {},
            "meta": {"source": "mmh3_asset_save", "external": True,
                     "description": "", "tags": [], "favorite": False},
            "urls": {},
            "project_id": None,
        }

    adir = asset_dir(kind, asset["id"])
    os.makedirs(adir, exist_ok=True)

    written = []
    for key, (ext, data) in files.items():
        fname = "%s%s" % (key, ext if ext.startswith(".") else "." + ext)
        with open(os.path.join(adir, fname), "wb") as f:
            f.write(data)
        asset["files"][key] = fname
        written.append(fname)

    meta = asset.setdefault("meta", {})
    if description_en.strip():
        meta["description"] = description_en.strip()
    if notes.strip():
        asset["notes"] = notes.strip()
    tags = [t.strip() for t in tags if t and t.strip()]
    if tags:
        meta["tags"] = sorted(set((meta.get("tags") or []) + tags))
    meta.setdefault("tags", [])
    meta["favorite"] = bool(favorite or meta.get("favorite"))
    if meta_extra:
        meta.update(meta_extra)
    meta.setdefault("description", "")
    asset["updated_at"] = _now()

    with open(os.path.join(adir, "asset.json"), "w", encoding="utf-8") as f:
        json.dump(asset, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return asset, written, creating
