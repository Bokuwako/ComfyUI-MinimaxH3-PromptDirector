# -*- coding: utf-8 -*-
"""에셋 라이브러리 노드 두 개.

    이미지 생성 ──► Asset Save ──► output/mmh3_library/ ──► Asset Load ──► <Picture N>
                                                                      └──► <Subject N> 정의문

Save 는 같은 종류에 같은 이름이 이미 있으면 거기에 파일을 얹습니다. 그래서 마스터를
한 번 뽑아 저장하고, 나중에 3면도를 같은 이름으로 저장하면 한 에셋 안에 둘 다 쌓입니다.
새 에셋을 강제로 만들고 싶으면 이름을 바꾸거나 `always_new` 를 켜면 됩니다.

Load 의 `file_key` 는 비워 두는 게 보통입니다 — 비어 있으면 `library.ROLE_KEYS` 의
우선순위대로, 배우면 전신 3면도 → 상반신 → 시트 → 마스터 순으로 알아서 고릅니다.
"""

import io
import os

try:
    from ..mmh3 import library
except ImportError:  # 테스트에서 직접 import 할 때
    from mmh3 import library

CATEGORY = "MiniMax H3/Library"

_SAVE_KINDS = ("actors", "costumes", "scenes", "props", "layouts")


def _png_bytes(frame):
    """[H,W,C] float 0..1 → PNG bytes."""
    import numpy as np
    from PIL import Image

    arr = np.clip(np.asarray(frame) * 255.0 + 0.5, 0, 255).astype("uint8")
    if arr.shape[-1] == 4:
        arr = arr[..., :3]
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _batch(image):
    """ComfyUI IMAGE 텐서를 프레임 리스트로."""
    import numpy as np

    arr = image
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    arr = np.asarray(arr)
    if arr.ndim == 3:
        arr = arr[None, ...]
    return [arr[i] for i in range(arr.shape[0])]


class MMH3_AssetSave:
    """이미지를 라이브러리에 에셋으로 저장합니다."""

    DESCRIPTION = (
        "IMAGE 를 output/mmh3_library 아래에 에셋으로 저장합니다. 같은 종류에 같은 "
        "이름이 있으면 그 에셋에 파일을 얹습니다. 배치로 여러 장이 들어오면 "
        "file_key 뒤에 _00, _01 이 붙습니다 — 장소 멀티앵글을 한 번에 저장할 때 씁니다."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {
                    "tooltip": "저장할 그림. 배치로 여러 장이면 한 에셋 안에 "
                               "여러 파일로 들어갑니다."}),
                "kind": (list(_SAVE_KINDS), {
                    "default": "actors",
                    "tooltip": "actors 배우 · costumes 의상 · scenes 장소 · "
                               "props 소품 · layouts 구도 스틸(Picture 1 용)."}),
                "name": ("STRING", {
                    "default": "",
                    "tooltip": "에셋 이름. 같은 종류에 같은 이름이 이미 있으면 "
                               "새로 만들지 않고 그 에셋에 파일을 더합니다."}),
                "file_key": ("STRING", {
                    "default": "master",
                    "tooltip": "이 그림이 그 에셋에서 맡는 역할. 배우는 master / "
                               "fullbody_threeview / bust_threeview, 장소는 angle "
                               "또는 plate, 레이아웃은 layout 을 씁니다. 배치면 "
                               "뒤에 _00, _01 이 붙습니다."}),
                "description_en": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": "영어 설명. H3 의 <Subject N> 정의문으로 그대로 "
                               "나갑니다. 비워 두면 기존 설명을 유지합니다."}),
            },
            "optional": {
                "tags": ("STRING", {
                    "default": "",
                    "tooltip": "쉼표로 구분. 나중에 찾기 위한 것이라 지금 비워 둬도 "
                               "됩니다."}),
                "notes": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": "나만 보는 메모. 프롬프트에는 안 나갑니다."}),
                "favorite": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "드롭다운 맨 위로 올립니다."}),
                "always_new": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "이름이 같아도 무조건 새 에셋을 만듭니다. 같은 인물의 "
                               "다른 버전을 나란히 두고 고르고 싶을 때."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("asset_id", "report")
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    def run(self, images, kind, name, file_key, description_en,
            tags="", notes="", favorite=False, always_new=False):
        frames = _batch(images)
        if not frames:
            raise ValueError("MMH3_AssetSave: 저장할 그림이 없습니다.")

        key = (file_key or "").strip() or "master"
        payload = {}
        if len(frames) == 1:
            payload[key] = (".png", _png_bytes(frames[0]))
        else:
            for i, f in enumerate(frames):
                payload["%s_%02d" % (key, i)] = (".png", _png_bytes(f))

        target = None if always_new else library.find_by_name(kind, name)
        asset, written, created = library.save(
            kind, name, payload,
            description_en=description_en or "",
            notes=notes or "",
            tags=(tags or "").split(","),
            favorite=favorite,
            asset=target,
        )

        report = "\n".join([
            "%s  %s" % ("새 에셋" if created else "기존 에셋에 추가",
                        asset["id"]),
            "종류   %s" % kind,
            "이름   %s" % asset.get("name"),
            "파일   %s" % ", ".join(written),
            "보유   %s" % ", ".join(sorted(k for k, v in asset["files"].items() if v)),
            "위치   %s" % library.asset_dir(kind, asset["id"]),
        ])
        return (asset["id"], report)


