# -*- coding: utf-8 -*-
"""Vocabulary and assembly for the shot-card builder.

A shot card is one entry the user added with [+ 샷 추가]. It holds their Korean prose
plus the camera choices for that shot only. This module turns a list of cards into

  * the Korean brief the writer reads, with the trigger vocabulary guaranteed and the
    continuity sentence written between every pair of shots, and
  * the axis tokens guideline._AXIS_TRIG needs to switch the right sections on.

Every option is (key, 한글 라벨, 한글 설명, English directive). The Korean label and
description are what the canvas UI shows and what it puts in a hover tooltip; the English
directive is what reaches the model.
"""

try:
    from . import acts
except ImportError:
    import acts

# (key, 한글 라벨, 한글 툴팁, 영어 지시문)

VIEWPOINT = [
    ("", "지정 안 함", "시점을 지정하지 않습니다. 모델이 정합니다.", ""),
    # 라벨에서 "제3자" 를 뺐습니다. 한글 라벨은 대괄호로 브리프에 같이 나가는데,
    # 이 항목의 뜻은 "관찰자가 하나 더 있다" 가 아니라 "카메라 자리에 아무도 없다" 입니다.
    # 실제로 관찰자를 세우고 싶으면 시점=1인칭 POV + 대상=지켜보는 제3자 를 씁니다.
    # `제3의 인물` 이라는 라벨이 구경꾼을 그리게 만든 전례가 있어 미리 갈라 둡니다.
    ("objective", "관찰 시점 (사람 없음)",
     "카메라 자리에 아무도 없습니다. 아무도 렌즈를 보지 않습니다. 관찰자를 실제로 "
     "세우려면 '1인칭 POV' + 대상 '지켜보는 제3자' 를 쓰세요.",
     "an observing camera with no character at the camera position; nobody looks into the lens"),
    ("shoulder", "어깨너머", "특정 인물의 어깨와 뒤통수가 화면 앞쪽에 걸칩니다.",
     "an over-the-shoulder framing with {who}'s shoulder and the back of their head in the near foreground"),
    ("subjective", "밀착 시점", "인물의 눈은 아니고, 머리 옆에 바짝 붙은 카메라입니다.",
     "a subjective camera held close beside {who}'s head without becoming their eyes"),
    # 공식 가이드에서 POV 는 카메라 모션 표의 한 줄입니다 — "POV | The subject's point
    # of view", Static Shot 이나 Arc Shot 과 같은 층이고, 샷은 "a medium-wide shot
    # frames ..." 같은 구도 명사구로 엽니다.
    #
    # 예전에는 여기에 "'a medium shot' 으로 시작하지 마라" 를 포함한 700자짜리 작성
    # 지시가 들어 있었습니다. 그건 스펙이 요구하는 오프닝 구도를 금지하는 말이라 —
    # 그리고 guideline.py 가 시키는 것과도 반대라 — 그냥 무시당했습니다. 이제 POV
    # 자체를 그 오프닝 구도 명사구로 씁니다. 다른 사이즈 항목과 같은 모양이니 알아서
    # 첫머리 자리에 들어가고, "먼저 써라" 라고 명령할 필요가 없습니다.
    #
    # 높이는 자세가 정합니다. 서 있는 사람의 POV 인데 "카메라는 그의 엉덩이 높이에"
    # 로 나온 적이 있어서, 무엇을 보고 있는지가 아니라 자세를 기준으로 못박습니다.
    ("pov", "1인칭 POV",
     "카메라가 그 인물의 눈입니다. 그 인물은 형체로 보이지 않고, 자기 시야에 들어오는 "
     "자기 몸만 보입니다.",
     "a POV shot seen from {who}'s own eyes, at the eye height of the posture they are "
     "actually in"),
]

# 시점의 주인. 레퍼런스 이미지 번호, 이 샷의 당사자, 또는 지켜보는 제3자.
#
# 라벨은 영어 문장 안에 그대로 박혀서 나갑니다 — "<레퍼런스에 없는 제3의 인물> lies
# face up" 처럼요. 그래서 라벨 단어 자체가 결과를 정합니다. 예전 "제3의 인물" 은
# 한국어로 '당사자가 아닌 사람' 이라, 행위 당사자로 쓰려던 자리에서 관음하는 구경꾼이
# 그려졌습니다. 이제 당사자용(MAN/WOMAN)과 관찰자용(THIRD)을 갈라 둡니다.
# 또 라벨에 "레퍼런스에 없는" 을 쓰지 않습니다 — 그건 레퍼런스에 대한 메타 정보라
# 영상 묘사에 들어갈 이유가 없고, subject_definitions 가 알아서 적어 줍니다.
VP_TARGET_THIRD = "third"
VP_TARGET_MAN = "man"
VP_TARGET_WOMAN = "woman"
VP_TARGET_NONE = ""

ANGLE = [
    ("", "지정 안 함", "카메라 높이를 지정하지 않습니다.", ""),
    ("eye", "눈높이", "렌즈가 인물의 눈 높이에 있습니다.", "at the subject's own eye height, level with them"),
    ("high", "하이앵글", "위에서 내려다봅니다.", "above the subject looking down at them"),
    ("low", "로우앵글", "아래에서 올려다봅니다.", "below the subject looking up at them"),
    ("overhead", "부감 / 탑샷", "바로 위에서 수직으로 내려다봅니다.", "directly above, looking straight down"),
    ("worm", "앙각 극단", "바닥 높이에서 가파르게 올려다봅니다.", "at ground level looking steeply upward"),
    ("dutch", "사각 기울기", "수평선이 기울어진 채 유지됩니다.", "with the horizon tilted off level and held tilted"),
]

# POV 에서 앵글은 "카메라를 어디에 두는가" 가 아니라 "시점 주인이 어디를 보는가" 입니다.
# 눈 높이는 자세가 정하고, 이 표가 시선의 각도를 정합니다. 둘을 나누지 않으면
# "눈높이에 있다" 와 "아래에서 올려다본다" 가 한 줄에서 싸웁니다.
ANGLE_POV = {
    "eye":      "looking straight ahead, level",
    "high":     "looking down at them",
    "low":      "looking up at them",
    "overhead": "looking straight down",
    "worm":     "looking steeply upward",
    "dutch":    "with the head tilted so the horizon sits off level",
}

