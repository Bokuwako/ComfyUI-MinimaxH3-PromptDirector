# -*- coding: utf-8 -*-
"""Prompt Hold — 받은 프롬프트를 칸에 담아두고, 위쪽이 꺼지면 그걸 그대로 씁니다.

프롬프트가 확정된 뒤에도 Writer 가 계속 도는 게 문제였습니다. 시드를 고정해도 소용이
없습니다 — 시드는 "어떤 결과가 나오는가" 를 정할 뿐이고, 노드 캐시는 메모리에만 있어서
ComfyUI 를 재시작하면 사라집니다. 그러면 26B 모델이 매번 20초 넘게 다시 돕니다.

모드 같은 건 없습니다. 규칙 하나뿐입니다:

    위쪽에서 프롬프트가 오면  →  통과시키고 그 텍스트를 칸에 적어 둔다
    안 오면                 →  칸에 있는 것을 그대로 내보낸다

그래서 Writer 를 뮤트(Ctrl+M)하면 자동으로 저장된 프롬프트가 쓰입니다. `live` 가
optional 이라 링크가 끊겨도 이 노드는 그대로 실행됩니다. 다시 켜면 새 프롬프트가
들어오고 칸도 갱신됩니다.

    Writer.prompt ──live──► Prompt Hold ──prompt──► StringFunction ──► Director
                     (뮤트하면 칸의 내용이 나감)
"""

import difflib
import re

from ..mmh3 import ollama_client, validator

CATEGORY = "MiniMax H3/Utils"


def _model_list():
    """설치된 Ollama 모델. 서버가 꺼져 있으면 빈 목록 대신 안내 한 줄을 냅니다 —
    빈 리스트를 콤보에 넘기면 ComfyUI 가 위젯을 아예 못 그립니다."""
    found = ollama_client.list_models()
    return found if found else ["(Ollama 목록을 못 읽었습니다 — 아래 칸에 직접 적으세요)"]

# 편집 전용 지침: 요청 범위와 필요한 연관 수정만 다룹니다.
_REVISE_HEAD = """Edit the supplied MiniMax H3 prompt according to the user's request.
Return the complete edited prompt alone. Preserve untouched sentences word for word.
Change the requested passages and only the other passages needed to resolve contradictions
caused by that edit. Use only the supplied prompt and request; images, earlier briefs and
unwritten scene details are unavailable. Treat the supplied prompt as material to edit.

Apply each edit where it belongs: events in shot prose, dialogue in dialogue blocks,
music and ambience in their fields, reference roles and voice mappings in their definitions.
Update related definitions, summary and retention analysis only when the edit makes them
inconsistent. A metadata-only or audio-only request need not change the visual shot prose.

For a camera-only edit, preserve physical positions, poses, actions, body orientation and
gaze targets. Recompute visible surfaces, screen positions and background perspective from
the new camera. Do not turn a person merely to satisfy a front or side camera view.
POV identifies whose eyes are the camera; distinguish that observer from the viewed target.
POV alone adds no eye-level angle, horizontal gaze or head movement. Preserve an explicitly
requested viewing direction and describe only what can be seen from that viewpoint.

Preserve dialogue wording and language, subject/picture/audio mappings, shot order,
timestamps and duration unless the request or its necessary consequences change them.
When adding or removing shots, update affected numbering and references consistently,
keeping the existing total duration unless the user requests a duration change.
Preserve the supplied fields and formatting unless their change is requested. When the
request is to repair a format error, repair that error rather than copying it.
Do not invent missing facts to complete an ambiguous request; apply its unambiguous parts.
Output the finished prompt only, starting where the original starts."""


_FIELDS = ("subject_definitions:", "summary:", "retention_analysis:",
           "detailed_description:", "overall_soundscape:", "non_diegetic_music:")


def _sentences(text):
    """문장 단위로 쪼갭니다. 줄바꿈 위치는 무시합니다 — 모델이 줄을 다시 접었다는
    이유만으로 '바뀐 곳' 이 수십 개로 늘어나면 diff 가 쓸모없어집니다."""
    flat = " ".join((text or "").split())
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', flat) if s.strip()]


