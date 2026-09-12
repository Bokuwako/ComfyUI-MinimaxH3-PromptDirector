# -*- coding: utf-8 -*-
"""MiniMax H3 Prompt Director — Ollama-backed prompt writer nodes."""

import hashlib
import json
import time

from ..mmh3 import (director_link, guideline, ollama_client, roles,
                    shotlist, styles, validator, vision)

CATEGORY = "MiniMax H3/Prompt"

WRITER_MODES = ["FOLLOW_DIRECTOR"] + guideline.MODES

_FALLBACK_MODELS = [
    # vision-capable (safe for I2VA / FL2VA / L2VA / REF2VA)
    "qwen2.5vl:7b", "qwen2.5vl:32b", "gemma4:12b", "gemma4:26b", "gemma4:e4b",
    "llama3.2-vision:11b", "minicpm-v:8b", "llava:13b", "gemma3:12b",
    # text-only (T2VA only)
    "qwen3:8b",
]

def _safe_int(v, default):
    """Widget values can arrive as NaN/'' when an old workflow is loaded into a
    node whose widget order changed. Never let that crash the run."""
    try:
        i = int(float(v))
        return i
    except (TypeError, ValueError):
        return default


def _safe_float(v, default):
    try:
        f = float(v)
        return default if f != f else f          # NaN check
    except (TypeError, ValueError):
        return default


DIALOGUE_MODES = ["none", "auto", "verbatim"]
KEEP_ALIVE_CHOICES = ["0", "30s", "1m", "5m", "15m", "30m", "1h", "-1"]
DIALOGUE_LANGS = ["English", "Korean", "Japanese", "Chinese", "Spanish",
                  "French", "German", "Portuguese", "Russian"]


def _model_list():
    found = ollama_client.list_models()
    if not found:
        return list(_FALLBACK_MODELS)
    extra = [m for m in _FALLBACK_MODELS if m not in found]
    return found + extra


def _resolve_mode(mode, has_first, has_last, has_ref):
    if mode != "AUTO":
        return mode
    if has_ref:
        return "REF2VA"
    if has_first and has_last:
        return "FL2VA"
    if has_last:
        return "L2VA"
    if has_first:
        return "I2VA"
    return "T2VA"