# 수평 방향. ANGLE(수직)과 별개 축이라 'side view' 가 여기 들어갑니다.
# 방향은 "누구를 기준으로" 가 없으면 뜻이 없습니다. 예전에는 전부 "the subject" 로
# 하드코딩되어 있어서, 두 사람이 있는 샷에서 누구의 뒤인지가 프롬프트에 실리지 않았고
# 기승위를 후면으로 잡았더니 배면 기승위처럼 그려졌습니다. {who} 는 카드의 구도 기준
# 인물(없으면 행위 줄의 칸1, 그것도 없으면 "the subject")로 채워집니다.
FACING = [
    ("", "지정 안 함", "인물을 어느 방향에서 볼지 지정하지 않습니다.", ""),
    ("front", "정면", "인물 정면에서 봅니다.", "seen from directly in front of {who}"),
    ("three_q", "3/4 앞", "정면과 옆 사이 비스듬한 각도입니다.",
     "seen from a three-quarter front angle on {who}"),
    ("side", "측면 (사이드뷰)", "완전히 옆에서 봅니다. 옆얼굴이 보입니다.",
     "seen from directly to the side of {who}, in full profile"),
    ("three_q_back", "3/4 뒤", "뒤쪽 비스듬한 각도입니다.",
     "seen from a three-quarter rear angle on {who}"),
    ("back", "후면", "인물 뒤에서 봅니다.", "seen from directly behind {who}"),
]

SIZE = [
    ("", "지정 안 함", "샷 사이즈를 지정하지 않습니다.", ""),
    ("ecu", "익스트림 클로즈업", "눈·입·손 같은 한 디테일이 화면을 채웁니다.", "an extreme close-up"),
    ("cu", "클로즈업", "머리와 어깨 약간이 화면을 채웁니다.", "a close-up"),
    ("mcu", "미디엄 클로즈업", "가슴 위로 잡습니다.", "a medium close-up framed from the chest up"),
    ("ms", "미디엄", "허리 위로 잡습니다.", "a medium shot framed from the waist up"),
    ("mls", "미디엄 롱", "무릎 위로 전신에 가깝게 잡습니다.", "a medium long shot from the knees up"),
    ("ws", "와이드", "전신과 주변 공간이 함께 보입니다.", "a wide shot with clear space around the figure"),
    ("ews", "익스트림 와이드", "인물이 넓은 공간 속에 작게 보입니다.", "an extreme wide shot"),
]

# 관계형 샷. SIZE(크기)로는 표현이 안 되는 것들.
SHOT_TYPE = [
    ("", "지정 안 함", "관계형 샷 타입을 지정하지 않습니다.", ""),
    ("two", "투샷", "두 인물이 한 프레임에 함께 잡힙니다.", "a two-shot holding both figures in the same frame"),
    ("single", "싱글", "한 인물만 프레임에 있습니다.", "a single with only one figure in frame"),
    ("insert", "인서트", "소품이나 디테일만 따로 잡습니다.", "an insert of the object alone"),
    ("reaction", "리액션", "말하는 사람이 아니라 듣는 사람을 잡습니다.", "a reaction shot on the listener"),
    ("establishing", "설정샷", "공간 전체를 먼저 보여줍니다.", "an establishing shot showing the whole space"),
]

# guideline 의 20종 목록 그대로. 목록 밖 단어는 모델이 렌더하지 못합니다.
MOTION = [
    ("", "지정 안 함", "카메라 움직임을 지정하지 않습니다.", ""),
    ("static", "고정", "카메라가 전혀 움직이지 않습니다.", "The camera holds a Static Shot"),
    ("push_in", "푸시 인", "카메라 몸체가 앞으로 다가갑니다.", "The camera pushes in"),
    ("pull_out", "풀 아웃", "카메라 몸체가 뒤로 물러납니다.", "The camera pulls out"),
    ("zoom_in", "줌 인", "카메라는 그대로, 초점거리만 당깁니다.", "The camera zooms in"),
    ("zoom_out", "줌 아웃", "카메라는 그대로, 초점거리만 넓힙니다.", "The camera zooms out"),
    ("pan_l", "팬 왼쪽", "제자리에서 렌즈만 왼쪽으로 돌립니다.", "The camera pans left"),
    ("pan_r", "팬 오른쪽", "제자리에서 렌즈만 오른쪽으로 돌립니다.", "The camera pans right"),
    ("truck_l", "트럭 왼쪽", "카메라가 통째로 왼쪽으로 평행 이동합니다.", "The camera trucks left"),
    ("truck_r", "트럭 오른쪽", "카메라가 통째로 오른쪽으로 평행 이동합니다.", "The camera trucks right"),
    ("tilt_up", "틸트 업", "제자리에서 렌즈를 위로 젖힙니다.", "The camera tilts up"),
    ("tilt_down", "틸트 다운", "제자리에서 렌즈를 아래로 숙입니다.", "The camera tilts down"),
    ("ped_up", "페데스탈 업", "카메라 전체가 위로 올라갑니다.", "The camera pedestals up"),
    ("ped_down", "페데스탈 다운", "카메라 전체가 아래로 내려갑니다.", "The camera pedestals down"),
    ("arc", "아크 샷", "인물 주위를 호를 그리며 돕니다.", "The camera performs an Arc Shot around the subject"),
    ("tracking", "트래킹", "움직이는 인물을 따라갑니다.", "The camera holds a Tracking Shot following the subject"),
    ("shake_s", "약한 흔들림", "구도는 그대로, 미세하게 흔들립니다.", "The camera shakes slightly"),
    ("shake_h", "강한 흔들림", "크게 흔들립니다.", "The camera shakes strongly"),
    ("roll_cw", "롤 시계방향", "렌즈 축을 중심으로 시계방향 회전합니다.", "The camera rolls clockwise"),
    ("roll_ccw", "롤 반시계", "렌즈 축을 중심으로 반시계 회전합니다.", "The camera rolls counterclockwise"),
]