class MMH3_AssetLoad:
    """라이브러리에서 에셋을 꺼냅니다."""

    DESCRIPTION = (
        "저장해 둔 에셋을 드롭다운으로 골라 그림과 영어 설명을 꺼냅니다. image 는 "
        "<Picture N> 레퍼런스로, description 은 <Subject N> 정의문으로 씁니다. "
        "새로 저장한 에셋은 브라우저를 새로고침해야 목록에 나타납니다."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset": (library.all_labels(), {
                    "tooltip": "종류/이름 · id. 목록은 브라우저를 새로고침할 때 "
                               "갱신됩니다."}),
            },
            "optional": {
                "file_key": ("STRING", {
                    "default": "",
                    "tooltip": "비워 두면 역할에 맞는 것을 알아서 고릅니다 — 배우는 "
                               "전신 3면도 → 상반신 → 시트 → 마스터 순. 특정 파일을 "
                               "쓰려면 그 논리 키를 적으세요 (예: angle_03)."}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image", "description", "name", "asset_id")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, asset, file_key=""):
        kind = library.kind_from_label(asset)
        return "%s|%s|%s" % (asset, file_key,
                             library.signature(kind) if kind else "")

    def run(self, asset, file_key=""):
        if not asset or asset == library.NONE_LABEL:
            raise ValueError(
                "MMH3_AssetLoad: 에셋을 고르세요. 목록이 비어 있으면 아직 저장된 "
                "에셋이 없는 것이고, 방금 저장했다면 브라우저를 새로고침하세요.")

        kind = library.kind_from_label(asset)
        asset_id = library.id_from_label(asset)
        if not kind or not asset_id:
            raise ValueError("MMH3_AssetLoad: 항목을 알아볼 수 없습니다 — %r" % asset)

        data = library.load(kind, asset_id)
        if data is None:
            raise ValueError(
                "MMH3_AssetLoad: %s/%s 를 찾을 수 없습니다. 폴더가 지워졌거나 "
                "이름이 바뀌었습니다." % (kind, asset_id))

        key, fname = library.pick_file(data, file_key)
        if not fname:
            have = ", ".join(sorted(k for k, v in (data.get("files") or {}).items() if v))
            raise ValueError(
                "MMH3_AssetLoad: %s 에 쓸 그림이 없습니다. file_key=%r, 보유=[%s]"
                % (asset_id, file_key, have))

        path = library.file_path(data, fname)
        if not os.path.exists(path):
            raise ValueError("MMH3_AssetLoad: 파일이 없습니다 — %s" % path)

        import numpy as np
        import torch
        from PIL import Image, ImageOps

        img = Image.open(path)
        img = ImageOps.exif_transpose(img).convert("RGB")
        arr = np.asarray(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr)[None, ...]

        return (tensor, library.description(data), data.get("name") or "", asset_id)
