# -*- coding: utf-8 -*-
"""
Shot-list axes — the columns a real shot list actually has.

This replaces the old "genre" dropdown. A genre is a bundle of taste; a shot list
is a set of independent decisions, and they are what a camera department actually
fills in before a setup: size, angle, mount, lens, depth of field, lighting key,
and whose point of view it is.

Every axis defaults to "auto" and emits nothing at all in that case, so a workflow
that touches none of them behaves exactly as before. Only the choices actually made
reach the model.
"""

# Each entry: key -> (dropdown label, the sentence handed to the model)
# The first entry of every axis is always "auto" and emits nothing.

SHOT_SIZE = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("ecu", "ECU · 익스트림 클로즈업",
     "Extreme close-up: a single detail fills the frame — eyes, a mouth, hands, a "
     "small object. The surrounding space is not visible."),
    ("cu", "CU · 클로즈업",
     "Close-up: the head and a little of the shoulders fill the frame. Facial detail "
     "is the subject; the location reads only as background tone."),
    ("mcu", "MCU · 미디엄 클로즈업",
     "Medium close-up: framed from roughly the chest up. Expression still reads "
     "clearly while some of the setting is visible behind."),
    ("ms", "MS · 미디엄 샷",
     "Medium shot: framed from roughly the waist up. Gesture and posture read as "
     "well as expression."),
    ("mls", "MLS · 미디엄 롱 샷",
     "Medium long shot: the whole figure from about the knees up, with the "
     "immediate surroundings visible."),
    ("ws", "WS · 와이드",
     "Wide shot: the full figure with clear space around it; the location is as "
     "much the subject as the person."),
    ("ews", "EWS · 익스트림 와이드",
     "Extreme wide shot: the figure is small within a large environment; the space "
     "dominates the frame."),
]

CAMERA_ANGLE = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("eye", "eye level · 눈높이",
     "Eye level: the lens sits at the subject's own eye height, level with them."),
    ("high", "high angle · 하이앵글",
     "High angle: the camera is above the subject looking down at them."),
    ("low", "low angle · 로우앵글",
     "Low angle: the camera is below the subject looking up at them."),
    ("overhead", "overhead · 부감 / 탑샷",
     "Overhead: the camera is directly above, looking straight down."),
    ("worm", "worm's eye · 앙각 극단",
     "Worm's eye: the camera is at or near the ground looking steeply upward."),
    ("dutch", "dutch · 사각 기울기",
     "Dutch angle: the horizon is tilted off level and stays tilted."),
]

CAMERA_MOUNT = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("tripod", "tripod · 삼각대 고정",
     "Tripod: the camera is locked off. No drift, no shake, no reframing at any "
     "point. Write it as a static shot."),
    ("handheld", "handheld · 핸드헬드",
     "Handheld: the operator holds the camera. Use the listed motion type \"shakes "
     "slightly\" with small amplitude at slow speed; the composition itself does not "
     "change."),
    ("dolly", "dolly / track · 달리·트랙",
     "Dolly or track: the camera body travels smoothly on a level path. State the "
     "direction of travel and keep it constant."),
    ("crane", "crane / jib · 크레인",
     "Crane or jib: the camera changes height on a smooth arc while the subject "
     "stays framed."),
    ("mounted", "mounted to subject · 피사체에 장착",
     "Mounted to the subject or vehicle: the camera is fixed to the thing that is "
     "moving, so the subject stays still in frame while the world streams past."),
    ("in_scene", "held by a character · 인물이 든 기기",
     "Held by a character inside the scene: the recording device is a physical "
     "object in the world. If the device itself is visible in frame it is a SUBJECT, "
     "not the camera — the camera holds a static shot and the hand holding the "
     "device gets one plain sentence of its own."),
]

LENS = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("wide", "wide · 광각 (18–35mm)",
     "Wide lens: perspective is exaggerated, near things loom and far things fall "
     "away quickly, more of the room is included, and straight lines bend near the "
     "frame edges."),
    ("normal", "normal · 표준 (50mm)",
     "Normal lens: perspective reads as the eye sees it, with no compression and no "
     "exaggeration."),
    ("long", "long · 망원 (85mm+)",
     "Long lens: space is compressed, the background sits flat and close behind the "
     "subject, and the subject separates from it."),
]

DEPTH_OF_FIELD = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("deep", "deep focus · 전심 초점",
     "Deep focus: foreground, subject and background are all sharp."),
    ("shallow", "shallow · 얕은 심도",
     "Shallow depth of field: the subject is sharp and everything in front of and "
     "behind them falls out of focus."),
    ("rack", "rack focus · 포커스 이동",
     "Rack focus: focus shifts from one plane to another during the shot. State "
     "what starts sharp, what ends sharp, and when the shift happens."),
]

