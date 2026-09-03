# -*- coding: utf-8 -*-
"""
Picture roles — tell the model what each reference image is FOR.

Two failures come from leaving this unsaid:

  * With only character references and no declared style source, H3 falls back to
    its own house look and ignores the art style of the references.
  * Add a pose or costume reference and H3 tends to treat it as a FRAME of the
    video — because nothing ever told it the pictures are not frames.

A role declaration fixes both. Each role emits a contract: how the picture becomes
a Subject, which retention marker applies, what transfers, and — the important half —
what must NOT transfer.

Declared in the node as one line per picture:

    1: character
    2: character
    3: pose        # 앉은 자세만
    4: background
    5: style
"""

import re

# key -> spec
ROLES = {
    "character": {
        "label": "캐릭터 / 인물 정체성",
        "subject": "own",
        "marker": "fully_preserved",
        "takes": "the character's complete identity — face, hairstyle and colour, eye "
                 "colour, skin tone, body proportions, and every garment and accessory",
        "blocks": "",
        "note": "Write the identity out exhaustively; this is the anchor everything else "
                "hangs on.",
    },
    "background": {
        "label": "배경 / 장소 / 환경",
        "subject": "own",
        "marker": "fully_preserved",
        "takes": "the location — architecture, furniture, materials, palette and the "
                 "quality and direction of its light",
        "blocks": "any person visible in it",
        "note": "",
    },
    "costume": {
        "label": "의상 / 복장만",
        "subject": "attribute",
        "marker": "attribute_transfer",
        "takes": "the garments, their cut, fabric, colours and how they sit on the body",
        "blocks": "the face, hairstyle, hair colour, body proportions and background of "
                  "that picture",
        "note": "",
    },
    "pose": {
        "label": "자세 / 포즈만",
        "subject": "attribute",
        "marker": "attribute_transfer",
        "takes": "the body axis, limb positions, weight distribution, support and contact "
                 "points, and head angle",
        "blocks": "the face, hairstyle, hair colour, clothing, body proportions and "
                  "background of that picture",
        "note": "Write the pose out in words as well as citing the picture. It is a "
                "posture, not a person, and never appears as a separate figure.",
    },
    "expression": {
        "label": "표정만",
        "subject": "attribute",
        "marker": "attribute_transfer",
        "takes": "the facial expression — brow, eye shape, mouth and the tension in the face",
        "blocks": "identity, hairstyle, clothing, body pose and background",
        "note": "",
    },
    "motion": {
        "label": "동작 / 움직임",
        "subject": "attribute",
        "marker": "attribute_transfer",
        "takes": "the movement itself — its path, rhythm, amplitude and which body part "
                 "drives it",
        "blocks": "appearance, clothing and setting",
        "note": "",
    },
    "style": {
        "label": "화풍 / 스타일",
        "subject": "attribute",
        "marker": "attribute_transfer",
        "takes": "the drawing style — line quality, shading method, colour treatment, "
                 "level of detail and overall rendering",
        "blocks": "the specific characters, objects, composition and setting shown in it",
        "note": "The style line that opens [Shot 1] must be derived from this picture. "
                "Name what the style actually looks like; do not fall back on a generic "
                "style label.",
    },
    "prop": {
        "label": "소품 / 사물",
        "subject": "own",
        "marker": "fully_preserved",
        "takes": "the object's shape, materials, colour and scale",
        "blocks": "the person holding it and the background it sits in",
        "note": "",
    },
    "composition": {
        "label": "구도 / 프레이밍만",
        "subject": "attribute",
        "marker": "attribute_transfer",
        "takes": "the framing — camera height and angle, subject size in frame, and where "
                 "things sit in the composition",
        "blocks": "the characters, their clothing, the location and the art style",
        "note": "",
    },
    "frame": {
        "label": "실제 프레임 (이것만 프레임 앵커)",
        "subject": "frame",
        "marker": "fully_preserved",
        "takes": "everything — this picture IS a literal frame of the target video",
        "blocks": "",
        "note": "This is the only role that makes a picture a frame. Add "
                "'keyframe completion' to the summary task types when it is present.",
    },
}

# Korean and loose aliases so the field is forgiving.
_ALIASES = {
    "캐릭터": "character", "인물": "character", "char": "character", "identity": "character",
    "배경": "background", "환경": "background", "장소": "background", "bg": "background",
    "environment": "background", "scene": "background", "location": "background",
    "의상": "costume", "복장": "costume", "옷": "costume", "outfit": "costume",
    "wardrobe": "costume", "clothes": "costume", "clothing": "costume",
    "자세": "pose", "포즈": "pose", "posture": "pose",
    "표정": "expression", "face": "expression",
    "동작": "motion", "움직임": "motion", "action": "motion", "movement": "motion",
    "화풍": "style", "그림체": "style", "스타일": "style", "art": "style",
    "소품": "prop", "사물": "prop", "object": "prop", "item": "prop",
    "구도": "composition", "프레이밍": "composition", "framing": "composition",
    "comp": "composition", "layout": "composition",
    "프레임": "frame", "키프레임": "frame", "keyframe": "frame", "anchor": "frame",
}

_LINE = re.compile(r"^\s*(?:<?\s*picture\s*)?(\d{1,2})\s*[:=\-.)]?\s*([^#\n]+?)\s*(?:#\s*(.*))?$",
                   re.IGNORECASE)


def role_names():
    return list(ROLES.keys())