class MMH3_OllamaPromptWriter:
    """Natural language (+ optional reference images) -> MiniMax H3 spec prompt."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            # Order here IS the order on the node. Grouped the way the shot is actually
            # planned: what to make -> how it is framed -> what is heard -> the engine.
            "required": {
                # ---- 1. 무엇을 만들까
                "brief": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "무엇을 만들지 자연어로 쓰세요. 한국어 가능.\n"
                                   "예) 비 오는 새벽 골목, 우산 든 여자가 뛰어가다 멈춰서 뒤를 돌아본다",
                    "tooltip": "자연어 입력. 어떤 언어로 써도 프롬프트는 영어로 나옵니다.",
                }),
                # ---- 2. 영상 규격
                "mode": (WRITER_MODES, {
                    "default": "FOLLOW_DIRECTOR",
                    "tooltip": "FOLLOW_DIRECTOR = Director의 mode를 그대로 사용. "
                               "AUTO = 연결된 이미지로 판단. 나머지는 강제 지정.",
                }),
                "duration": ("INT", {"default": 0, "min": 0, "max": 60, "step": 1,
                                     "tooltip": "0 = Director의 길이를 사용."}),
                "shot_count": ("INT", {"default": 0, "min": 0, "max": 8, "step": 1,
                                       "tooltip": "0 = 모델이 판단."}),
                "link_to_director": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "MiniMaxH3Director에서 mode·길이·이미지를 그대로 읽어옵니다. "
                               "추가 배선이 필요 없습니다.",
                }),

                # ---- 4. 이미지 판독
                "max_ref_images": ("INT", {
                    "default": 9, "min": 1, "max": 9, "step": 1,
                    "tooltip": "REF2VA 전용. I2VA·L2VA·FL2VA는 각각 첫 1장 / 마지막 1장 / "
                               "첫+마지막 2장으로 고정이라 영향이 없습니다.",
                }),
                "image_max_side": ("INT", {
                    "default": 1024, "min": 512, "max": 2048, "step": 64,
                    "tooltip": "Ollama에 보내기 전 긴 변 크기(px). 어둡거나 디테일이 많은 "
                               "그림은 1024에서 뭉개집니다. 색·명암은 건드리지 않습니다.",
                }),
                "vision_pass": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "쓰기 전에 이미지를 한 장씩 따로 판독합니다. 이미지 1장당 "
                               "Ollama 호출이 1회 늘지만 묘사 누락이 크게 줄어듭니다.",
                }),
                "vision_max_images": ("INT", {
                    "default": 0, "min": 0, "max": 9, "step": 1,
                    "tooltip": "판독할 이미지 수를 따로 제한합니다. 0 = max_ref_images 를 "
                               "그대로 사용. 판독은 1장당 Ollama 호출 1회라, 인물 레퍼런스만 "
                               "읽고 배경은 건너뛰고 싶을 때 낮춰 잡으세요. 앞쪽 N장을 읽고 "
                               "나머지는 모델에는 그대로 전달됩니다.",
                }),

                # ---- 6. Ollama
                "ollama_url": ("STRING", {"default": ollama_client.DEFAULT_URL}),
                "model": (_model_list(), {}),
                "vision_model": (["(작성 모델과 동일)"] + _model_list(), {
                    "default": "(작성 모델과 동일)",
                    "tooltip": "이미지 판독만 이 모델로 합니다. 판독이 끝나면 즉시 "
                               "언로드되므로 두 모델이 동시에 올라가지 않습니다. "
                               "다른 모델을 고르면 작성 단계에는 이미지를 보내지 않고 "
                               "판독 결과만 넘깁니다 — 작성 모델은 비전이 없어도 됩니다.",
                }),
                "temperature": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 2.0,
                                          "step": 0.05}),
                "llm_seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF,
                                     "tooltip": "0 = 매 실행마다 새 결과. 1 이상이면 고정."}),
                "num_ctx": ("INT", {"default": 8192, "min": 2048, "max": 131072,
                                    "step": 1024}),
                "max_tokens": ("INT", {"default": 1200, "min": 256, "max": 8192,
                                       "step": 64}),
                "max_words": ("INT", {
                    "default": 500, "min": 150, "max": 2000, "step": 50,
                    "tooltip": "결과 프롬프트의 목표 단어 수 상한입니다. 하한은 이 값의 "
                               "70%% 로 잡힙니다(500 이면 350~500). 첫 프레임 모드처럼 "
                               "이미지를 말로 다시 적어야 할 때 올리면 판독 내용이 더 "
                               "많이 실립니다. 무작정 올리면 핵심 지시가 묻힐 수 있습니다.",
                }),
                "keep_alive": (KEEP_ALIVE_CHOICES, {
                    "default": "0",
                    "tooltip": "Ollama가 모델을 VRAM에 붙들고 있는 시간. 기본 '0' 은 응답 "
                               "직후 해제입니다 — H3 본체가 VRAM을 거의 다 쓰기 때문에, "
                               "LLM이 남아 있으면 H3가 PCIe 스트리밍으로 밀려 크게 느려집니다. "
                               "LLM만 반복해서 돌릴 때만 올려 잡으세요.",
                }),
                "unload_after": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "응답 직후 Ollama에서 모델을 내려 VRAM을 비웁니다.",
                }),

                # ---- 7. 출력 처리
                "auto_fix": ("BOOLEAN", {"default": True,
                                         "tooltip": "규격 자동 수리 패스를 실행합니다."}),
                "force_english": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "한국어가 섞여 나오면 다시 생성하고, 그래도 남으면 번역 패스를 "
                               "돌립니다. <d> 안의 대사와 \"화면 텍스트\"는 원문 유지.",
                }),
            },
            "optional": {
                # Brief Composer 의 spec 출력. 스타일·샷스펙·소리·역할이 전부 여기 담겨 옵니다.
                "spec": ("STRING", {"default": "", "forceInput": True,
                                    "tooltip": "MMH3 Brief Composer 의 spec 출력을 연결하세요."}),
                "first_frame": ("IMAGE",),
                "last_frame": ("IMAGE",),
                "ref_images": ("IMAGE",),
                "template_prompt": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "완성된 H3 프롬프트를 통째로 붙여넣으세요.\n"
                                   "샷 구성·디테일 밀도·연속성 습관만 따라 씁니다.\n"
                                   "인물·장소·대사·타임스탬프는 복사하지 않습니다.\n"
                                   "쓸 때는 shot_count 를 반드시 지정하세요.",
                    "tooltip": "문서를 어떻게 조립할지. 샷 구조와 서술 습관을 가져옵니다.",
                }),
                "director_node_id": ("STRING", {
                    "default": "",
                    "tooltip": "Director 노드가 여러 개일 때만 필요합니다. 비워두면 "
                               "하나뿐인 Director를 자동으로 찾습니다.",
                }),
            },
            "hidden": {
                "graph_prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("prompt", "mode", "report", "duration", "raw")
    FUNCTION = "run"
    CATEGORY = CATEGORY
    DESCRIPTION = ("Turns a plain-language brief (any language) plus an optional style preset "
                   "and reference images into a MiniMax H3 spec-compliant prompt, using a local "
                   "Ollama model. Wire `prompt` into MiniMaxH3Director.external_prompt_overwrite.")

    @classmethod
    def IS_CHANGED(cls, **kw):
        if _safe_int(kw.get("llm_seed"), 0) == 0:
            return time.time()
        payload = repr(sorted((k, str(v)[:2000]) for k, v in kw.items()
                              if k not in ("first_frame", "last_frame", "ref_images",
                                           "graph_prompt")))
        # The Director's widgets are not our inputs, so hash them in explicitly or a
        # mode/duration/image change over there would never re-trigger this node.
        if kw.get("link_to_director", True):
            payload += director_link.fingerprint(kw.get("graph_prompt"),
                                                 kw.get("director_node_id", "") or "")
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def run(self, brief, mode, duration, shot_count, link_to_director,
            max_ref_images, image_max_side, vision_pass, vision_max_images,
            ollama_url, model, vision_model, temperature, llm_seed, num_ctx,
            max_tokens, max_words, keep_alive,
            unload_after, auto_fix, force_english,
            spec="",
            first_frame=None, last_frame=None, ref_images=None,
            template_prompt="", director_node_id="",
            graph_prompt=None, unique_id=None,
            # Authoring inputs. These live on the Brief Composer now and arrive through
            # `spec`; the defaults keep the node runnable with nothing connected.
            style="", shot_size="", camera_angle="", camera_mount="", lens="",
            depth_of_field="", lighting_key="", pov_mode="", performance="",
            dialogue_mode="none", dialogue_language="English",
            include_soundscape=True, include_music=True,
            dialogue_text="", register="", picture_roles="", custom_style="",
            extra_directives=""):

        # ---- unpack the composer's spec over the authoring defaults
        spec_note = ""
        self._ref_roles = {}
        if isinstance(spec, str) and spec.strip():
            try:
                _s = json.loads(spec)
            except Exception as exc:
                raise RuntimeError("spec is not valid JSON from MMH3 Brief Composer: %s" % exc)
            _c = _s.get("shot_choices", {}) or {}
            shot_size = _c.get("shot_size", shot_size)
            camera_angle = _c.get("camera_angle", camera_angle)
            camera_mount = _c.get("camera_mount", camera_mount)
            lens = _c.get("lens", lens)
            depth_of_field = _c.get("depth_of_field", depth_of_field)
            lighting_key = _c.get("lighting_key", lighting_key)
            pov_mode = _c.get("pov_mode", pov_mode)
            performance = _c.get("performance", performance)
            # extra axes that only exist to switch guideline sections on
            self._extra_axes = {k: _c.get(k, "") for k in ("viewpoint_change", "ref_framing")}
            style = _s.get("style", style)
            custom_style = _s.get("custom_style", custom_style)
            register = _s.get("register", register)
            picture_roles = _s.get("picture_roles", picture_roles)
            # Shot Builder 는 역할 문단을 브리프에 직접 쓰기 때문에 picture_roles 는
            # 비워서 보냅니다. 역할 자체는 이쪽으로 옵니다 — 비전 패스가 그림마다
            # 물어볼 항목을 줄이는 데 씁니다.
            _rr = _s.get("ref_roles")
            if isinstance(_rr, list):
                self._ref_roles = {int(r.get("n") or 0): (r.get("role") or "")
                                   for r in _rr if isinstance(r, dict)}
            extra_directives = _s.get("extra_directives", extra_directives)
            dialogue_mode = _s.get("dialogue_mode", dialogue_mode)
            dialogue_language = _s.get("dialogue_language", dialogue_language)
            dialogue_text = _s.get("dialogue_text", dialogue_text)
            include_soundscape = _s.get("include_soundscape", include_soundscape)
            include_music = _s.get("include_music", include_music)
            spec_note = "spec: composer 연결됨"
        else:
            self._extra_axes = {}
            spec_note = "spec: 미연결 — 샷 스펙 없이 브리프만으로 씁니다"

        model_name = model
        if not model_name:
            raise RuntimeError("No Ollama model selected. Install one with `ollama pull qwen2.5vl:7b`.")
        keep_alive = keep_alive if isinstance(keep_alive, str) and keep_alive.strip() else "5m"

        notes = []
        max_ref = max(1, min(9, _safe_int(max_ref_images, 9)))
        has_first = first_frame is not None
        has_last = last_frame is not None
        has_ref = ref_images is not None
        manual_images = has_first or has_last or has_ref

        # ---- Director link: mode, duration and reference images with no extra wiring
        d = None
        if link_to_director:
            d = director_link.read_director(graph_prompt, node_id_hint=director_node_id)
            notes.extend(d["notes"])
            # IS_CHANGED 는 dynprompt 없이 호출되어 graph_prompt 가 {} 로 들어옵니다.
            # 그래서 Director 의 mode/길이/이미지를 바꿔도 이 노드는 재실행되지 않고
            # 예전 프롬프트가 그대로 하류로 갑니다. 캐시를 강제로 끄면 매 실행마다
            # LLM 을 다시 돌려야 하니, 대신 무엇을 해야 하는지 리포트에 적어 둡니다.
            if _safe_int(llm_seed, 0) > 0:
                notes.append("주의: llm_seed 가 고정이라 이 노드는 캐시됩니다. "
                             "Director 쪽 변경(mode·길이·이미지)은 캐시 판정에 잡히지 "
                             "않으니, Director 를 바꿨으면 llm_seed 를 한 칸 올리세요.")
            if d["found"]:
                notes.insert(0, "Director #{}: mode={} duration={}s timeline images={}".format(
                    d["node_id"], d["raw_mode"], d["duration"], len(d["image_items"])))

        # ---- mode
        if mode == "FOLLOW_DIRECTOR":
            if d and d["found"] and d["mode"]:
                resolved = d["mode"]
            else:
                resolved = _resolve_mode("AUTO", has_first, has_last, has_ref)
                notes.append("mode=FOLLOW_DIRECTOR but no Director state — "
                             "fell back to AUTO -> {}.".format(resolved))
        else:
            resolved = _resolve_mode(mode, has_first, has_last, has_ref)
            if d and d["found"] and d["mode"] and d["mode"] != resolved:
                notes.append("mode widget overrides the Director ({} -> {}).".format(
                    d["mode"], resolved))

        # ---- duration
        duration = _safe_int(duration, 0)
        shot_count = _safe_int(shot_count, 0)
        if duration <= 0:
            if d and d["found"] and d["duration"]:
                duration = int(d["duration"])
            else:
                duration = 6
                notes.append("duration=0 but no Director duration available — using 6s.")
        elif d and d["found"] and d["duration"] and int(d["duration"]) != duration:
            notes.append("duration widget ({}s) differs from the Director ({}s) — "
                         "using {}s.".format(duration, d["duration"], duration))

        # ---- style
        if style.startswith("99."):
            style_dict = styles.custom_style(custom_style)
            style_key = "custom"
        else:
            style_key, style_dict = styles.by_label(style)
        if style_key == "auto":
            style_dict = {}

        # ---- images: connected IMAGE inputs win; otherwise take the Director's uploads.
        images = []
        img_source = "none"
        pic_numbers = []
        if manual_images:
            img_source = "node inputs"
            try:
                if resolved == "REF2VA":
                    images = ollama_client.tensor_to_b64_list(ref_images, max_images=max_ref,
                        max_side=_safe_int(image_max_side, 1024))
                    if has_first:
                        images = ollama_client.tensor_to_b64_list(
                            first_frame, max_images=1,
                            max_side=_safe_int(image_max_side, 1024)) + images
                elif resolved == "FL2VA":
                    images = (ollama_client.tensor_to_b64_list(first_frame, max_images=1,
                                              max_side=_safe_int(image_max_side, 1024))
                              + ollama_client.tensor_to_b64_list(last_frame, max_images=1,
                                              max_side=_safe_int(image_max_side, 1024)))
                elif resolved == "I2VA":
                    images = ollama_client.tensor_to_b64_list(first_frame, max_images=1,
                                              max_side=_safe_int(image_max_side, 1024))
                elif resolved == "L2VA":
                    images = ollama_client.tensor_to_b64_list(last_frame, max_images=1,
                                              max_side=_safe_int(image_max_side, 1024))
            except Exception as e:
                raise RuntimeError("Failed to encode reference image(s): %s" % e)
        elif d and d["found"] and d["image_items"]:
            # Select AFTER the final mode is known, so a manual mode override still
            # picks the right pictures out of the Director's lane.
            chosen = director_link.select_for_mode(d["image_items"], resolved,
                                                   max_images=max_ref)
            images, names, media_prompts, load_notes, pic_numbers = \
                director_link.load_items(
                    chosen, max_side=_safe_int(image_max_side, 1024))
            notes.extend(load_notes)
            d["media_prompts"] = media_prompts
            if len(d["image_items"]) > len(chosen):
                notes.append("{} of {} timeline image(s) used for mode {}.".format(
                    len(chosen), len(d["image_items"]), resolved))
            if images:
                img_source = "Director timeline (" + ", ".join(names) + ")"
                notes.append(roles.slot_report(resolved, names))

        if resolved in ("I2VA", "FL2VA", "L2VA", "REF2VA") and not images:
            raise RuntimeError(
                "Mode {} needs picture(s) but none were found.\n"
                "Either drop them into the MiniMaxH3Director media lane (with "
                "link_to_director on), connect first_frame / last_frame / ref_images, "
                "or set mode to T2VA.".format(resolved))
        notes.append("{}: {} [{}]".format(
            guideline.picture_kind(resolved)["label"].lower(), len(images), img_source))

        # 판독 전용 모델을 쓰면 작성 모델에는 이미지가 가지 않습니다. 그 경우 작성 모델이
        # 텍스트 전용이어도 정상이므로, 아래 가드는 판독 모델 쪽에 걸어야 합니다.
        _vm = (vision_model or "").strip()
        vis_model = "" if (not _vm or _vm.startswith("(")) else _vm
        vis_split = bool(vis_model) and vis_model != model_name
        reader = vis_model if (vis_split and vision_pass) else model_name

        if images:
            can_see = ollama_client.supports_vision(ollama_url, reader)
            if can_see is False:
                raise RuntimeError(
                    "'{}' is a TEXT-ONLY model — it cannot see the {} reference image(s) "
                    "this {} prompt needs, and would silently invent them.\n"
                    "Install a vision model and select it:\n"
                    "    ollama pull qwen2.5vl:7b        # 6GB, 빠름\n"
                    "    ollama pull gemma4:12b          # 7.6GB, Gemma 계열 비전\n"
                    "(others: gemma4:26b, gemma4:e4b, llama3.2-vision:11b, minicpm-v:8b)\n"
                    "Or set mode to T2VA if you really want a text-only prompt."
                    .format(reader, len(images), resolved))
            if can_see is None:
                notes.append("could not verify vision support for '{}' — if the prompt "
                             "ignores the images, use a vision model (qwen2.5vl:7b)."
                             .format(reader))

        # ---- Picture roles: say what each reference is FOR, and that none is a frame.
        parsed_roles, role_problems = roles.parse(picture_roles, n_images=len(images))
        roles_block = roles.build_block(parsed_roles, len(images), resolved) if images else ""
        line = roles.summary_line(parsed_roles, role_problems)
        if line:
            notes.extend(line.splitlines())
        elif images and getattr(self, "_ref_roles", None):
            _named = ", ".join("{}={}".format(n, r)
                               for n, r in sorted(self._ref_roles.items()) if r)
            notes.append("picture roles: {} (샷 카드에서 지정됨)".format(_named))
        elif images:
            notes.append("picture roles: none declared — the model decides what each "
                         "image is for")

        # ---- Shot specification: only the axes the operator actually set.
        shot_choices = {
            "shot_size": shot_size, "camera_angle": camera_angle,
            "camera_mount": camera_mount, "lens": lens,
            "depth_of_field": depth_of_field, "lighting": lighting_key,
            "pov_mode": pov_mode, "performance": performance,
        }
        shot_block = shotlist.build_block(shot_choices, register)
        _sl = shotlist.summary_line(shot_choices, register)
        if _sl:
            notes.append(_sl)
        notes.append(spec_note)
        # viewpoint_change / ref_framing carry no shotlist text of their own; they exist
        # so guideline._AXIS_TRIG switches the matching constraint sections on.
        shot_choices.update(getattr(self, "_extra_axes", {}) or {})

        # ---- Stage 0: look at the pictures, one at a time, before writing anything.
        vision_note = ""
        inventories = []
        # 판독 대상은 따로 제한할 수 있습니다. 0 이면 모델에 가는 장수 그대로.
        _vmax = _safe_int(vision_max_images, 0)
        vision_images = images if _vmax <= 0 else images[:_vmax]
        if len(vision_images) < len(images):
            notes.append("vision_pass: {} of {} image(s) read; the rest are still sent "
                         "to the model unread.".format(len(vision_images), len(images)))
        # 판독 전용 모델. 고르지 않으면 지금까지처럼 작성 모델이 판독까지 합니다.
        vis_used = False

        if vision_images and vision_pass:
            _vw = ollama_client.check_context_budget(
                _safe_int(num_ctx, 8192), 800, [vision.INVENTORY_SYSTEM],
                1, _safe_int(image_max_side, 1024))
            if _vw:
                notes.append("vision_pass " + _vw.splitlines()[0])
            shots_seen = []
            for i, img in enumerate(vision_images, start=1):
                try:
                    seen = validator.strip_wrapper(ollama_client.chat(
                        base_url=ollama_url,
                        model=(vis_model if vis_split else model_name),
                        system=vision.INVENTORY_SYSTEM,
                        user=vision.question(i, len(vision_images),
                                            (getattr(self, '_ref_roles', None) or {}).get(i, '')),
                        images=[img],
                        options={"temperature": 0.1,
                                 "num_ctx": _safe_int(num_ctx, 8192),
                                 "num_predict": 800,
                                 "top_p": 0.8},
                        keep_alive=("0" if vis_split else keep_alive))) or ""
                except Exception as exc:                      # never kill the run for this
                    seen = ""
                    notes.append("vision_pass: <Picture {}> failed ({}) — falling back to "
                                 "the single-call reading.".format(i, exc))
                if seen.strip():
                    shots_seen.append(seen.strip())
            if shots_seen:
                vision_note = vision.build_note(shots_seen, resolved)
                inventories = shots_seen
                vis_used = vis_split
                notes.append("vision_pass: {} picture(s) inventoried ({} chars){}.".format(
                    len(shots_seen), sum(len(x) for x in shots_seen),
                    " by " + vis_model if vis_split else ""))
            if vis_split:
                # 두 모델이 동시에 올라가면 16GB 급에서는 버티지 못합니다.
                ok, detail = ollama_client.unload(ollama_url, vis_model)
                notes.append("vision_model unloaded: {} — {}".format(
                    "yes" if ok else "FAILED", detail))

        writing_brief = brief
        if (template_prompt or "").strip():
            notes.append("template: {} chars used as a structural exemplar{}".format(
                len(template_prompt.strip()),
                "" if _safe_int(shot_count, 0) > 0
                else " — set shot_count, or the template's shot count will be copied"))

        _cons_text, _cons_used = guideline.build_constraints(
            brief + "\n" + (extra_directives or ""), shot_choices)
        notes.append("constraints: {} ({} tokens)".format(
            ", ".join(_cons_used) if _cons_used else "none triggered",
            len(_cons_text) // 4))

        # 오디오 파일이 하나도 없으면 오디오 챕터(약 1,200 토큰)를 통째로 뺍니다.
        # Director 목록의 항목은 "(audio — NOT shown to you)" 처럼 종류가 붙어 옵니다.
        _other = (d.get("other_labels") if d and d.get("found") else None) or []
        _has_audio = any("audio" in str(x).lower() for x in _other)
        if not _has_audio:
            notes.append("no audio reference — the audio rules block was left out "
                         "(about 1,200 tokens saved).")

        system = guideline.build_system_prompt(
            mode=resolved, duration=float(duration), shot_hint=int(shot_count),
            style=style_dict, dialogue_policy=dialogue_mode,
            soundscape_on=bool(include_soundscape), music_on=bool(include_music),
            extra_directives=extra_directives, dialogue_language=dialogue_language,
            n_images=len(images), template_prompt=template_prompt,
            roles_block=roles_block, shot_block=shot_block,
            brief=brief + "\n" + (extra_directives or ""),
            shot_labels=shot_choices,
            other_items=_other,
            picture_numbers=pic_numbers,
            max_words=_safe_int(max_words, 500),
            has_audio_refs=_has_audio)

        user = guideline.build_user_message(
            brief=writing_brief, mode=resolved, duration=float(duration),
            dialogue_text=dialogue_text if dialogue_mode == "verbatim" else "",
            dialogue_language=dialogue_language,
            style_label=style_dict.get("label", "auto") if style_dict else "auto",
            skip_image_checklist=bool(vision_note))

        if vision_note:
            user += "\n\n" + vision_note

        if d and d["found"] and d.get("media_prompts") and not manual_images:
            user += "\n\nPER-IMAGE NOTES FROM THE DIRECTOR TIMELINE:\n" + "\n".join(
                d["media_prompts"])

        options = {
            "temperature": _safe_float(temperature, 0.6),
            "num_ctx": _safe_int(num_ctx, 8192),
            "num_predict": _safe_int(max_tokens, 1200),
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        }
        if _safe_int(llm_seed, 0) > 0:
            options["seed"] = _safe_int(llm_seed, 0)

        # Always check the budget, not only on the vision-pass path. A prompt that does
        # not fit is silently truncated by Ollama, and the symptom is a rule that works
        # one run and vanishes the next — with no error anywhere.
        # 계산은 여기 한 번뿐입니다. 예전에는 아래에서 같은 인자로 한 번 더 부르고
        # notes 에 두 번 넣어서, 같은 경고가 리포트 위아래로 두 번 나왔습니다.
        budget_warning = ollama_client.check_context_budget(
            _safe_int(num_ctx, 8192), _safe_int(max_tokens, 1200),
            [system, user], len(images), _safe_int(image_max_side, 1024))
        if budget_warning:
            notes.insert(0, budget_warning)

        def _call(sys_prompt, usr, with_images=True):
            text = ollama_client.chat(
                base_url=ollama_url, model=model_name, system=sys_prompt, user=usr,
                images=(images or None) if with_images else None,
                options=options, keep_alive=keep_alive)
            # Ollama reports what it really tokenised; the pre-check is only len/4.
            _u = ollama_client.usage_note(_safe_int(num_ctx, 8192),
                                          _safe_int(max_tokens, 1200))
            if _u:
                notes.append(_u)
            return text

        def _finish(text):
            if auto_fix:
                c, r = validator.normalize(
                    text, mode=resolved, duration=float(duration),
                    dialogue_expected=(dialogue_mode != "none"),
                    enforce_instruction=True,
                    ref2va_sections=(resolved == "REF2VA"), n_images=len(images),
                    expected_shots=max(0, _safe_int(shot_count, 0)))
                if not c:
                    # Nothing was repaired, so the model's raw text goes straight to the
                    # Director. Say so at the TOP of the report — buried at the bottom
                    # this line is easy to miss, and the prompt downstream is unchecked.
                    return validator.strip_wrapper(text), (
                        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                        "!! REPAIR FAILED — the RAW model output is being passed  !!\n"
                        "!! through unchecked. Do not trust this prompt.          !!\n"
                        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n" + r)
                return c, r
            return (validator.strip_wrapper(text),
                    "auto_fix disabled — raw model output passed through.")

        # 판독을 전용 모델이 이미 끝냈다면 작성 단계에 이미지를 다시 보낼 이유가 없습니다.
        # 가이드라인이 이미 "인벤토리를 보고 쓰라" 고 말하고 있어서, 이미지를 같이 주면
        # 토큰만 쓰고 판독 결과와 어긋날 여지만 남습니다. 작성 모델은 비전이 없어도 됩니다.
        send_images = not vis_used
        if vis_used:
            notes.append("writing pass: text only — the inventory replaces the pictures "
                         "({} image(s) not resent).".format(len(images)))
        raw = _call(system, user, with_images=send_images)
        clean, report = _finish(raw)

        # ---- English lock: regenerate, then translate, rather than only warning.
        if force_english:
            leaks = validator.find_non_english(clean)
            if leaks:
                notes.append("non-English leaked ({}) — regenerating with a stricter "
                             "language directive.".format(", ".join(leaks[:3])))
                retry_system = system + "\n\n" + guideline.ENGLISH_RETRY_DIRECTIVE
                retry_opts = dict(options)
                retry_opts["temperature"] = min(_safe_float(temperature, 0.6), 0.35)
                raw2 = ollama_client.chat(
                    base_url=ollama_url, model=model_name, system=retry_system,
                    user=user + "\n\n" + guideline.ENGLISH_RETRY_DIRECTIVE,
                    images=images or None, options=retry_opts, keep_alive=keep_alive)
                clean2, report2 = _finish(raw2)
                if clean2 and not validator.find_non_english(clean2):
                    raw, clean, report = raw2, clean2, report2
                    notes.append("retry produced clean English.")
                else:
                    # Last resort: a structure-preserving translation pass.
                    translated = ollama_client.chat(
                        base_url=ollama_url, model=model_name,
                        system=guideline.ENGLISH_REPAIR_SYSTEM,
                        user=guideline.build_english_repair_message(clean2 or clean),
                        images=None, options={"temperature": 0.0,
                                              "num_ctx": _safe_int(num_ctx, 8192),
                                              "num_predict": _safe_int(max_tokens, 1200)},
                        keep_alive=keep_alive)
                    clean3, report3 = _finish(translated)
                    if clean3 and len(validator.find_non_english(clean3)) < len(
                            validator.find_non_english(clean2 or clean)):
                        raw, clean, report = translated, clean3, report3
                        notes.append("translation pass applied.")
                    else:
                        notes.append("STILL non-English after 2 passes — use a bigger model "
                                     "(qwen2.5vl:32b) or lower temperature.")

        # ---- did what the vision pass saw actually reach the prompt?
        for problem in validator.check_inventory_coverage(clean, inventories):
            notes.append("[warn] not carried over: " + problem)

        # ---- contradictions the spec forbids
        for problem in validator.check_structure(clean):
            notes.append("[warn] structure: " + problem)

        # ---- do the lines fit in the running time? 넘치면 모델이 음절을 삼킵니다.
        for problem in validator.check_dialogue_rate(clean, duration):
            notes.append("[warn] 대사 길이: " + problem)

        # ---- 사건 순서가 시각으로 박혀 있는가, 상대 표현뿐인가
        for problem in validator.check_event_order(clean):
            notes.append("[warn] 사건 순서: " + problem)

        # ---- is the camera described with the spec's vocabulary, or by analogy?
        for problem in validator.check_camera_vocabulary(clean):
            notes.append("[warn] camera wording: " + problem)
        for problem in validator.check_reserved_camera_verbs(clean):
            notes.append("[warn] camera wording: " + problem)

        # ---- camera lock: did the model obey a "camera never moves" brief?
        # Look at what the user typed and the extra directives — the lock can be
        # stated in either.
        brief_for_lint = "\n".join(
            x for x in (brief, extra_directives) if x)
        for problem in validator.check_camera_lock(clean, brief_for_lint):
            notes.append("[warn] camera lock: " + problem)

        if unload_after:
            ok, detail = ollama_client.unload(ollama_url, model_name)
            notes.append("unload_after: {} — {}".format(
                "VRAM freed" if ok else "FAILED", detail))
        else:
            resident = ollama_client.loaded_models(ollama_url)
            if resident:
                notes.append("still resident in Ollama: {} (keep_alive={}). "
                             "Turn on unload_after to free VRAM for H3."
                             .format(", ".join(resident), keep_alive))

        header = "\n".join("[link] " + n for n in notes)
        if budget_warning:
            header = ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                      + budget_warning +
                      "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n"
                      + header)
        tail = ""
        if inventories:
            # Show what the vision pass actually saw. Without this there is no way to
            # tell a bad reading of the picture from a good reading badly used.
            tail = "\n\n" + "\n\n".join(
                "======== VISION PASS — <Picture {}> ========\n{}".format(i, t.strip())
                for i, t in enumerate(inventories, start=1))
        return (clean, resolved, (header + "\n\n" + report).strip() + tail,
                int(duration), raw)


class MMH3_PromptValidator:
    """Run the deterministic spec repair on any prompt string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "forceInput": False}),
                "mode": (["T2VA", "I2VA", "FL2VA", "L2VA", "REF2VA"], {"default": "T2VA"}),
                "duration": ("INT", {"default": 6, "min": 1, "max": 60, "step": 1}),
                "dialogue_expected": ("BOOLEAN", {"default": True}),
                # 이 둘이 없으면 normalize() 의 REF2VA 섹션 검사와 샷 수 검사가
                # 조용히 무력화됩니다. Writer 는 넘겨주는데 여기만 빠져 있었습니다.
                "n_images": ("INT", {
                    "default": 0, "min": 0, "max": 9, "step": 1,
                    "tooltip": "프롬프트가 참조하는 레퍼런스 이미지 장수. REF2VA 에서 "
                               "<Picture N> 개수와 subject 정의를 대조하는 데 씁니다. "
                               "0 이면 그 검사를 건너뜁니다."}),
                "expected_shots": ("INT", {
                    "default": 0, "min": 0, "max": 8, "step": 1,
                    "tooltip": "있어야 할 [Shot N] 개수. 0 이면 검사하지 않습니다."}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "report")
    FUNCTION = "run"
    CATEGORY = CATEGORY
    DESCRIPTION = ("Checks and repairs field layout, shot numbering, cut timestamps and the "
                   "reference-alignment instruction line. No model call, no network.")

    def run(self, prompt, mode, duration, dialogue_expected, n_images=0,
            expected_shots=0):
        clean, report = validator.normalize(
            prompt, mode=mode, duration=float(duration),
            dialogue_expected=bool(dialogue_expected),
            enforce_instruction=True,
            ref2va_sections=(mode == "REF2VA"),
            n_images=_safe_int(n_images, 0),
            expected_shots=max(0, _safe_int(expected_shots, 0)))
        if not clean:
            return (validator.strip_wrapper(prompt), report)
        return (clean, report)