AMPLITUDE = [
    ("", "보통", "움직임 폭을 따로 말하지 않습니다.", ""),
    ("small", "작게", "구도가 조금만 바뀝니다.", "with small amplitude"),
    ("large", "크게", "구도가 크게 바뀝니다.", "with large amplitude"),
]

SPEED = [
    ("", "보통", "속도를 따로 말하지 않습니다.", ""),
    ("slow", "느리게", "천천히 움직입니다.", "at slow speed"),
    ("fast", "빠르게", "빠르게 움직입니다.", "at fast speed"),
]

TRANSITION = [
    ("cut", "하드컷", "즉시 전환됩니다. 기본값입니다.", "the shot cuts to"),
    ("dissolve", "디졸브", "앞 샷이 겹치며 사라집니다. 명시 요청일 때만 씁니다.",
     "the shot cross-dissolves to"),
    ("fade", "페이드", "검게 사라졌다 나타납니다.", "the shot fades to"),
    ("wipe", "와이프", "화면을 쓸어내며 바뀝니다.", "the shot wipes to"),
    ("match", "매치컷", "앞 샷과 형태·동작이 이어지며 바뀝니다.",
     "the shot cuts to a matching composition in"),
]


# 레퍼런스 이미지의 용도. first_frame / last_frame 은 그 이미지를 실제 프레임으로 못박는
# keyframe completion 이고, REF2VA 에서도 유효합니다 (H3 는 refs 와 keyframes 를 함께 받고,
# 풀레퍼런스 가이드도 keyframe completion 태스크 타입을 정의합니다).
REF_ROLE = [
    ("", "미사용", "이 이미지는 이 영상에서 쓰지 않습니다.", ""),
    # 이 줄들의 한글 설명은 UI 툴팁이면서 동시에 브리프에 들어가는 지시문입니다
    # (refs_block 이 그대로 씁니다). 화면 문구가 아니라 지시로 읽히게 써야 합니다.
    ("character", "캐릭터 / 인물",
     "인물의 얼굴·머리·눈·체형만 가져옵니다. 입고 있는 옷은 가져오지 않습니다.",
     "governs that character's face, hair, eyes and body proportions only; "
     "their clothing does not transfer"),
    ("character_full", "캐릭터 전체 (의상 포함)",
     "인물의 외형 전체를 가져옵니다 — 얼굴·머리·눈·체형에 더해 입고 있는 옷과 장신구를 "
     "색과 재질까지 그대로. 옷을 하나하나 묘사하라. 이 이미지에 맨몸이 드러나 있으면 "
     "가슴·유두·성기도 이 이미지를 기준으로 삼는다. 그 부위는 완곡어 대신 해부학 "
     "용어를 그대로 쓴다.",
     "governs that character's entire look: face, hair, eyes and body proportions plus "
     "every garment and accessory they are wearing, with its colour and material. "
     "Write each garment out explicitly. Wherever this picture shows the bare body, it "
     "is also the reference for the breasts, nipples and genitals it shows. Name those "
     "parts with their plain anatomical words — penis, vagina, nipples — and never "
     "soften them to pubic area, groin, crotch, private parts, intimate area or "
     "anything similar."),
    ("breasts", "가슴 / 유두",
     "가슴과 유두의 크기·모양·간격, 유륜과 유두의 색과 모양을 이 이미지에서 가져옵니다. "
     "그 외에는 아무것도 가져오지 않습니다.",
     "is the reference for that character's breasts and nipples: their size, shape and "
     "spacing, and the colour and shape of the areolae and nipples. Nothing else "
     "transfers from it."),
    ("genitals", "성기",
     "성기(음경 또는 질)의 모양·크기·색과 주변 체모를 이 이미지에서 가져옵니다. "
     "프롬프트에도 그 단어를 그대로 쓰고 완곡어로 바꾸지 않습니다. 그 외에는 "
     "아무것도 가져오지 않습니다.",
     "is the reference for that character's genitals — the penis or the vagina, whichever "
     "this picture shows: its shape, size and colour, and the body hair around it. Use "
     "that plain word in the prompt; never write pubic area, groin, crotch, private "
     "parts or any other euphemism. Nothing else transfers from it."),
    ("face", "얼굴 / 작화",
     "이 이미지가 얼굴의 최종 기준입니다. 눈매·눈동자·코·입·턱선과 그려진 방식(선 굵기, "
     "채색, 음영)까지 이 이미지를 따릅니다. 다른 이미지와 얼굴이 다르면 이 이미지가 이깁니다. "
     "몸·의상·배경은 가져오지 않습니다. 얼굴을 말로 자세히 풀어쓰라.",
     "is the AUTHORITY for that character's face and for how the face is drawn: eye shape, "
     "iris and highlight rendering, brows, how the nose and mouth are simplified, jaw and "
     "chin line, hair shape, plus line weight and shading style. Where another picture "
     "disagrees about the face, this one wins. Body, wardrobe and background do not "
     "transfer from it. Write the face out in words."),
    ("background", "배경 / 장소", "장소와 공간을 이 이미지에서 가져옵니다.",
     "governs the environment"),
    ("pose", "자세 / 포즈", "몸의 자세만 가져옵니다. 얼굴·의상·배경은 가져오지 않습니다.",
     "supplies the body pose only; face, hair, clothing and background do not transfer"),
    ("outfit", "의상", "옷과 그 상태를 이 이미지에서 가져옵니다.", "governs the wardrobe"),
    ("prop", "소품 / 사물", "물건을 이 이미지에서 가져옵니다.", "governs the prop"),
    ("style", "화풍 / 스타일", "그림체와 색감만 가져옵니다.", "governs the visual style"),
    ("expression", "표정", "표정만 가져옵니다.", "supplies the facial expression only"),

    # 카메라를 맡은 인물 전용. 다른 역할과 성격이 다릅니다 — 이 이미지는 "무엇을
    # 그릴지" 가 아니라 "화면에 거의 안 나오는 사람이 어떻게 생겼는지" 를 정합니다.
    # 이걸 '캐릭터' 나 '얼굴' 로 지정하면 역할은 얼굴을 보존하라 하고 시점은 얼굴이
    # 안 보인다고 해서, 모델이 둘 다 만족시키려고 인물을 둘로 쪼갭니다 — POV 대상이
    # 여자인데 카메라용 남자를 새로 만들어 낸 실제 사례가 있었습니다.
    ("pov_self", "◉ 카메라 인물 (1인칭)",
     "이 인물이 카메라입니다. 자기 시야에 들어오는 자기 몸의 피부색과 그 부위의 옷만 "
     "이 이미지에서 가져오고, 얼굴·머리·표정은 가져오지 마라 — 화면에 없습니다. "
     "이 인물을 형체로 그리지 말고, 카메라를 맡을 인물을 따로 만들지도 마라. "
     "시점을 '1인칭 POV' 로 두고 그 대상을 이 이미지로 지정해서 함께 쓰세요.",
     "is the person whose eyes the camera is. It governs the skin tone and the clothing "
     "on whatever parts of their own body fall within their own line of sight in the "
     "posture they are in. Do not take the face, hair or expression from it: none of "
     "that is on screen. Give this person a <Subject N> whose line says that, and never "
     "invent a second person to hold the camera"),
    ("ots_self", "◉ 어깨너머 인물",
     "이 인물은 화면 앞쪽에 어깨와 뒤통수만 걸칩니다. 머리 모양·머리색·어깨선·체격은 "
     "이 이미지에서 가져오되, 얼굴·눈·표정은 가져오지 마라 — 뒤통수만 보입니다. "
     "얼굴을 보여주려고 인물을 돌리지 마라. 시점을 '어깨너머' 로 두고 그 대상을 이 "
     "이미지로 지정해서 함께 쓰세요.",
     "is the person whose shoulder and the back of whose head sit in the near "
     "foreground. It governs the hair shape and colour, the shoulder line and the build. "
     "Do not take the face, eyes or expression from it — only the back of the head is "
     "visible — and never turn the figure round to show the face"),

    ("first_frame", "★ 첫 프레임", "이 이미지가 0.00초 첫 프레임이 됩니다. REF2VA 에서도 됩니다.",
     "is the first frame of [Shot 1] at 0.00 seconds"),
    ("last_frame", "★ 마지막 프레임", "이 이미지가 마지막 샷의 끝 프레임이 됩니다.",
     "is the final frame of the last shot"),
]

