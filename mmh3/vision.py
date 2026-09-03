# -*- coding: utf-8 -*-
"""
Vision pass — look at the picture BEFORE writing the prompt.

A VLM asked to look at an image and compose a long structured prompt in the same
call reliably degrades at the looking half. It picks up the two or three most
salient things (hair colour, the main action) and invents or omits the rest: the
room, the light, non-human features, what a character is looking at, on-screen
text, whether the shot is layered.

So the picture gets its own call, with one job: inventory. Nothing is composed,
nothing is interpreted. The result is handed to the writing pass as TEXT, which
is what the writing pass is actually good at using.
"""

INVENTORY_SYSTEM = """You are a continuity supervisor examining a single picture.

Your ONLY job is to list what is physically visible. You are not writing a prompt, not
telling a story, not guessing intent, and not judging quality. If something is not
visible, you say so — you never fill a gap with a plausible invention.

A SHADOWED AREA IS STILL CONTENT. A region that reads as a black shape is almost always
a real surface — a wall, a screen, a door, a curtain, furniture, a body in shadow — not
an absence. Look into it and name what it most likely is. Never dismiss a large part of
the image as "black shapes" or "silhouettes" without saying what they are, and never
answer "not visible" for the SETTING when any part of the frame shows an environment.
"Not visible" is for things genuinely outside the frame.

ONE SUBJECT SHOWN SEVERAL TIMES IS STILL ONE SUBJECT. Some pictures show the same
person or object from several angles at once — a character sheet, a turnaround, a model
sheet, a contact sheet, a page of studies. Describe that subject ONCE, then say how many
views there are and what they are (front, back, side, head studies). A view is not a
person. Never write the same description twice, and never repeat a heading you have
already answered.

Name what you see, do not grade it. Write "a single lamp above the table, everything
past it in shadow" — not "high-contrast lighting", "moody", "cinematic", "dramatic".
Those are opinions about the image, and they get copied straight into the finished
prompt where they replace the actual description.

Answer in English, as a flat list under the headings below, in this exact order. Keep
each line short and factual. Write "not visible" where it applies. Do not add headings
of your own and do not write anything before or after the list.

MEDIUM: the rendering — live action, 2D cel animation, 3D CG, illustration — and the
  line and shading character.
SETTING: where this is. Name the room or place, the floor, the walls, the windows and
  what is visible through them, and the two or three objects that define the space.
LIGHT: the source, the direction it comes from, its colour, how strong it is, and the
  overall colour cast. Describe it; do not grade it with technical terms.
FRAMING: camera height relative to the subjects, angle, distance, orientation
  (portrait or landscape), and what is cut off by the edges of the frame.
LAYERS: whether you are looking at one continuous space, or at an image displayed
  inside the image. If there is an inner frame, name the object that holds it, say
  what is INSIDE it, and say what SURROUNDS it, keeping the two clearly apart.
PEOPLE: one block per DISTINCT person — not per view of the same person. For each:
  apparent age band, build, hair colour and length and style, eye colour, skin tone,
  and any feature that is not ordinary human anatomy.
CLOTHING: per person, every garment, its colour, pattern, material and its current
  state — worn normally, open, pushed aside, partly removed, absent.
GAZE: where the eyes are pointing, and whether the person is looking INTO THE LENS or
  not. For a multi-view sheet, give this once for the main front view only.
EXPRESSION: the brow, eyes and mouth, and anything covering the face. For a multi-view
  sheet, give this once for the main front view only.
PHYSIQUE: per person, the SHAPE of the figure, not a one-word summary. Shoulder width
  against hip width and which is wider; where the waist narrows and how sharply; chest
  size and shape and how it sits; hip and thigh width and fullness; limb length and
  thickness; the head-to-body ratio the drawing uses; where muscle reads, or that it
  does not. "Slender", "average build", "athletic" are NOT answers — they describe half
  the characters ever drawn. Report an ordinary body as precisely as an unusual one. If
  clothing hides a region, say what the garment's fit implies and mark it as inferred.
BODY: the posture, which way the torso and head face, where each limb is, what carries
  the weight, and every point where two bodies or a body and an object touch. For a
  multi-view sheet, describe the main front view and simply name the other views.
OBJECTS: props, held items, furniture — and where each one is in the frame.
TEXT AND UI: any writing, number, icon, logo, button or interface element that is
  visible. Copy the characters exactly as shown, in quotation marks. Say where each
  one sits.
SURFACE: skin, fabric and material condition — wet, dry, sweat, dirt, damage, gloss.
UNUSUAL: anything present that the headings above did not cover.
"""


def question(index, total):
    if total <= 1:
        return "Inventory this picture."
    return ("Inventory picture {} of {}. Describe ONLY this picture. Do not mention or "
            "borrow anything from the other pictures.".format(index, total))