class MMH3_ImageDescribe:
    """Vision-only helper: see exactly what the VLM reads from a reference image."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "ollama_url": ("STRING", {"default": ollama_client.DEFAULT_URL}),
                "model": (_model_list(), {}),
                "question": ("STRING", {
                    "multiline": True,
                    "default": "Describe this frame for a video prompt: visual style, subject "
                               "identity (hair, eyes, skin, every garment and its colour, "
                               "accessories), pose, framing, camera height, lighting direction, "
                               "background and key props. English only, no interpretation.",
                }),
                "temperature": ("FLOAT", {"default": 0.2, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 600, "min": 64, "max": 4096, "step": 32}),
                "keep_alive": (KEEP_ALIVE_CHOICES, {
                    "default": "0",
                    "tooltip": "Ollama가 모델을 VRAM에 붙들고 있는 시간. '0' = 응답 직후 즉시 "
                               "해제. 자유 입력이던 것을 목록으로 바꿨습니다 — 오타가 조용히 "
                               "통과해서 모델이 계속 상주하는 일이 있었습니다.",
                }),
            },
            "optional": {
                "model_override": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("description",)
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, image, ollama_url, model, question, temperature, max_tokens,
            keep_alive, model_override=""):
        model_name = (model_override or "").strip() or model
        images = ollama_client.tensor_to_b64_list(image, max_images=1)
        if not images:
            raise RuntimeError("No image received.")
        out = ollama_client.chat(
            base_url=ollama_url, model=model_name,
            system="You are a precise visual describer. Report only what is visibly present.",
            user=question, images=images,
            options={"temperature": float(temperature), "num_predict": int(max_tokens)},
            keep_alive=keep_alive or "5m")
        return (validator.strip_wrapper(out) or out.strip(),)


class MMH3_StyleDirective:
    """Emit a style block as text — useful for feeding extra_directives or reviewing presets."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"style": (styles.style_labels(),
                                       {"default": styles.style_labels()[1]})}}

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("style_line", "full_directive")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, style):
        _key, sd = styles.by_label(style)
        lines = []
        for k in ("style_line", "render", "lighting", "camera", "motion",
                  "soundscape", "music", "avoid"):
            if sd.get(k):
                lines.append("{}: {}".format(k, sd[k]))
        return (sd.get("style_line", ""), "\n".join(lines))