FRAME_ROLES = ("first_frame", "last_frame")


def _table(rows):
    return {k: (ko, tip, en) for k, ko, tip, en in rows}


TABLES = {
    "viewpoint": _table(VIEWPOINT), "angle": _table(ANGLE), "facing": _table(FACING),
    "size": _table(SIZE), "shot_type": _table(SHOT_TYPE), "motion": _table(MOTION),
    "amp": _table(AMPLITUDE), "speed": _table(SPEED), "transition": _table(TRANSITION),
    "ref_role": _table(REF_ROLE),
}


def en(field, key, who="the subject"):
    row = TABLES.get(field, {}).get(key or "")
    if not row or not row[2]:
        return ""
    return row[2].replace("{who}", who)


def ko(field, key):
    row = TABLES.get(field, {}).get(key or "")
    return row[0] if row else ""


PROGRESSION_RANDOM = "랜덤 — 행위 참가자 중에서"


def target_labels():
    """전개 대상 드롭다운. who_label() 과 같은 문구를 써서 표기가 갈라지지 않게 합니다."""
    out = [PROGRESSION_RANDOM, who_label(VP_TARGET_MAN), who_label(VP_TARGET_WOMAN)]
    out += [who_label("pic:{}".format(i)) for i in range(1, 10)]
    return out


def target_key(label):
    """드롭다운 라벨 -> vp_target 키. 랜덤이거나 못 찾으면 빈 문자열."""
    lab = (label or "").strip()
    if not lab or lab == PROGRESSION_RANDOM or lab.startswith("랜덤"):
        return ""
    for k in (VP_TARGET_MAN, VP_TARGET_WOMAN):
        if lab == who_label(k):
            return k
    for i in range(1, 10):
        k = "pic:{}".format(i)
        if lab == who_label(k):
            return k
    return ""


def facing_anchor(card, who):
    """FACING 의 기준 인물 — "누구의 뒤/앞/옆인가".

    카드에 `facing_target` 이 있으면 그것, 없으면 행위 줄의 첫 참가자를 씁니다.
    POV 인물은 화면에 그려지지 않으므로 그 사람의 앞뒤를 말하는 건 뜻이 없어서
    후보에서 뺍니다. 아무것도 못 찾으면 예전처럼 "the subject" 로 둡니다.
    """
    explicit = card.get("facing_target") or ""
    if explicit:
        return "<{}>".format(who_label(explicit))
    pov_t = (card.get("vp_target") or "") if card.get("viewpoint") == "pov" else ""
    seen = []
    for ln in (card.get("acts") or []):
        if not isinstance(ln, dict):
            continue
        for t in (ln.get("a"), ln.get("b")):
            if t and t != pov_t and t not in seen:
                seen.append(t)
    if seen:
        return "<{}>".format(who_label(seen[0]))
    if who and who != "한 인물":
        return "<{}>".format(who)
    return "the subject"


def who_label(target, names=None):
    """vp_target -> the Korean phrase naming whose viewpoint it is."""
    if not target:
        return "한 인물"
    if target == VP_TARGET_THIRD:
        return "이 장면을 지켜보는 제3자"
    if target == VP_TARGET_MAN:
        return "이 샷의 남자"
    if target == VP_TARGET_WOMAN:
        return "이 샷의 여자"
    if str(target).startswith("pic:"):
        return "이미지 {}의 인물".format(str(target)[4:])
    return str(target)