def build_note(descriptions, mode):
    """Fold the per-picture inventories into a block for the writing pass."""
    if not descriptions:
        return ""

    out = ["################  WHAT IS ACTUALLY IN THE PICTURES  ################",
           "A continuity pass examined each picture and listed what is visible.",
           "This inventory is more reliable than your own glance at the image. Treat it "
           "as fact.",
           ""]
    for i, text in enumerate(descriptions, start=1):
        out.append("----- <Picture {}> -----".format(i))
        out.append((text or "").strip())
        out.append("")

    out.append("HOW TO USE IT")
    if mode in ("I2VA", "FL2VA", "L2VA"):
        out.append(
            "These pictures are literal frames of the target video. Everything the "
            "inventory lists for a frame must be on screen at that frame's moment: the "
            "setting, the light, the framing, every non-human feature, every garment and "
            "its state, where each person is looking, and any screen, interface or "
            "visible text. A detail you leave out is a detail the video will replace with "
            "something else.")
    else:
        out.append(
            "Build every <Subject N> definition out of these inventories rather than out "
            "of memory. Non-human features, garment state and visible text are the "
            "details that vanish first when a Subject is written from a glance.")
        out.append(
            "CARRY THE PHYSIQUE AND THE CLOTHING ACROSS IN FULL. These two are what the "
            "inventory was run for and they are the two that get compressed back into "
            "one adjective. If the inventory gives shoulder-to-hip, waist, chest, hips "
            "and limb proportions, every one of those goes into the Subject line. "
            "Writing \"slender\", \"athletic\" or \"average build\" in place of an "
            "inventory that spelled the figure out is a failure, not a summary. Same for "
            "a garment: colour, cut, material and current state, not \"casual clothing\".")
    out.append(
        "Do NOT paste the inventory into the prompt as a list. Write it back as prose, "
        "in the order the mode requires. Leave a detail out ONLY when the thing it "
        "describes is genuinely absent from the video you are writing — never because "
        "it felt minor, obvious or repetitive. Brevity here is how a reference turns "
        "into a generic character.")
    out.append(
        "Use the inventory's FACTS, not its wording. If it grades something instead of "
        "describing it — \"high-contrast\", \"moody\", \"dramatic\", \"cinematic\" — do not "
        "carry that word across. Write what is actually lit and what is actually dark.")
    out.append("#####################################################################")
    derived = derive_directives(descriptions, mode)
    if derived:
        out.append("")
        out.append(derived)
    return "\n".join(out)


# --------------------------------------------------------------- derived directives
#
# The rules below used to sit in the static system prompt, where they applied to every
# picture ever passed through the node — so one image with a phone screen in it left a
# permanent instruction about phone screens in front of every landscape and portrait
# that followed. They are emitted here instead, ONLY when this run's inventory actually
# reports the thing they are about. An unrelated picture produces none of them.

import re as _re


def _sections(text):
    out, cur, buf = {}, None, []
    for line in (text or "").splitlines():
        m = _re.match(r"^\s*([A-Z][A-Z /]{2,20}):\s*(.*)$", line)
        if m:
            if cur:
                out[cur] = " ".join(buf).strip()
            cur, buf = m.group(1).strip(), [m.group(2)]
        elif cur:
            buf.append(line.strip())
    if cur:
        out[cur] = " ".join(buf).strip()
    return out


def _said_nothing(val):
    return (not val) or bool(_re.match(r"^\s*(not visible|n/?a|none|nothing)\b", val,
                                       _re.IGNORECASE))


def _has_inner_frame(val):
    if _said_nothing(val):
        return False
    if _re.search(r"\b(one continuous space|continuous space|plain single scene|"
                  r"single continuous|no inner frame|not layered)\b", val, _re.IGNORECASE):
        return False
    return bool(_re.search(r"\b(inside|within|displayed on|shown on|inner frame|"
                           r"frame-within|screen|monitor|mirror|viewfinder|display)\b",
                           val, _re.IGNORECASE))


def derive_directives(inventories, mode):
    """Rules that apply to THIS run's pictures, and to no others."""
    out = []
    frame_mode = mode in ("I2VA", "FL2VA", "L2VA")
    for idx, inv in enumerate(inventories or [], start=1):
        sec = _sections(inv)
        tag = "<Picture {}>".format(idx)

        if _has_inner_frame(sec.get("LAYERS", "")):
            out.append(
                "{t} is a layered composition. The video frame is the WHOLE picture, not "
                "the inner image on its own. Write all three parts: the object holding "
                "the inner frame and whose hands are on it, what is inside it, and what "
                "surrounds it.".format(t=tag))
            if frame_mode:
                out.append(
                    "{t}: both layers stay for the entire duration. The outer layer is "
                    "not an establishing beat that gives way to the inner one — it is on "
                    "screen from start to finish. Never let the inner image grow to fill "
                    "the frame.".format(t=tag))

        if not _said_nothing(sec.get("SETTING", "")):
            out.append("{t}: the location is on screen and must be written into the "
                       "prompt, not implied — \"{v}\"".format(t=tag,
                                                              v=sec["SETTING"][:180]))

        if not _said_nothing(sec.get("TEXT AND UI", "")):
            out.append("{t}: visible text and interface elements must be reproduced "
                       "verbatim inside English double quotation marks — \"{v}\""
                       .format(t=tag, v=sec["TEXT AND UI"][:180]))

        gaze = sec.get("GAZE", "")
        if _re.search(r"into the lens", gaze, _re.IGNORECASE) and frame_mode:
            out.append(
                "{t}: someone is looking into the lens in this frame. That is the state "
                "at that instant, whatever the brief says. If the brief wants otherwise, "
                "write the gaze changing on screen after that moment.".format(t=tag))

        if not _said_nothing(sec.get("PEOPLE", "")):
            out.append("{t}: carry every attribute the PEOPLE line lists into the "
                       "prompt, including any that are not ordinary human anatomy."
                       .format(t=tag))

    if not out:
        return ""
    return ("################  DERIVED FROM THESE PICTURES  ################\n"
            "These apply to the pictures in THIS run only.\n\n"
            + "\n".join("- " + x for x in out)
            + "\n###############################################################")