def normalize(word):
    w = (word or "").strip().lower().replace("_", " ").replace("-", " ")
    w = re.sub(r"\s+", " ", w)
    if w in ROLES:
        return w
    if w in _ALIASES:
        return _ALIASES[w]
    for k in ROLES:                     # "character reference", "pose only"
        if w.startswith(k):
            return k
    for a, k in _ALIASES.items():
        if w.startswith(a):
            return k
    return ""


def parse(text, n_images=0):
    """
    'text' -> (roles, problems)

    roles: [{"n": 3, "role": "pose", "note": "앉은 자세만"}], sorted by picture number.
    """
    roles, problems, seen = [], [], set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m = _LINE.match(line)
        if not m:
            problems.append("could not read '{}' — use 'N: role'".format(line[:40]))
            continue
        n = int(m.group(1))
        key = normalize(m.group(2))
        note = (m.group(3) or "").strip()
        if not key:
            problems.append("unknown role '{}' on picture {}".format(m.group(2).strip(), n))
            continue
        if n in seen:
            problems.append("picture {} declared twice".format(n))
            continue
        if n_images and n > n_images:
            problems.append("picture {} declared but only {} image(s) are sent".format(
                n, n_images))
            continue
        seen.add(n)
        roles.append({"n": n, "role": key, "note": note})
    roles.sort(key=lambda r: r["n"])
    return roles, problems


def build_block(roles, n_images, mode):
    """The PICTURE ROLES section injected into the system prompt."""
    if not n_images:
        return ""

    lines = ["################  PICTURE ROLES  ################"]
    has_frame_role = any(r["role"] == "frame" for r in roles)
    mode_defines_frames = mode in ("I2VA", "FL2VA", "L2VA")

    if roles:
        lines.append("Each supplied picture has an assigned job. Honour it exactly.")
        lines.append("")
        for r in roles:
            spec = ROLES[r["role"]]
            lines.append("<Picture {}> — {} reference".format(r["n"], r["role"].upper()))
            lines.append("    transfers: " + spec["takes"])
            if spec["blocks"]:
                lines.append("    must NOT transfer: " + spec["blocks"])
            if spec["subject"] == "own":
                lines.append("    declare it as its own <Subject N>, marker: "
                             + spec["marker"])
            elif spec["subject"] == "attribute":
                lines.append("    declare it as an attribute-only Subject, marker: "
                             + spec["marker"] + " — say in that same line which property "
                             "transfers and which explicitly do not")
            else:
                lines.append("    this picture is a literal frame of the video")
            if spec["note"]:
                lines.append("    " + spec["note"])
            if r["note"]:
                lines.append("    operator note: " + r["note"])
            lines.append("")
        undeclared = [i for i in range(1, n_images + 1)
                      if i not in {r["n"] for r in roles}]
        if undeclared:
            lines.append("No role was given for <Picture {}>. Decide from the brief what "
                         "each contributes and state it explicitly.".format(
                             ">, <Picture ".join(str(i) for i in undeclared)))
            lines.append("")
    else:
        lines.append("No roles were declared. Decide from the brief what each picture "
                     "contributes — identity, environment, costume, pose, style — and say "
                     "so explicitly for every one of them.")
        lines.append("")

    # The single most important line, and the one that was missing entirely.
    if not has_frame_role and not mode_defines_frames:
        lines.append("NONE OF THESE PICTURES IS A FRAME OF THE TARGET VIDEO.")
        lines.append("Do not reproduce any picture as the opening frame, the closing frame "
                     "or any frame in between. Do not copy a picture's composition, camera "
                     "angle or background layout unless a picture is explicitly marked as a "
                     "composition or background reference. They supply attributes to a newly "
                     "staged scene. The summary task type is 'reference generation' — never "
                     "'keyframe completion'.")
    elif has_frame_role:
        anchors = [r["n"] for r in roles if r["role"] == "frame"]
        lines.append("<Picture {}> is a frame anchor; every other picture is a reference "
                     "only and must not be reproduced as a frame. Add 'keyframe completion' "
                     "to the summary task types.".format(
                         ">, <Picture ".join(str(a) for a in anchors)))

    style_ref = [r["n"] for r in roles if r["role"] == "style"]
    if style_ref:
        lines.append("")
        lines.append("The art style of the video comes from <Picture {}>. Open [Shot 1] by "
                     "describing that style in concrete terms — line quality, shading, "
                     "colour treatment, level of detail — instead of a generic label."
                     .format(style_ref[0]))
    lines.append("#################################################")
    return "\n".join(lines)


def summary_line(roles, problems):
    if not roles and not problems:
        return ""
    parts = []
    if roles:
        parts.append("picture roles: " + ", ".join(
            "{}={}".format(r["n"], r["role"]) for r in roles))
    for p in problems:
        parts.append("[warn] roles: " + p)
    return "\n".join(parts)


# ------------------------------------------------------------- per-mode picture roles

_MODE_SLOTS = {
    "T2VA": [],
    "I2VA": ["the literal 0.00s frame"],
    "L2VA": ["the literal final frame"],
    "FL2VA": ["the literal 0.00s frame", "the literal final frame"],
}


def slot_report(mode, names):
    """One line spelling out what each supplied picture actually IS in this mode."""
    if not names:
        return "{}: no pictures sent".format(mode)
    labels = _MODE_SLOTS.get(mode)
    if labels is None:                                   # REF2VA
        return "{}: <Picture 1..{}> = {} — appearance references, NOT frames".format(
            mode, len(names), ", ".join(names))
    parts = []
    for i, nm in enumerate(names):
        what = labels[i] if i < len(labels) else "unused"
        parts.append("<Picture {}> = {} ({})".format(i + 1, nm, what))
    return "{}: {}".format(mode, "; ".join(parts))