def who_label_en(target):
    """vp_target -> the English phrase naming the speaker, for the DIALOGUE block."""
    if not target:
        return "unspecified speaker"
    if target == VP_TARGET_THIRD:
        return "the onlooker watching this scene"
    if target == VP_TARGET_MAN:
        return "the man in this shot"
    if target == VP_TARGET_WOMAN:
        return "the woman in this shot"
    if str(target).startswith("pic:"):
        return "the person in reference image {}".format(str(target)[4:])
    return str(target)


def dialogue_lines(card):
    """[{who, text}] for this card, oldest form included.

    A single free-text `dialogue` field forced two speakers into one string, and the
    writer then had to guess how they relate — which is where "Simultaneously, <Subject
    2> says" came from. Lines carry their own speaker and their own order instead.
    """
    out = []
    for ln in (card.get("lines") or []):
        if not isinstance(ln, dict):
            continue
        txt = (ln.get("text") or "").strip()
        if txt:
            out.append({"who": (ln.get("who") or "").strip(), "text": txt,
                        "at": _seconds(ln.get("at"))})
    if not out:
        legacy = (card.get("dialogue") or "").strip()
        if legacy:
            out.append({"who": "", "text": legacy, "at": None})
    return out


def _seconds(v):
    """A dialogue line's start time in seconds, or None when it was left blank."""
    # `v in (None, "", False)` 로 쓰면 0 == False 라서 0초가 빈 값으로 사라집니다.
    if v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip()):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def clock(sec):
    """seconds -> MM:SS.mmm, the only timestamp format H3 accepts."""
    sec = max(0.0, float(sec))
    m, s = divmod(sec, 60.0)
    return "{:02d}:{:06.3f}".format(int(m), s)


def dialogue_block(card, language="Korean"):
    """The card's dialogue as an ordered, non-overlapping script.

    `language` is the language the video is spoken in, not the language the card was
    typed in — a line typed in Korean under a Japanese setting gets translated.
    """
    lines = dialogue_lines(card)
    if not lines:
        return ""
    rows, timed = [], False
    for i, ln in enumerate(lines, start=1):
        speaker = who_label(ln["who"]) if ln["who"] else "화자 미지정"
        when = ""
        if ln.get("at") is not None:
            when = " [{}초 시작]".format(_fmt_at(ln["at"]))
            timed = True
        rows.append("  {}){} {}: {}".format(i, when, speaker, ln["text"]))
    head = "대사 — 아래 순서대로, 한 번에 한 사람씩:"
    lang = language or "Korean"
    tail = ["모든 대사는 {} 로 말한다. 이미 {} 인 줄은 그대로 두고, 다른 언어로 적힌 줄은 "
            "자연스러운 {} 구어로 옮겨라. 원문을 그대로 남기거나 두 언어를 같이 넣지 "
            "마라.".format(lang, lang, lang)]
    if len(lines) > 1:
        tail.insert(0, "각 대사는 앞 대사가 완전히 끝난 뒤에 시작한다. "
                       "두 사람이 동시에 말하지 않는다.")
    if timed:
        # 시각을 박으면 컷 없이도 화자 사이에 경계가 생깁니다. 컷은 화면을 새로 그리게
        # 하지만 시각 표시는 같은 샷 안의 사건이라 프레이밍이 유지됩니다.
        tail.insert(0, "적힌 시각은 그 대사가 시작하는 시점이다. 이 샷 안에서 그대로 "
                       "지켜라. 이 시각들 때문에 컷을 넣지 마라 — 같은 샷이 끊기지 않고 "
                       "이어지는 채로 그 시각에 말이 시작될 뿐이다.")
    return "\n".join([head] + rows + tail)


def _fmt_at(sec):
    """2.0 -> '2', 2.5 -> '2.5' — 한글 브리프에 읽기 좋은 형태로."""
    f = float(sec)
    return str(int(f)) if f == int(f) else ("%g" % f)


# 컷 뒤의 샷이 앞 샷과 어떤 관계인가. 예전에는 한 가지뿐이었습니다 — "같은 장소,
# 같은 인물, 같은 의상, 같은 조명. 동작은 끊기지 않고 이어진다." 그래서 두 경우가
# 다 틀린 말을 받았습니다:
#
#   * 카메라만 바꾸고 싶은데 자세를 잠가 주지 않아, 행위 줄을 손으로 다시 고르지
#     않으면 자세 문장이 통째로 빠졌습니다. 배경도 모델 자유였고요.
#   * 회상이나 장소 이동인데 "같은 장소" 라고 우겼습니다.
#
# 그리고 배경이 컷마다 바뀌는 진짜 이유가 여기 있었습니다. 시스템 프롬프트의
# CONTINUITY 블록은 "브리프가 준 것을 옮겨라" 라고만 하고, "샷 1에서 네가 지어낸
# 것도 지켜라" 라는 말이 어디에도 없습니다. 브리프가 장소를 안 주면 모델은 샷 1에서
# 자유롭게 창문을 만들고, 샷 2에서 또 자유롭게 만듭니다 — 각 샷에서는 규칙을 어긴
# 적이 없습니다. 그 구속을 여기, 샷 내용 바로 옆에 답니다. 46,000자 시스템 프롬프트
# 안의 같은 규칙은 이미 여러 번 졌습니다.
SHOT_LINK = [
    ("same_moment", "같은 순간 — 카메라만 바뀜",
     "장소·인물·의상·조명에 더해 자세와 동작까지 그대로입니다. 행위와 내용을 앞 "
     "샷에서 그대로 물려받습니다. 정면에서 후면으로 돌 때처럼 카메라만 바꾸는 컷."),
    ("", "이어지는 동작 (기본)",
     "장소·인물·의상·조명은 같고, 동작은 앞 샷에서 이어서 진행됩니다."),
    ("new_scene", "새 장면 — 장소/시간이 바뀜",
     "앞 샷의 장소와 조명을 이어받지 않습니다. 인물의 외형과 의상은 유지됩니다. "
     "회상이나 장소 이동에 씁니다."),
]

SHOT_LINK_LABELS = [row[1] for row in SHOT_LINK]
_LINK_BY_LABEL = {row[1]: row[0] for row in SHOT_LINK}


