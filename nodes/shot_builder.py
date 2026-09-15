# -*- coding: utf-8 -*-
"""Shot Builder — the whole authoring surface in one node.

Replaces the Shot Builder + Brief Composer pair. The shot cards are drawn by a custom
LiteGraph widget rather than onDrawForeground, so they take part in normal widget layout
and cannot overlap the dropdowns above them.

    Shot Builder ──brief / spec──► Prompt Writer ──prompt──► Director
                 └──report───────► PreviewAny

Only the settings that describe the whole video stay as ordinary widgets: style, lens,
depth of field, key light, dialogue mode, the two sound toggles and the prohibitions.
Everything per-shot lives on the cards.
"""

import json

try:
    from ..mmh3 import acts, guideline, shotcards, shotlist, styles, themes, validator
except ImportError:  # direct import during tests
    from mmh3 import acts, guideline, shotcards, shotlist, styles, themes, validator

CATEGORY = "MiniMax H3/Prompt"

# The canvas reads its dropdowns from here so the Korean labels and explanations can
# never drift from the sentences this module builds.
try:
    from aiohttp import web as _web
    from server import PromptServer as _PS

    @_PS.instance.routes.get("/mmh3/shotcards/vocab")
    async def _shotcard_vocab(_request):
        def rows(table):
            return [{"key": k, "ko": ko, "tip": tip} for k, ko, tip, _en in table]
        return _web.json_response({
            "viewpoint": rows(shotcards.VIEWPOINT), "angle": rows(shotcards.ANGLE),
            "facing": rows(shotcards.FACING), "size": rows(shotcards.SIZE),
            "shot_type": rows(shotcards.SHOT_TYPE), "motion": rows(shotcards.MOTION),
            "amp": rows(shotcards.AMPLITUDE), "speed": rows(shotcards.SPEED),
            "transition": rows(shotcards.TRANSITION),
            # SHOT_LINK 은 영어 문장이 없는 3열 표라 rows() 를 못 씁니다.
            "shot_link": [{"key": k, "ko": ko, "tip": tip}
                          for k, ko, tip in shotcards.SHOT_LINK],
            "ref_role": rows(shotcards.REF_ROLE),
            "act": acts.rows(acts.ACTS), "act_pos": acts.rows(acts.POSITION),
            "mover": acts.rows(acts.MOVER),
        })
except Exception:  # importable outside ComfyUI (tests)
    pass

DEFAULT_SETTINGS = {
    "style": "", "lens": "", "depth_of_field": "", "lighting_key": "",
    "dialogue_mode": "", "dialogue_language": "Korean",
    "include_soundscape": True, "include_music": True,
    "must_not": "", "must_happen": "",
    "progression": "끄기", "progression_seed": 0, "progression_target": "",
    "theme": "",
}

PROGRESSION = {"끄기": 0, "1회": 1, "2회": 2}

DIALOGUE_MODE = {"auto — 브리프에서 판단": "auto", "대사 없음": "none", "대사 있음": "speech"}

_BLOCK_KO = {
    "CAMERA_LOCK": "카메라 고정", "OPERATOR": "촬영자 / 시점", "PROHIBITION": "금지 사항",
    "SUSTAINED": "지속·반복 동작", "NONVERBAL": "비언어 음성", "VIEWPOINT": "시점 전환",
    "REF_FRAMING": "레퍼런스 각도 분리", "CONTINUITY": "샷 간 연속성",
}
_ORDER = tuple(_BLOCK_KO)

# 구형 `dialogue` 문자열 필드는 화자별 `lines` 로 대체됐고, 카드에는 `acts` 가
# 생겼는데 기본값에는 없어서 새 워크플로우의 첫 카드만 모양이 달랐습니다.
DEFAULT_SHOTS = json.dumps({"version": 1, "shots": [
    {"text": "", "viewpoint": "", "vp_target": "", "size": "", "angle": "",
     "facing": "", "shot_type": "", "motion": "", "amp": "", "speed": "",
     "at": None, "transition": "cut", "acts": [], "lines": []}
], "refs": [{"n": i, "role": ""} for i in range(1, 4)]}, ensure_ascii=False)


def _seconds_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _lines(text):
    out = []
    for raw in (text or "").replace("\r", "").split("\n"):
        s = raw.strip().lstrip("-*·•").strip()
        if s:
            out.append(s)
    return out


def _parse(shots_data):
    """-> (cards, refs, errors)"""
    try:
        d = json.loads(shots_data) if isinstance(shots_data, str) and shots_data.strip() else {}
    except Exception:
        return [], [], ["shots_data 를 읽지 못했습니다 (JSON 오류)."]
    if isinstance(d, list):
        return d, [], []
    shots = d.get("shots")
    refs = d.get("refs")
    return ((shots if isinstance(shots, list) else []),
            (refs if isinstance(refs, list) else []), [])


