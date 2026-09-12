# -*- coding: utf-8 -*-
"""에셋 라이브러리 패널이 쓰는 HTTP 라우트.

노드는 에셋을 '고르기'만 합니다. 이름을 고치고, 설명을 다시 쓰고, 지우는 일은
큐를 누르는 것과 아무 상관이 없어야 하므로 여기서 처리합니다 — 패널에서 클릭
하면 바로 반영되고, 다음 큐 때 노드가 `IS_CHANGED` 로 알아챕니다.

ComfyUI 의 PromptServer 를 가져올 수 있을 때만 등록됩니다. 테스트에서 이
모듈을 그냥 import 하면 아무 일도 일어나지 않습니다.
"""

import json
import logging
import os
import shutil

_LOG = logging.getLogger("mmh3")

try:
    from aiohttp import web
    from server import PromptServer
    _server = PromptServer.instance
except Exception:      # headless / 테스트 / 아주 오래된 ComfyUI
    web = None
    _server = None

try:
    from .mmh3 import library
except ImportError:
    from mmh3 import library

_THUMB_SIDE = 320


def _safe_asset_dir(kind, asset_id):
    """라이브러리 밖으로 새어 나가는 경로를 막습니다."""
    if kind not in library.KINDS:
        return None
    if not library._ID_RE.match(asset_id or ""):
        return None
    d = os.path.realpath(library.asset_dir(kind, asset_id))
    root = os.path.realpath(library.root())
    if os.path.commonpath([d, root]) != root or not os.path.isdir(d):
        return None
    return d


def _card(asset):
    files = {k: v for k, v in (asset.get("files") or {}).items() if v}
    meta = asset.get("meta") or {}
    key, _ = library.pick_file(asset)
    return {
        "id": asset["id"],
        "kind": asset["kind"],
        "name": asset.get("name") or asset["id"],
        "description": meta.get("description") or "",
        "notes": asset.get("notes") or "",
        "tags": meta.get("tags") or [],
        "favorite": bool(meta.get("favorite")),
        "files": sorted(files),
        "cover": key,
        "created_at": asset.get("created_at") or "",
        "label": "%s/%s%s%s" % (asset["kind"], asset.get("name") or asset["id"],
                                library._LABEL_SEP, asset["id"]),
    }


def _register():
    routes = _server.routes

    def _json(handler):
        async def wrapped(request):
            try:
                return web.json_response(await handler(request))
            except ValueError as exc:
                return web.json_response({"error": str(exc)}, status=400)
            except Exception as exc:                      # noqa: BLE001
                _LOG.exception("mmh3 library route failed")
                return web.json_response({"error": str(exc)}, status=500)
        wrapped.__name__ = handler.__name__
        return wrapped

    async def _body(request):
        try:
            return await request.json()
        except Exception:
            return {}

    @routes.get("/mmh3_library/list")
    @_json
    async def library_list(request):
        want = request.rel_url.query.get("kind") or ""
        kinds = [want] if want in library.KINDS else list(library.KINDS)
        items = []
        for kind in kinds:
            items.extend(_card(a) for a in library.list_assets(kind))
        return {"kinds": list(library.KINDS), "items": items,
                "root": library.root()}

    @routes.get("/mmh3_library/image")
    async def library_image(request):
        q = request.rel_url.query
        kind, asset_id = q.get("kind", ""), q.get("id", "")
        adir = _safe_asset_dir(kind, asset_id)
        if adir is None:
            return web.json_response({"error": "no such asset"}, status=404)
        asset = library.load(kind, asset_id)
        if asset is None:
            return web.json_response({"error": "no such asset"}, status=404)
        _, fname = library.pick_file(asset, q.get("key") or "")
        if not fname:
            return web.json_response({"error": "no image"}, status=404)
        real = os.path.realpath(os.path.join(adir, fname))
        if os.path.commonpath([real, adir]) != adir or not os.path.isfile(real):
            return web.json_response({"error": "no image"}, status=404)

        if q.get("thumb") and os.path.splitext(real)[1].lower() in (
                ".png", ".jpg", ".jpeg", ".webp"):
            thumb = os.path.join(adir, ".thumb_%s.jpg" % os.path.splitext(fname)[0])
            try:
                if (not os.path.exists(thumb)
                        or os.path.getmtime(thumb) < os.path.getmtime(real)):
                    from PIL import Image
                    im = Image.open(real).convert("RGB")
                    im.thumbnail((_THUMB_SIDE, _THUMB_SIDE), Image.LANCZOS)
                    im.save(thumb, format="JPEG", quality=82)
                return web.FileResponse(thumb)
            except Exception:
                pass       # 썸네일을 못 만들면 원본을 그냥 준다
        return web.FileResponse(real)

    @routes.post("/mmh3_library/update")
    @_json
    async def library_update(request):
        b = await _body(request)
        kind, asset_id = b.get("kind", ""), b.get("id", "")
        if _safe_asset_dir(kind, asset_id) is None:
            raise ValueError("no such asset")
        asset = library.load(kind, asset_id)
        if asset is None:
            raise ValueError("no such asset")

        if "name" in b:
            name = (b.get("name") or "").strip()
            if not name:
                raise ValueError("이름은 비울 수 없습니다")
            asset["name"] = name
        meta = asset.setdefault("meta", {})
        if "description" in b:
            meta["description"] = (b.get("description") or "").strip()
        if "notes" in b:
            asset["notes"] = (b.get("notes") or "").strip()
        if "tags" in b:
            raw = b.get("tags")
            if isinstance(raw, str):
                raw = raw.split(",")
            meta["tags"] = sorted({t.strip() for t in (raw or []) if t and t.strip()})
        if "favorite" in b:
            meta["favorite"] = bool(b.get("favorite"))

        path = os.path.join(library.asset_dir(kind, asset_id), "asset.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asset, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return {"ok": True, "item": _card(library.load(kind, asset_id))}

    @routes.post("/mmh3_library/delete")
    @_json
    async def library_delete(request):
        b = await _body(request)
        kind, asset_id = b.get("kind", ""), b.get("id", "")
        adir = _safe_asset_dir(kind, asset_id)
        if adir is None:
            raise ValueError("no such asset")
        shutil.rmtree(adir)
        return {"ok": True, "deleted": asset_id}

    @routes.post("/mmh3_library/open_folder")
    @_json
    async def library_open_folder(request):
        b = await _body(request)
        kind, asset_id = b.get("kind", ""), b.get("id", "")
        target = _safe_asset_dir(kind, asset_id) if asset_id else library.root()
        if target is None or not os.path.isdir(target):
            raise ValueError("no such folder")
        if os.name == "nt":
            os.startfile(target)               # noqa: S606
            return {"ok": True, "path": target}
        raise ValueError("이 기능은 Windows 에서만 됩니다")

    _LOG.info("mmh3: library routes registered under /mmh3_library/")


if _server is not None and web is not None:
    _register()