def link_key(label):
    """드롭다운 라벨 -> 키. 못 알아보면 기본값(이어지는 동작)."""
    return _LINK_BY_LABEL.get(label, "")


def is_same_moment(card):
    """이 카드가 앞 샷에서 행위·내용을 물려받는가."""
    return (card or {}).get("link") == "same_moment"


def continuity_line(card, n):
    """샷 n 이 앞 샷과 어떻게 이어지는지. n 은 1부터."""
    prev = n - 1
    link = (card or {}).get("link") or ""
    if link == "same_moment":
        return ("유지: 이 샷은 샷 {}과 같은 순간이 이어지는 것이다. 장소·인물·의상·"
                "조명은 물론 자세와 누가 무엇을 하고 있는지까지 전부 샷 {}과 같다. "
                "샷 {}에 쓴 장소 묘사를 같은 단어로 그대로 다시 써라 — 브리프에 없던 "
                "것을 샷 {}에서 네가 정했다면 그것도 이 영상의 사실이고, 네가 지어낸 "
                "것이라고 해서 바꿔도 되는 것이 아니다. 이 샷에서 바뀌는 것은 카메라 "
                "하나뿐이다.".format(prev, prev, prev, prev))
    if link == "new_scene":
        return ("전환: 이 샷은 샷 {}과 다른 장소이거나 다른 시간이다. 앞 샷의 장소와 "
                "조명을 이어받지 마라. 다만 인물의 외형과 의상은 그대로 유지하고, 이 "
                "샷에서도 다시 적어라.".format(prev))
    return ("유지: 샷 {}과 같은 장소, 같은 인물, 같은 의상, 같은 조명이다. "
            "장소와 인물 외형을 이 샷에서도 다시 적어라. "
            "동작은 끊기지 않고 이어진다.".format(prev))


def camera_sentence(card, who, frame_anchored=False):
    """This card's camera as explicit instructions.

    The English directive is what goes out, not the Korean dropdown label: a bare noun
    list ("와이드, 눈높이, 정면") reads as loose keywords and the writer silently drops
    the ones it considers obvious, which is how a chosen facing never reaches the prompt.
    The Korean label rides along in brackets so the line stays readable next to the rest
    of the brief.
    """
    bits = []
    # POV 는 카메라 높이를 "그 인물의 눈" 으로 못박습니다. 그 위에 앵글을 또 얹으면
    # "눈높이" 와 "아래에서 올려다봄" 이 한 줄에서 싸우고, 실제로 카메라가 붕 떴습니다.
    pov = card.get("viewpoint") == "pov"
    # 첫 프레임이 지정된 샷에서는 구도를 이미지가 정합니다. 여기서 샷 사이즈나 앵글을
    # 또 말하면 "이렇게 잡아라" 라는 지시가 되어 0.00초의 프레임을 다시 짜버립니다.
    # 카메라 움직임(모션)은 0초 이후의 일이라 그대로 둡니다.
    framing = () if frame_anchored else ("size", "shot_type", "angle", "facing")
    # POV 자체가 오프닝 구도 명사구입니다. 여기에 사이즈를 또 얹으면 한 줄에서
    # "a POV shot seen from his own eyes; a medium shot framed from the waist up" 이
    # 되어 구도가 둘이 되고, 뒤에 온 쪽이 앞의 것을 덮습니다 — 예전에는 POV 문장이
    # 직접 "'a medium shot' 으로 시작하지 마라" 라고 쓰면서 그 바로 다음 항목이
    # 그 문구를 내보내는 상태였습니다.
    if pov:
        framing = tuple(f for f in framing if f not in ("size", "shot_type"))

    # POV 는 카메라 줄에서도 맨 앞이어야 합니다. 사이즈 절이 먼저 나가면 모델은
    # "a medium shot" 을 손에 쥔 채로 POV 문장을 읽게 되고, 정작 그 문장이 "a medium
    # shot 으로 시작하지 마라" 라고 말합니다 — 지시가 스스로를 반박합니다.
    if pov:
        key = card.get("viewpoint")
        sent, lab = en("viewpoint", key, who), ko("viewpoint", key)
        if sent:
            bits.append("{} [{}]".format(sent, lab))

    for f in framing:
        key = card.get(f)
        if f == "angle" and pov:
            sent = ANGLE_POV.get(key or "", "")
        elif f == "facing":
            # 방향의 기준은 시점의 주인이 아니라 화면에 그려지는 인물입니다.
            sent = en(f, key, facing_anchor(card, who))
        else:
            sent = en(f, key, who)
        lab = ko(f, key)
        if sent:
            bits.append("{} [{}]".format(sent, lab))

    if not pov:                       # POV 는 위에서 이미 맨 앞에 넣었습니다
        key = card.get("viewpoint")
        sent, lab = en("viewpoint", key, who), ko("viewpoint", key)
        if sent:
            bits.append("{} [{}]".format(sent, lab))

    key = card.get("motion")
    sent, lab = en("motion", key, who), ko("motion", key)
    if sent:
        for f in ("amp", "speed"):
            extra = en(f, card.get(f))
            if extra:
                sent += " " + extra
                lab += " " + ko(f, card.get(f))
        bits.append("{} [{}]".format(sent, lab))

    if not bits:
        return ""
    return ("; ".join(bits)
            + ". 위 카메라 지시는 전부 프롬프트에 그대로 반영하라. 하나도 빠뜨리지 마라.")