def _by_field(text):
    """필드 이름 -> 그 필드의 본문. 어디가 바뀌었는지 이름으로 말해 주기 위한 것."""
    out, cur, buf = {}, "(머리말)", []
    for line in (text or "").split("\n"):
        # 첫 줄은 "integrated_multimodal_description: subject_definitions:" 처럼
        # 두 이름이 붙어 나오므로, 줄 앞이 아니라 줄 안에서 찾습니다.
        hit = next((f for f in _FIELDS if f in line), None)
        if hit:
            out[cur] = "\n".join(buf)
            cur, buf = hit.rstrip(":"), [line.split(hit, 1)[1]]
        else:
            buf.append(line)
    out[cur] = "\n".join(buf)
    return out


def _clip(s, n=220):
    """리포트 한 줄의 길이를 제한하되, 잘랐다는 것을 보이게 합니다.

    표시 없이 자르면 문장이 단어 중간에서 끝나 모델이 철자를 깨뜨린 것처럼
    보입니다. 실제로 그렇게 오해한 적이 있습니다 — 프롬프트는 멀쩡한데
    리포트만 잘린 것이었습니다.
    """
    s = s or ""
    return s if len(s) <= n else s[:n].rstrip() + " …(생략)"


def diff_note(before, after, max_items=6):
    """무엇이 바뀌었는지 사람이 읽을 수 있게. 글자 수만으로는 '요청한 것만 고쳤는지'
    를 알 수 없어서, 실제로 갈아치워진 문장을 보여 줍니다."""
    a_f, b_f = _by_field(before), _by_field(after)
    lines, shown, more = [], 0, 0
    for name in list(dict.fromkeys(list(a_f) + list(b_f))):
        a, b = _sentences(a_f.get(name, "")), _sentences(b_f.get(name, ""))
        if a == b:
            continue
        lines.append("  [{}]".format(name))
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
            if tag == "equal":
                continue
            if shown >= max_items:
                more += (i2 - i1) + (j2 - j1)
                continue
            for s in a[i1:i2]:
                lines.append("    - " + _clip(s))
            for s in b[j1:j2]:
                lines.append("    + " + _clip(s))
            shown += 1
    if not lines:
        return "  바뀐 문장이 없습니다 — 요구사항이 반영되지 않았을 수 있습니다."
    if more:
        lines.append("    … 그 밖에 {}군데 더".format(more))
    return "\n".join(lines)


def revision_notes(before, after):
    """Report observable changes; do not pretend to judge the user's intent."""
    notes = []
    if len(after) < len(before) * 0.5:
        notes.append("[warn] 원본의 절반 이하로 짧아졌습니다. 요청한 삭제·축약인지 확인하세요.")
    old_fields, new_fields = _by_field(before), _by_field(after)
    removed = [f for f in old_fields if f != "(머리말)" and f not in new_fields]
    if removed:
        notes.append("[변경] 삭제된 필드: " + ", ".join(removed))
    patterns = (
        ("샷 순서", r"\[Shot\s+\d+\]"),
        ("전환 시각", r"\bAt\s+\d+:\d+(?:\.\d+)?"),
        ("대사", r"<d>.*?</d>"),
        ("참조 번호", r"<(?:Subject|Picture|Audio)\s+\d+>"),
    )
    for label, pattern in patterns:
        old = re.findall(pattern, before, re.S)
        new = re.findall(pattern, after, re.S)
        if label == "참조 번호":
            old, new = sorted(set(old)), sorted(set(new))
        if old != new:
            notes.append("[변경] {}: {} → {}".format(label, _clip(str(old)), _clip(str(new))))
    old_warnings = list(dict.fromkeys(validator.check_structure(before)))
    new_warnings = list(dict.fromkeys(validator.check_structure(after)))
    notes.extend("[새 구조 경고] " + w for w in new_warnings if w not in old_warnings)
    notes.extend("[기존 구조 경고] " + w for w in new_warnings if w in old_warnings)
    notes.extend("[해결된 구조 경고] " + w for w in old_warnings if w not in new_warnings)
    return notes


def revise_system(prompt_text):
    """편집용 시스템 프롬프트.

    규격은 붙이지 않습니다. 고칠 프롬프트가 이미 형식의 실물이고, 편집은 그걸
    보고 따라 하면 되는 일입니다. `prompt_text` 는 지금 쓰지 않지만, 나중에
    프롬프트 종류에 따라 한 줄을 더할 자리로 남겨 둡니다.
    """
    return _REVISE_HEAD