LIGHTING = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("soft_front", "soft frontal · 부드러운 정면광",
     "Soft frontal key: a large soft source near the lens axis; shadows are faint "
     "and the subject is evenly lit."),
    ("soft_side", "soft side · 부드러운 측광",
     "Soft side key: a large soft source roughly 45–90 degrees off axis; one side "
     "of the face is brighter with a gentle falloff into the other."),
    ("hard_side", "hard side · 강한 측광",
     "Hard side key: a small hard source off to one side; the shadow edge on the "
     "face is sharp and the unlit side goes dark."),
    ("back", "backlit / rim · 역광·림라이트",
     "Backlight: the key comes from behind the subject, drawing a bright edge along "
     "hair and shoulders while the front stays comparatively dark."),
    ("top", "top light · 톱라이트",
     "Top light: the source is directly above; brows and nose cast downward shadows "
     "and the eyes sit in shadow."),
    ("under", "underlit · 언더라이트",
     "Underlight: the source is below the face, reversing the usual shadow "
     "direction."),
    ("practical", "practical only · 실광원만",
     "Practical sources only: every bit of light comes from something visible in "
     "the frame — a lamp, a screen, a window, a fire. Name the source."),
    ("low_key", "low key · 로우키",
     "Low key: one dominant source, a very dark fill, most of the frame in shadow."),
    ("high_key", "high key · 하이키",
     "High key: bright and evenly filled, very little shadow anywhere."),
]

POV_MODE = [
    ("auto", "auto — 브리프에서 판단", ""),
    ("objective", "objective · 관찰 시점",
     "Objective: the camera is an outside observer. No character occupies the "
     "camera position and nobody looks into the lens."),
    ("subjective", "subjective · 밀착 시점",
     "Subjective: the camera sits close to one character's viewpoint without "
     "becoming their eyes — over the shoulder or beside the head."),
    ("pov", "POV · 1인칭",
     "First-person POV: the camera IS a character's eyes, at the eye height of the "
     "posture they are in. Whatever parts of their own body that posture puts in "
     "their line of sight are drawn foreshortened; their face, head and back never "
     "are. Their arms are in shot only while they are using them for something. "
     "Other characters may look into the lens."),
]

PERFORMANCE = [
    ("brief", "브리프대로 (기본)",
     ""),
    ("restrained", "절제 — 작게",
     "PERFORMANCE SCALE — RESTRAINED. Keep every movement small and state how small: "
     "a slight turn of the head, only the fingers moving, the body staying where it "
     "is. Under-ask rather than over-ask."),
    ("strong", "강하게 — 크게",
     "PERFORMANCE SCALE — FULL. Write the action at its full physical size. Give it "
     "real amplitude, real speed and real force where the brief calls for them, and "
     "do not soften, shrink or hedge a movement the brief asked for. Restraint is "
     "NOT the default here; describing the action smaller than asked is the failure "
     "mode to avoid."),
]

AXES = (
    ("shot_size", "Shot size · 사이즈", SHOT_SIZE),
    ("camera_angle", "Angle · 앵글", CAMERA_ANGLE),
    ("camera_mount", "Mount · 마운트", CAMERA_MOUNT),
    ("lens", "Lens · 렌즈", LENS),
    ("depth_of_field", "Depth of field · 심도", DEPTH_OF_FIELD),
    ("lighting", "Lighting key · 조명", LIGHTING),
    ("pov_mode", "POV · 시점", POV_MODE),
)


def labels(axis_list):
    return [row[1] for row in axis_list]


def text_for(axis_list, label):
    """Dropdown label -> the sentence for the model ('' for auto)."""
    for _key, lab, txt in axis_list:
        if lab == label:
            return txt
    return ""


def build_block(choices, register=""):
    """
    choices: {"shot_size": <label>, "camera_angle": <label>, ...}
    Emits ONLY the axes that were actually set. All-auto returns "".
    """
    lines = []
    for key, title, axis_list in AXES:
        txt = text_for(axis_list, choices.get(key, ""))
        if txt:
            lines.append("- {}: {}".format(title.split(" · ")[0], txt))

    perf = text_for(PERFORMANCE, choices.get("performance", ""))
    reg = (register or "").strip()

    if not lines and not perf and not reg:
        return ""

    out = ["################  SHOT SPECIFICATION  ################",
           "These are camera-department decisions that have already been made. Honour "
           "them exactly; do not substitute your own. Anything not listed here is still "
           "yours to choose from the brief."]
    if lines:
        out.append("")
        out.extend(lines)
    if perf:
        out.append("")
        out.append(perf)
    if reg:
        out.append("")
        out.append("REGISTER — write in the voice of the sample below. Match its "
                   "vocabulary, its directness and its level of detail. Copy the manner "
                   "of writing, never its content.")
        out.append("<REGISTER SAMPLE>")
        out.append(reg)
        out.append("</REGISTER SAMPLE>")
    out.append("######################################################")
    return "\n".join(out)


def summary_line(choices, register=""):
    """One report line naming what was set."""
    parts = []
    for key, title, axis_list in AXES:
        lab = choices.get(key, "")
        if lab and text_for(axis_list, lab):
            parts.append("{}={}".format(key, lab.split(" · ")[0]))
    perf = choices.get("performance", "")
    if perf and text_for(PERFORMANCE, perf):
        parts.append("performance={}".format(perf.split(" —")[0]))
    if (register or "").strip():
        parts.append("register={} chars".format(len(register.strip())))
    return "shot spec: " + ", ".join(parts) if parts else ""