# 역할이 무엇을 가져오는지는 툴팁에 있지만, 그건 설명이라 지시로 읽히지 않습니다.
# "몸·의상·배경은 가져오지 않습니다" 라고 써 있어도, 시스템 프롬프트의 체형 체크리스트
# (FOR A BODY, "SLENDER" IS NOT A DESCRIPTION) 가 무조건 몸을 쓰라고 하니 그쪽이
# 이깁니다 — 얼굴 전용 레퍼런스에 허리·엉덩이·가슴 묘사가 딸려 나왔습니다.
# 그래서 "가져오지 마라" 를 능동적인 금지로 한 줄 더 붙입니다.
ROLE_EXCLUDE = {
    "character":  "이 이미지에서 의상은 가져오지 마라.",
    "face":       "이 이미지에서 몸·체형·의상·배경은 가져오지 마라. 체형 체크리스트는 "
                  "이 이미지에 적용되지 않는다. 몸을 써야 하면 '내용' 에 적힌 것만 쓰고, "
                  "이 이미지에서 온 것처럼 적지 마라.",
    "breasts":    "이 이미지에서 가슴과 유두 외에는 아무것도 가져오지 마라.",
    "genitals":   "이 이미지에서 성기와 그 주변 외에는 아무것도 가져오지 마라.",
    "background": "이 이미지에서 인물·의상은 가져오지 마라. 장소와 공간만이다.",
    "pose":       "이 이미지에서 얼굴·의상·배경·체형은 가져오지 마라. 자세만이다.",
    "outfit":     "이 이미지에서 얼굴·체형·배경은 가져오지 마라. 옷과 그 상태만이다.",
    "prop":       "이 이미지에서 인물·배경은 가져오지 마라. 그 물건만이다.",
    "style":      "이 이미지에서 인물·의상·배경의 내용은 가져오지 마라. 그림체와 색감만이다.",
    "expression": "이 이미지에서 얼굴 생김새·체형·의상은 가져오지 마라. 표정만이다.",
}

def refs_block(refs, cards=None):
    """레퍼런스 이미지 용도표. 첫/마지막 프레임이면 keyframe completion 을 요구합니다."""
    if not refs:
        return "", {}
    lines, axes = [], {}
    for r in refs:
        role = (r.get("role") or "").strip()
        n = r.get("n")
        if not role or n in (None, ""):
            continue
        ko_lab, tip, _en = TABLES["ref_role"].get(role, ("", "", ""))
        if not ko_lab:
            continue
        line = "- 이미지 {}: {} — {}".format(n, ko_lab, tip)
        extra = ROLE_EXCLUDE.get(role)
        if extra:
            line += " " + extra
        lines.append(line)
        if role in FRAME_ROLES:
            axes["frame_anchor"] = "yes"
    if not lines:
        return "", {}
    out = ["레퍼런스 이미지 용도(각 이미지가 무엇을 지배하는지 반드시 명시할 것):"] + lines
    if axes.get("frame_anchor"):
        out.append("위에서 ★ 로 표시된 이미지는 실제 프레임이다. subject_definitions 에 "
                   "<Picture N> 항목을 따로 세우고, summary 의 태스크 타입에 "
                   "keyframe completion 을 포함하라.")
    return "\n".join(out), axes