class MMH3_ShotBuilder:
    """Shot-card authoring surface for the MiniMax H3 prompt writer."""

    DESCRIPTION = (
        "Builds the brief and the shot specification. [+ 샷 추가] stacks shot cards; each "
        "card carries its own Korean prose and its own camera, and from card 2 on a cut "
        "time and transition. The continuity sentence between cards keeps the location, "
        "people, wardrobe and light across every cut. Hover any control for a Korean "
        "explanation. Wire brief and spec into MiniMax H3 Prompt Writer."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 캔버스가 편집합니다. multiline=False 라야 DOM textarea 로 안 바뀝니다.
                "shots_data": ("STRING", {"default": DEFAULT_SHOTS, "multiline": False}),
            },
            "optional": {
                "settings": ("STRING", {
                    "forceInput": True,
                    "tooltip": "MiniMax H3 Shot Settings 노드를 연결하세요. 없으면 기본값으로 "
                               "동작합니다.",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("brief", "spec", "report")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    # ------------------------------------------------------------------ build
    @staticmethod
    def compose(cards, refs, must_not="", dialogue_mode="", language="Korean",
                must_happen="", progression="끄기", progression_seed=0,
                duration=0.0, progression_target="", theme=""):
        parts = []
        tb = themes.block(theme)
        if tb:
            parts.append(tb)
        MMH3_ShotBuilder._last_theme = theme
        body, axes, problems = shotcards.build(
            cards, refs=refs, language=language,
            progression=PROGRESSION.get(progression, 0),
            progression_seed=progression_seed, duration=duration,
            progression_target=shotcards.target_key(progression_target))
        if body:
            parts.append(body)
        _dm = DIALOGUE_MODE.get(dialogue_mode)
        if _dm == "none":
            parts.append("대사는 없다. 단어가 되는 말소리는 절대 넣지 마라.")
        elif _dm == "speech":
            # 시스템 프롬프트에도 speech 블록이 있지만, 그건 36,000자 안의 한 블록입니다.
            # '대사 없음' 만 브리프에 직접 한 줄이 들어가고 '대사 있음' 은 안 들어가서,
            # 정작 샷 내용 옆에는 대사 얘기가 없었습니다. 가까운 지시가 이깁니다.
            parts.append("대사: 이 샷에서 인물들이 실제로 말을 한다. 대사는 사용자가 "
                         "쓰지 않았으니 네가 써라. 위 내용과 행위를 보고, 그 상황에서 "
                         "그 사람이 할 법한 짧은 말을 넣어라. 상황상 말할 거리가 "
                         "없어 보여도 반드시 넣어라 — 신음·숨소리로 대신하지 마라. "
                         "적어도 한 사람이 한 번은 말한다.")
        mn = _lines(must_not)
        if mn:
            parts.append("절대 금지:\n" + "\n".join("- " + m for m in mn))
        mh = _lines(must_happen)
        if mh:
            parts.append("반드시 일어나야 하는 것 — 하나도 빠뜨리지 마라:\n"
                         + "\n".join("- " + m for m in mh))
        return "\n\n".join(p for p in parts if p).strip(), axes, problems

    @staticmethod
    def dialogue_script(cards, language="Korean"):
        """The typed lines, in order, as an English script for the writer.

        One row per line with its own speaker, so the model never has to guess who
        talks when — guessing is what produced "Simultaneously, <Subject 2> says".

        Each row also says whether to copy it or translate it. The cards are typed in
        whatever language is convenient; `language` is what the video is meant to be
        spoken in, so a Korean line under a Japanese setting has to be translated, not
        pasted through and mislabelled <d>[Japanese] 안녕하세요</d>.
        """
        lang = language or "Korean"
        rows, n, need, timed = [], 0, False, False
        for i, c in enumerate(cards, start=1):
            for ln in shotcards.dialogue_lines(c):
                n += 1
                ok = validator.script_matches(ln["text"], lang)
                if ok:
                    how = "copy verbatim, already {}".format(lang)
                elif ok is None:
                    # 문자만으로는 판정이 안 되는 언어 (태국어, 베트남어, 네덜란드어 ...).
                    # 모르면서 "번역하라"고 하면 같은 언어를 번역하라는 지시가 됩니다.
                    how = "in {}".format(lang)
                else:
                    how = "translate into {}".format(lang)
                    need = True
                when = ""
                if ln.get("at") is not None:
                    when = " starting at {}".format(shotcards.clock(ln["at"]))
                    timed = True
                rows.append("{}. [shot {}]{} {} says ({}): {}".format(
                    n, i, when, shotcards.who_label_en(ln["who"]), how, ln["text"]))
        if not rows:
            return ""
        tail = ["Every <d> block is [{}] and holds {} only.".format(lang, lang)]
        # 이 목록이 대사 한 줄을 쓰는 완성된 서식으로 읽힙니다. 여기에 오디오 인용이
        # 없으면 시스템 프롬프트에 있는 인용 규칙이 이 서식에 밀립니다 — 실제로 밀려서
        # <Audio N> 이 detailed_description 에서 통째로 빠졌습니다.
        tail.append(
            "IF a speaker was given a voice reference, name that <Audio N> in the same "
            "sentence as each of their lines, every time they speak and not only in "
            "subject_definitions, and never let one speaker borrow another's. IF no audio "
            "reference was provided, write no <Audio N> at all — never invent one.")
        if timed:
            # 시각이 컷으로 번역되면 화면이 새로 그려집니다. 같은 샷 안의 사건으로 못박습니다.
            tail.append(
                "The times given are when each line starts. Write them into the shot body "
                "as 'At MM:SS.mmm, ...' on the speech event itself. THEY ARE NOT CUTS: do "
                "not open a new [Shot N] for them and do not write any cut phrasing. The "
                "shot runs continuously through all of them, same framing, same place, "
                "same people; only who is speaking changes.")
        if need:
            tail.append(
                "The lines marked 'translate' are written in another language for the "
                "author's convenience. Render them as natural spoken {}, matching the "
                "meaning, tone and roughly the length; do not leave the original words "
                "in and do not put both languages in.".format(lang))
        tail.append(
            "These lines are consecutive, never concurrent. Each one starts only after "
            "the previous one has finished. Give each its own <d> block in this order.")
        return "\n".join(rows + tail)

    @staticmethod
    def build_spec(axes, cards, refs=None, **kw):
        choices = {
            "shot_size": "", "camera_angle": "", "camera_mount": "",
            "lens": kw.get("lens", ""), "depth_of_field": kw.get("depth_of_field", ""),
            "lighting_key": kw.get("lighting_key", ""), "pov_mode": "", "performance": "",
        }
        choices.update(axes)
        script = MMH3_ShotBuilder.dialogue_script(
            cards, kw.get("dialogue_language", "Korean"))
        mode = DIALOGUE_MODE.get(kw.get("dialogue_mode"), "auto")
        return {
            "shot_choices": choices,
            "shot_count": len(cards),
            "cut_times": [c.get("at") for c in cards[1:]],
            "dialogue_rows": [line for card in cards for line in shotcards.dialogue_lines(card)],
            "style": kw.get("style", ""), "custom_style": "", "register": "",
            # `picture_roles` 는 Shot Builder 를 안 쓸 때 Writer 에 직접 적는 칸이라
            # 비워 둡니다 — 여기서 채우면 shotcards 가 이미 브리프에 쓴 역할 문단과
            # roles.py 가 만드는 계약문이 겹쳐서 같은 말이 두 번 나갑니다.
            #
            # 대신 역할 키를 그대로 실어 보냅니다. 비전 패스가 이걸 보고 그림마다
            # 물어볼 항목을 줄이고, 리포트도 역할이 선언됐다는 걸 알 수 있습니다.
            # 예전에는 이 경로가 없어서, 카드에 역할을 다 골라 놔도 리포트가
            # "picture roles: none declared" 라고 했습니다.
            "ref_roles": [{"n": int(r.get("n") or 0), "role": (r.get("role") or "")}
                          for r in (refs or []) if (r.get("role") or "")],
            "picture_roles": "", "extra_directives": "",
            # Lines typed on the cards are quotes, not a suggestion: switch the writer
            # to verbatim so it copies them instead of inventing its own.
            "dialogue_mode": ("verbatim" if (script and mode != "none") else mode),
            "dialogue_language": kw.get("dialogue_language", "Korean"),
            "dialogue_text": script,
            "include_soundscape": bool(kw.get("include_soundscape", True)),
            "include_music": bool(kw.get("include_music", True)),
        }

    # ----------------------------------------------------------------- report
    @classmethod
    def diagnose(cls, brief, spec, cards, refs, problems, must_not="",
                 must_happen=""):
        fired = set(guideline.build_constraints(
            brief, shot_labels=spec["shot_choices"])[1])
        used = [r for r in refs if (r.get("role") or "")]
        rows = ["샷 {}개 · 레퍼런스 {}장 지정".format(len(cards), len(used))]

        th = getattr(cls, "_last_theme", "")
        if th:
            rows[0] += " · 테마 {}".format(th)

        # 무엇을 넘겼는지 눈으로 확인할 수 있어야 합니다. 행위의 참가자가 비어 있으면
        # 브리프에 신원 없는 <사람 A>/<사람 B> 가 나가고 모델이 순번대로 배정하는데,
        # 예전 리포트는 샷 수만 보여줘서 남녀가 뒤집힌 결과를 사전에 알 길이 없었습니다.
        rows.append("")
        rows.append("=== 샷 내용 ===")
        for i, c in enumerate(cards, start=1):
            head = "  샷 {}".format(i)
            vp = c.get("viewpoint") or ""
            if vp:
                head += " · 시점 {}".format(shotcards.ko("viewpoint", vp) or vp)
                if c.get("vp_target"):
                    head += "({})".format(shotcards.who_label(c["vp_target"]))
            nline = len(shotcards.dialogue_lines(c))
            if nline:
                head += " · 대사 {}줄".format(nline)
            if not (c.get("text") or "").strip():
                head += " · [내용 비어 있음]"
            rows.append(head)
            al = [x for x in (c.get("acts") or []) if isinstance(x, dict) and x.get("act")]
            if not al:
                rows.append("      행위 없음 — 자세는 '내용' 이 정합니다")
            for ln in al:
                row = acts.act_row(ln.get("act"))
                name = row[1] if row else ln.get("act")
                s1, s2 = acts.slot_labels(ln.get("act"))
                def nm(v, slot):
                    return shotcards.who_label(v) if v else "!! {} 비어 있음".format(slot)
                if acts.is_solo(ln.get("act")):
                    who = nm(ln.get("a"), s1)
                else:
                    who = "{} ←→ {}".format(nm(ln.get("a"), s1), nm(ln.get("b"), s2))
                rows.append("      {} : {}".format(name, who))

        rows.append("")
        rows.append("=== 활성화된 가이드라인 블록 ===")
        for key in _ORDER:
            rows.append("  [{}] {}".format("ON " if key in fired else "off", _BLOCK_KO[key]))

        warn = list(problems)
        if len(cards) > 1 and "CONTINUITY" not in fired:
            warn.append("! 샷이 2개 이상인데 연속성 블록이 안 켜졌습니다.")
        if any(c.get("viewpoint") == "pov" and not c.get("vp_target") for c in cards):
            warn.append("- POV 인데 시점 주인이 비어 있습니다. 카드에서 고르세요.")
        if not used:
            warn.append("- 레퍼런스 이미지 용도가 하나도 지정되지 않았습니다.")
        if not _lines(must_not):
            warn.append("- 금지 사항이 없습니다. 원치 않는 동작을 막을 수단이 없습니다.")
        if not fired:
            warn.append("- 켜진 규칙 블록이 없습니다. 카드에서 카메라·시점을 고르면 "
                        "해당 규칙이 프롬프트에 들어갑니다.")
        rows.append("")
        rows.append("브리프 {}자 · 대사 {}줄 · 금지 {}개 · 필수 {}개".format(
            len(brief),
            sum(len(shotcards.dialogue_lines(c)) for c in cards),
            len(_lines(must_not)), len(_lines(must_happen))))
        if warn:
            rows.append("")
            rows.append("=== 확인 ===")
            rows.extend("  " + w for w in warn)
        return "\n".join(rows)

    def run(self, shots_data="", settings="", **kw):
        cfg = dict(DEFAULT_SETTINGS)
        try:
            if settings and settings.strip():
                got = json.loads(settings)
                if isinstance(got, dict):
                    cfg.update({k: v for k, v in got.items() if v is not None})
        except Exception:
            pass
        cfg.update({k: v for k, v in kw.items() if v is not None})

        cards, refs, errs = _parse(shots_data)
        cards = shotcards.effective_cards(cards)
        must_not = cfg.get("must_not", "")
        brief, axes, problems = self.compose(
            cards, refs, must_not=must_not, dialogue_mode=cfg.get("dialogue_mode", ""),
            theme=cfg.get("theme", ""),
            language=cfg.get("dialogue_language", "Korean"),
            must_happen=cfg.get("must_happen", ""),
            progression=cfg.get("progression", "끄기"),
            progression_seed=cfg.get("progression_seed", 0),
            progression_target=cfg.get("progression_target", ""))
        spec = self.build_spec(axes, cards, refs=refs, **cfg)
        report = self.diagnose(brief, spec, cards, refs, errs + problems,
                               must_not, cfg.get("must_happen", ""))
        return (brief, json.dumps(spec, ensure_ascii=False), report)