class MMH3_PromptFreeze:
    """Pass a prompt through and remember it; emit the remembered one when none arrives."""

    DESCRIPTION = (
        "Remembers the last prompt that came through and emits it whenever nothing new "
        "arrives — so muting the writer is all it takes to stop the LLM running. There "
        "is no mode to set. Fixing the seed does not achieve this: a seed decides what "
        "comes out, not whether the node runs, and the node cache is memory-only so a "
        "restart re-runs everything anyway. The text is stored in the workflow, so it "
        "survives a restart, and you can edit it by hand."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_text": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "한 번 돌리면 여기가 자동으로 채워집니다.\n"
                                   "위쪽 노드를 뮤트(Ctrl+M)하면 이 텍스트가 그대로 나갑니다.",
                    "tooltip": "받은 프롬프트가 실행 때마다 여기 갱신됩니다. 워크플로우에 "
                               "저장되므로 재시작해도 남습니다. 직접 고쳐 써도 되고, 그 "
                               "상태로 위쪽을 뮤트해두면 고친 내용이 쓰입니다.",
                }),
                "revise": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "고칠 곳을 한국어로 쓰고 실행하세요. 예)\n"
                                   "너무 멀리서 찍힘. 어깨와 얼굴만 나오는 클로즈업으로.\n"
                                   "적용되면 이 칸은 자동으로 비워집니다.",
                    "tooltip": "위쪽이 꺼져 있을 때만 동작합니다. 위 프롬프트를 여기 적은 "
                               "대로 고쳐서 다시 위 칸에 저장하고, 이 칸은 비웁니다. "
                               "비어 있으면 LLM 을 호출하지 않습니다.",
                }),
                "revise_url": ("STRING", {
                    "default": ollama_client.DEFAULT_URL,
                    "tooltip": "수정에 쓸 Ollama 주소.",
                }),
                # 빈 문자열 칸이면 무엇을 적어야 할지 알 수가 없습니다. Writer 와 같이
                # 설치된 모델을 읽어 드롭다운으로 냅니다. Ollama 가 꺼져 있으면 목록이
                # 비므로, 직접 적을 수 있는 칸을 아래에 따로 둡니다.
                "revise_model": (_model_list(), {
                    "tooltip": "수정에 쓸 모델. 편집만 하는 일이라 큰 모델이 아니어도 "
                               "됩니다 — 이미지도 안 보내고 46,000자 가이드라인도 안 "
                               "읽습니다. 목록에 없으면 아래 칸에 태그를 직접 적으세요.",
                }),
                "revise_model_override": ("STRING", {
                    "default": "",
                    "tooltip": "여기에 적으면 위 드롭다운보다 우선합니다. ComfyUI 시작 "
                               "뒤에 설치한 모델처럼 목록에 안 뜨는 것을 쓸 때.",
                }),
                "revise_temperature": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.5, "step": 0.05,
                    "tooltip": "편집이라 낮게 둡니다. 높이면 요청하지 않은 곳까지 다시 씁니다.",
                }),
            },
            "optional": {
                # optional 이라야 위쪽을 뮤트했을 때 링크가 사라져도 이 노드가 실행됩니다.
                # required 였다면 "입력이 없다" 로 검증에서 막힙니다.
                "live": ("STRING", {"forceInput": True,
                                    "tooltip": "MiniMax H3 Prompt Writer 의 prompt 출력을 "
                                               "연결하세요. 이 노드를 뮤트하면 아래 칸의 "
                                               "텍스트가 대신 쓰입니다."}),
            },
            # 저장 파일에 박히는 워크플로우를 이 실행의 프롬프트로 고치기 위한 것입니다.
            # 아래 _stamp() 주석 참고.
            "hidden": {"extra_pnginfo": "EXTRA_PNGINFO", "prompt": "PROMPT",
                       "unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "source", "previous")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    @staticmethod
    def _stamp(text, extra_pnginfo, prompt, unique_id):
        """이 실행의 프롬프트를 저장 파일의 워크플로우에 박아 넣습니다.

        칸을 채우는 것은 프론트엔드가 `executed` 이벤트를 받은 뒤입니다. 그런데
        저장 노드가 파일에 쓰는 워크플로우는 **Queue 를 누른 순간** 프론트엔드가
        보낸 스냅샷이라, 거기에는 아직 이전 실행의 값이 들어 있습니다. 그래서
        영상에서 워크플로우를 다시 불러오면 프롬프트가 한 번 뒤처져 있었고,
        저화질로 뽑고 나중에 업스케일로 다시 돌리면 다른 결과가 나왔습니다.

        ComfyUI 는 EXTRA_PNGINFO 와 PROMPT 를 실행 내내 같은 객체로 넘깁니다
        (execution.py 의 hidden 입력 처리). 이 노드는 저장 노드보다 위에 있으니,
        여기서 고쳐 두면 저장 노드가 고쳐진 것을 씁니다.
        """
        nid = str(unique_id) if unique_id is not None else ""
        # 1) 프론트엔드가 다시 불러오는 쪽 — 드래그해서 여는 워크플로우.
        try:
            for node in ((extra_pnginfo or {}).get("workflow") or {}).get("nodes") or []:
                if str(node.get("id")) != nid:
                    continue
                wv = node.get("widgets_values")
                if isinstance(wv, list) and wv:
                    wv[0] = text
                elif isinstance(wv, dict):
                    wv["prompt_text"] = text
                else:
                    node["widgets_values"] = [text]
                named = node.get("widgets_values_named")
                if isinstance(named, dict):
                    named["prompt_text"] = text
        except Exception:
            pass                      # 메타데이터 때문에 생성을 죽이지는 않습니다
        # 2) API 형식 쪽 — 스크립트로 다시 돌릴 때 읽는 것.
        try:
            node = (prompt or {}).get(nid)
            if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                node["inputs"]["prompt_text"] = text
        except Exception:
            pass

    @staticmethod
    def _revise(text, request, url, model, temperature):
        """LLM 에게 프롬프트를 고치게 합니다 -> (새 텍스트, 문제 목록).

        문제가 하나라도 있으면 원본을 그대로 씁니다. 반쯤 망가진 프롬프트를 조용히
        내보내는 것보다, 안 고쳐진 채로 리포트에 이유가 적히는 편이 낫습니다.
        """
        if not model.strip():
            return text, ["수정에 쓸 모델이 정해지지 않았습니다 — revise_model 드롭다운에서 "
                          "고르거나 revise_model_override 에 태그를 적어 주세요."]
        user = "\n".join([
            "아래는 완성된 MiniMax H3 프롬프트다.",
            "",
            "=== 프롬프트 시작 ===",
            text,
            "=== 프롬프트 끝 ===",
            "",
            "요청: " + request,
            "",
            # 마지막 줄은 모델이 가장 가까이서 읽는 자리입니다. 여기서 보존을
            # 앞세우면 보존만 하고 끝납니다 — 실제로 한 글자도 안 바뀐 채로
            # 돌아왔습니다. 할 일을 먼저 말합니다.
            "요청을 반영하고, 요청이 건드리지 않은 문장은 그대로 두고, "
            "프롬프트 전체를 다시 출력하라.",
        ])
        # 컨텍스트는 이 편집에 실제로 필요한 만큼만 잡습니다. 예전에는 32768 을
        # 고정으로 잡았는데, 재 보니 4% 만 쓰고 있었습니다. 27B 급 모델에서 그
        # 차이는 KV 캐시 몇 GB 이고, 그만큼을 돌려주면 같은 16GB 카드에 한 단계
        # 위 양자화가 들어갑니다 — 낮은 양자화에서 나오는 공백 붙은 단어
        # (thethree, Thefloor)가 거기서 사라집니다.
        sysp = revise_system(text)
        need_in = ollama_client.estimate_text_tokens(sysp + user)
        predict = max(1024, min(4096, int(len(text) / 3) + 512))
        ctx = need_in + predict + 512                      # 여유 512
        ctx = max(4096, min(32768, -(-ctx // 1024) * 1024))  # 1024 단위로 올림
        try:
            out = ollama_client.chat(
                base_url=url, model=model, system=sysp, user=user,
                # 반복 페널티는 여기서 1.0 (비활성) 이어야 합니다. 이 노드가 하는 일은 입력을
                # 글자 그대로 다시 뱉는 것인데, 페널티는 정확히 그 반대를 시킵니다.
                # 1.1 로 뒀더니 " the" 같은 최빈 토큰이 계속 깎여 공백 없는 "the" 가
                # 뽑혔고, 결과에 thethree / Thefloor / thefigure 가 나왔습니다.
                options={"temperature": float(temperature), "num_ctx": ctx,
                         "num_predict": predict, "top_p": 0.9,
                         "repeat_penalty": 1.0},
                keep_alive="0", return_metadata=True)
            out, completion = out
        except Exception as exc:
            return text, ["수정 호출이 실패했습니다: {}".format(exc)]

        out = (validator.strip_wrapper(out) or "").strip()
        if not out:
            return text, ["수정 결과가 비어 있습니다."]
        if completion.get("done_reason") == "length" or completion.get("done") is False:
            return text, ["모델 출력이 완료되지 않았습니다. 원본을 유지합니다. 출력 길이 제한과 모델 응답 상태를 확인하세요."]
        if _sentences(out) == _sentences(text):
            return text, ["수정 전후의 문장이 같습니다. 이미 요청과 일치하는지 또는 요청이 반영되지 않은 것인지 확인하세요."]
        return out, []

    def run(self, prompt_text, revise="", revise_url="", revise_model="",
            revise_model_override="", revise_temperature=0.3, live=None,
            extra_pnginfo=None, prompt=None, unique_id=None):
        saved = (prompt_text or "").strip()
        fresh = live.strip() if isinstance(live, str) else ""
        want = (revise or "").strip()
        # 직접 적은 쪽이 이깁니다. 드롭다운이 안내 문구뿐일 때도 여기로 빠져나갑니다.
        #
        # 다만 override 는 위젯 밀림의 착지점이 되기 쉽습니다. 이 칸을 추가하면서 옛
        # 노드의 값이 한 칸씩 밀려 온도 "0.3" 이 여기 들어왔고, 그게 모델 이름으로
        # 쓰여 호출이 조용히 실패했습니다. 모델 태그로 볼 수 없는 값은 버립니다.
        override = (revise_model_override or "").strip()
        if override and not any(c.isalpha() for c in override):
            override = ""
        model = override or (revise_model or "").strip()
        if model.startswith("("):     # 드롭다운의 "목록을 못 읽었습니다" 안내 문구
            model = ""

        if fresh:
            # 위쪽이 살아 있으면 그쪽이 이깁니다. 방금 새로 만든 프롬프트를 예전에 적어 둔
            # 요구사항으로 고쳐 버리면, 무엇이 반영된 결과인지 알 수 없게 됩니다.
            self._stamp(fresh, extra_pnginfo, prompt, unique_id)
            note = "새 프롬프트 ({}자) — 칸과 저장 메타데이터에 기록했습니다".format(len(fresh))
            if want:
                note += ("\n요구사항은 이번에 쓰지 않았습니다 — 위쪽 Writer 를 뮤트한 뒤 "
                         "실행하세요.")
            return {"ui": {"captured": [fresh]}, "result": (fresh, note, saved)}

        if saved and want:
            new, problems = self._revise(
                saved, want, revise_url or ollama_client.DEFAULT_URL,
                model, revise_temperature)
            if problems:
                return (saved, "수정하지 않았습니다:\n  - " + "\n  - ".join(problems), saved)
            self._stamp(new, extra_pnginfo, prompt, unique_id)
            note = "요구사항을 적용했습니다 ({}자 → {}자)\n  요청: {}\n\n{}".format(
                len(saved), len(new), " ".join(want.split())[:80],
                diff_note(saved, new))
            for w in revision_notes(saved, new):
                note += "\n  " + w
            # clear_revise 를 받으면 프론트엔드가 요구사항 칸을 비웁니다. 안 비우면
            # 다음 실행에서 같은 수정이 또 얹힙니다.
            return {"ui": {"captured": [new], "clear_revise": [True]},
                    "result": (new, note, saved)}

        if saved:
            return (saved,
                    "위쪽이 꺼져 있어 저장된 것을 사용했습니다 ({}자)".format(len(saved)),
                    saved)

        # 둘 다 비었으면 조용히 빈 문자열을 흘려보내지 않습니다. 빈 프롬프트는 훨씬
        # 하류에서 훨씬 알아보기 어려운 형태로 터집니다.
        raise RuntimeError(
            "Prompt Hold: 내보낼 프롬프트가 없습니다.\n"
            "위쪽 Prompt Writer 를 켜고 한 번 실행하거나, prompt_text 칸에 직접 "
            "붙여넣으세요.")