def build(cards, subjects_text="", refs=None, language="Korean",
          progression=0, progression_seed=0, duration=0.0,
          progression_target=""):
    """cards -> (brief_body, axis_tokens, problems)

    The continuity sentence between cards is what stops the second shot from landing in
    a different room with differently dressed people.
    """
    out, problems = [], []
    axes = {}
    seen_vp = []

    # '같은 순간' 샷은 행위와 내용을 앞 샷에서 물려받습니다. 여기서 한 번 채워 두면
    # 아래의 모든 블록(행위·내용·전개·리포트)이 같은 값을 봅니다 — 카드마다 따로
    # 챙기면 한 군데를 빠뜨리게 되고, 실제로 행위 줄을 다시 고르지 않아 자세 문장이
    # 통째로 빠지는 일이 있었습니다. 원본 리스트는 건드리지 않습니다.
    cards = [dict(c) if isinstance(c, dict) else {} for c in (cards or [])]
    for i in range(1, len(cards)):
        if is_same_moment(cards[i]):
            cards[i]["acts"] = cards[i - 1].get("acts") or []
            cards[i]["text"] = cards[i - 1].get("text") or ""
            # 추가 동작과 대사는 물려받지 않습니다. 같은 순간이라도 이 샷에서만
            # 보여주고 싶은 것이 있을 수 있고, 대사를 복제하면 같은 말이 두 번 나갑니다.
    if cards and is_same_moment(cards[0]):
        cards[0] = dict(cards[0])
        cards[0]["link"] = ""          # 첫 샷은 이어받을 앞 샷이 없습니다
        problems.append("샷 1: '같은 순간' 은 앞 샷이 있어야 합니다 — 기본값으로 "
                        "처리했습니다.")

    rb, raxes = refs_block(refs, cards)
    anchored = bool(raxes.get("frame_anchor"))
    if rb:
        out.append(rb)
        out.append("")
        axes.update(raxes)

    for i, c in enumerate(cards):
        n = i + 1
        who = who_label(c.get("vp_target"))
        head = "[샷 {}]".format(n)
        if n > 1:
            at = c.get("at")
            tr = ko("transition", c.get("transition") or "cut")
            if at in (None, ""):
                problems.append("샷 {}: 전환 시각이 비어 있습니다.".format(n))
                head += " {}".format(tr)
            else:
                head += " {}초에 {}".format(at, tr)
        out.append(head)

        # 순서가 곧 우선순위입니다. 이 모델은 가장 나중에·가장 구체적으로 적힌 지시를
        # 따릅니다. 그래서 약한 것부터 강한 것 순으로 쌓습니다:
        #   내용(장면) -> 행위(몸) -> 대사 -> 카메라(그림)
        # 예전에는 카메라가 맨 앞이고 "내용이 카메라·행위를 이긴다" 는 문장이 붙어
        # 있었는데, 정작 행위 블록이 내용보다 뒤에 있어서 규칙과 배치가 서로 반대로
        # 밀었습니다. 이제 어느 쪽이 무엇을 결정하는지 영역으로 나눠 적습니다.
        # 뒤에 실제로 무엇이 나가는지 먼저 알아야 우선권 문장을 옳게 쓸 수 있습니다.
        # 행위 줄을 비운 샷에서 "자세는 아래 '행위' 가 정한다" 가 그대로 나가면, 가리킬
        # 블록이 없는 지시가 됩니다. 모델은 자세를 자기 관할이 아니라고 읽고 사용자가
        # 내용 칸에 쓴 자세를 버릴 수 있습니다 — 행위로 표현 못 하는 자세를 자연어로
        # 쓰는 경우가 바로 그 경우라, 가장 필요한 곳에서 가장 크게 깨집니다.
        pov_t = c.get('vp_target') if c.get('viewpoint') == 'pov' else None
        av = acts.act_block(c, who_label, pov_t)
        if acts.pov_slots_unknown(c, pov_t):
            problems.append(
                "샷 {}: 시점 대상({})은 정했는데 행위 참가자 칸이 비어 있습니다 — "
                "이 인물이 행위에 참여하는지 판단할 수 없어, 참여 여부를 말하지 않는 "
                "카메라 문장만 나갑니다. 참가자 칸을 채우면 자세에 맞는 문장이 "
                "붙습니다.".format(n, who_label(pov_t)))
        cam = camera_sentence(c, who, frame_anchored=(anchored and n == 1))

        body = (c.get("text") or "").strip()
        if body:
            # "빠뜨리지 마라" 는 그대로 둡니다. 350~500 단어로 줄일 때 강제가 없는 줄이
            # 가장 먼저 잘려나가서, 사용자가 쓴 손 위치가 통째로 사라진 적이 있습니다.
            # 다만 '완전성' 과 '우선권' 은 다른 문제라, 우선권은 영역별로 쪼갭니다.
            rule = ["위 내용은 사용자가 직접 쓴 것이다. 한 문장도 빠뜨리지 말고 전부 "
                    "프롬프트에 반영하라."]
            if av and cam:
                rule.append("장소·의상·표정·분위기는 이 내용이 정하고, 아래의 지시보다 "
                            "우선한다. 다만 몸의 자세와 방향, 누가 움직이는지는 아래 "
                            "'행위' 가 정하고, 무엇이 화면에 그려지는지는 아래 '카메라' 가 "
                            "정한다. 그 둘과 어긋나는 부분은 버리고, 두 쪽을 섞지 마라.")
            elif av:
                rule.append("장소·의상·표정·분위기는 이 내용이 정하고, 아래의 지시보다 "
                            "우선한다. 다만 몸의 자세와 방향, 누가 움직이는지는 아래 "
                            "'행위' 가 정한다. 그와 어긋나는 부분은 버리고, 두 쪽을 섞지 "
                            "마라.")
            elif cam:
                rule.append("장소·의상·표정·분위기에 더해 몸의 자세와 방향, 누가 "
                            "움직이는지도 이 내용이 정한다. 아래 '카메라' 는 무엇이 화면에 "
                            "그려지는지만 정하니, 그와 어긋나는 부분만 버려라.")
            else:
                rule.append("이 샷의 자세·움직임·구도는 전부 이 내용이 정한다. "
                            "여기 적히지 않은 것만 네가 채워라.")
            out.append("내용: " + body)
            out.append(" ".join(rule))
        else:
            problems.append("샷 {}: 내용이 비어 있습니다.".format(n))

        if av:
            out.append(av)

        # 추가 동작은 행위를 이기는 게 아니라 그 위에 얹힙니다. 그래서 행위 바로 뒤에
        # 두고, 무엇을 쓸 수 있고 부딪히면 무엇을 버릴지를 그 자리에서 못박습니다.
        # "자유롭게 해라" 는 옆의 구체적인 행위 문장에 항상 집니다 — 쓸 수 있는 부위를
        # 이름으로 부르는 편이 실제로 먹힙니다.
        extra = (c.get("extra") or "").strip()
        if extra:
            out.append("추가 동작: " + extra)
            if av:
                out.append("위의 행위는 그대로 계속된다. 이 추가 동작은 그 위에 겹친다. "
                           "위 행위가 이미 쓰고 있는 신체 부위는 쓰지 말고, 남는 부위로만 "
                           "하라. 위 행위의 자세·방향·누가 움직이는지를 바꾸는 내용이면 "
                           "그 부분은 버려라.")
            else:
                out.append("이 샷에는 지정된 행위가 없다. 위 동작을 그대로 쓰되, "
                           "적히지 않은 부분만 네가 채워라.")

        # 전개는 추가 동작보다 약합니다 — 사용자가 직접 쓴 것이 굴린 주사위에 밀리면
        # 안 되니, 앞의 두 블록이 자리를 잡은 뒤에 옵니다. 샷마다 길이를 따로 알 수는
        # 없어서 전체 길이를 샷 수로 나눠 씁니다.
        if progression:
            pb = acts.progression_block(
                c, who_label, progression_seed, progression,
                (float(duration or 0) / max(1, len(cards))) or 6.0,
                pov_target=(c.get("vp_target") if c.get("viewpoint") == "pov" else None),
                target=progression_target)
            if pb:
                out.append(pb)

        d = dialogue_block(c, language)
        if d:
            out.append(d)

        if cam:
            out.append("카메라: " + cam)
            out.append("카메라는 무엇이 화면에 그려지는지만 정한다. 위에 적힌 자세와 "
                       "움직임은 그대로 두고, 그것을 이 시점에서 본 모습으로 그려라.")
        if anchored and n == 1:
            out.append("구도: 0.00초의 화면은 지정된 첫 프레임 이미지 그대로다. 샷 "
                       "사이즈·앵글·방향을 글로 다시 지시하지 마라. 프레임 안에 무엇이 "
                       "있는지만 적고, 어떻게 잡혔는지는 적지 마라.")

        if n > 1:
            out.append(continuity_line(c, n))

        vp = c.get("viewpoint") or ""
        if vp:
            seen_vp.append(vp)
        out.append("")

    if len(cards) > 1:
        axes["multi_shot"] = "yes"
    # a viewpoint that is not the same in every card is a viewpoint CHANGE
    if len({v for v in seen_vp if v}) > 1:
        axes["viewpoint_change"] = "pov" if "pov" in seen_vp else "subjective"
    if any((c.get("vp_target") or "").startswith("pic:") for c in cards):
        axes["ref_framing"] = "content_only"

    return "\n".join(out).strip(), axes, problems
