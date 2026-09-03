# -*- coding: utf-8 -*-
"""Shot Settings — everything that describes the WHOLE video, split out of Shot Builder.

    Shot Settings ──settings──► Shot Builder ──brief / spec──► Prompt Writer

Shot Builder draws its cards on a canvas whose height follows the content. Ordinary
widgets sitting above that canvas fight it for space, so the two are separated: this
node holds the plain dropdowns and text boxes, Shot Builder holds only the canvas.
"""

import json

try:
    from ..mmh3 import shotcards, shotlist, styles
except ImportError:  # direct import during tests
    from mmh3 import shotcards, shotlist, styles

CATEGORY = "MiniMax H3/Prompt"

DIALOGUE_MODE = {"auto — 브리프에서 판단": "auto", "대사 없음": "none", "대사 있음": "speech"}


class MMH3_ShotSettings:
    """The whole-video settings for the MiniMax H3 shot builder."""

    DESCRIPTION = (
        "Whole-video settings for the MiniMax H3 shot builder: style, lens, depth of "
        "field, key light, dialogue policy and language, the two sound toggles, and the "
        "prohibitions and requirements. Wire `settings` into MiniMax H3 Shot Builder."
    )

    @classmethod
    def INPUT_TYPES(cls):
        sl = shotlist.labels
        return {
            "required": {
                "style": (styles.style_labels(), {
                    "default": styles.style_labels()[0],
                    "tooltip": "영상 전체의 화풍. [샷 1] 스타일 문장이 여기서 나옵니다.",
                }),
                "lens": (sl(shotlist.LENS), {
                    "default": sl(shotlist.LENS)[0],
                    "tooltip": "초점거리. 광각은 원근이 과장되고, 망원은 배경이 납작해집니다.",
                }),
                "depth_of_field": (sl(shotlist.DEPTH_OF_FIELD), {
                    "default": sl(shotlist.DEPTH_OF_FIELD)[0],
                    "tooltip": "심도. 얕으면 배경이 날아가고 깊으면 다 선명합니다.",
                }),
                "lighting_key": (sl(shotlist.LIGHTING), {
                    "default": sl(shotlist.LIGHTING)[0],
                    "tooltip": "키 라이트의 방향과 성질.",
                }),
                "dialogue_mode": (list(DIALOGUE_MODE), {
                    "default": list(DIALOGUE_MODE)[0],
                    "tooltip": "'대사 없음' 을 고르면 말소리를 넣지 말라는 지시가 들어갑니다.",
                }),
                "dialogue_language": ("STRING", {
                    "default": "Korean",
                    "tooltip": "영상에서 실제로 들릴 대사의 언어입니다. 카드에 다른 언어로 써도 "
                               "이 언어로 번역되어 <d>[언어] ...</d> 안에 들어갑니다.",
                }),
                "include_soundscape": ("BOOLEAN", {
                    "default": True, "tooltip": "환경음·동작음 요약을 넣습니다."}),
                "include_music": ("BOOLEAN", {
                    "default": True, "tooltip": "관객만 듣는 배경음악을 넣습니다."}),
                "must_not": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "절대 일어나면 안 되는 것을 한 줄에 하나씩\n예) 자세를 바꾸지 않는다",
                    "tooltip": "금지 사항 규칙 블록을 켭니다. 원치 않는 동작을 막는 유일한 수단입니다.",
                }),
                "progression": (["끄기", "1회", "2회"], {
                    "default": "끄기",
                    "tooltip": "샷 중간에 '다음 동작' 을 일으킵니다. 동작 이름을 정해주는 "
                               "대신 누가·어느 부위로·어디를 향해만 지정하고, 구체적인 "
                               "동작은 모델이 채웁니다. 이름을 적으면 그것만 반복하고 "
                               "아무것도 안 적으면 아무 일도 안 일어나는 문제의 가운데입니다. "
                               "행위 줄의 참가자가 지정돼야 동작합니다.",
                }),
                "progression_target": (shotcards.target_labels(), {
                    "default": shotcards.target_labels()[0],
                    "tooltip": "전개에서 움직일 사람입니다. '랜덤' 이면 행위 줄의 참가자 "
                               "중에서 시드로 뽑습니다 — 한 칸을 비워두면 후보가 한 명뿐이라 "
                               "항상 그 사람만 나옵니다. 특정 인물을 고르면 행위 줄에 없어도 "
                               "그 사람이 움직입니다.",
                }),
                "progression_seed": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFFF,
                    "tooltip": "전개 조합을 굴리는 시드입니다. LLM seed 와 별개입니다 — "
                               "LLM seed 는 문장 표현만 바꾸지만 이 값은 브리프 내용 자체를 "
                               "바꿉니다. 같은 카드로 다른 전개를 뽑고 싶으면 이걸 올리세요.",
                }),
                "must_happen": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "반드시 일어나야 하는 것을 한 줄에 하나씩\n예) 끝까지 같은 자세를 유지한다",
                    "tooltip": "금지의 반대입니다. 빠지면 안 되는 사건을 한 줄에 하나씩 적으면 "
                               "빠뜨리지 말라는 지시와 함께 브리프에 들어갑니다.",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("settings",)
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, **kw):
        return (json.dumps({k: kw.get(k) for k in (
            "style", "lens", "depth_of_field", "lighting_key", "dialogue_mode",
            "dialogue_language", "include_soundscape", "include_music",
            "must_not", "must_happen", "progression", "progression_seed",
            "progression_target")},
            ensure_ascii=False),)
