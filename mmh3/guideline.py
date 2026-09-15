# -*- coding: utf-8 -*-
"""
System-prompt construction for the MiniMax H3 prompt writer.

Encodes VIDEO_PROMPT_WRITING_GUIDE (T2VA / I2VA / FL2VA / L2VA) plus the
extended six-section REF2VA layout used by the DaSiWa MiniMaxH3Director node.
"""

import re

_LEADING_INDEX = re.compile(r"^\s*\d+\s*[.)]\s*")

MODES = ["AUTO", "T2VA", "I2VA", "FL2VA", "L2VA", "REF2VA"]

# ---------------------------------------------------------------- base rules

BASE_RULES = """Write one finished MiniMax H3 prompt. Output only the prompt, without commentary,
code fences, reasoning, examples or an additional copy of any field.

LANGUAGE AND CONTENT
Write descriptive prose in English. Dialogue follows the target language specified in
the DIALOGUE block. Preserve visible on-screen text and punctuation inside double quotes.
Preserve requested people, actions, dialogue meaning and event order. Fill unspecified
visual details only where they fit the brief and reference role; keep added detail
subordinate to the requested events. Describe visible or audible facts.

AUTHORITY AND SCOPE
Mode and supplied frame anchors determine the state at their timestamps. Explicit shot
camera settings determine that shot's view; explicit action settings determine physical
posture and action. Natural-language content supplies events and all unspecified choices.
Style tendencies and inferred detail fill remaining gaps. Conflicts that cannot coexist
must not be hidden by silently deleting requested content.

SHOTS
Use [Shot 1] without a timestamp. Each later cut opens a sequential [Shot N] followed by
At MM:SS.mmm, and a cut phrase. Use the actual final shot number in frame alignment lines.
Use the camera cuts to / the shot cuts to / the shot transitions to / the shot changes to /
the shot switches to. Dissolves, fades and wipes require an explicit request.
Event times inside a shot do not create cuts. Keep cut times increasing and within the
duration. A requested new camera angle can start a new shot even if the scene is unchanged.
When cuts are not requested, prefer continuous action rather than inventing extra shots.

CAMERA
Describe the current camera position, angle, distance and movement clearly. Use natural
sentences with these motion types where applicable: Zoom In, Zoom Out, Push In, Pull Out,
Pan Left, Pan Right, Truck Left, Truck Right, Tilt Up, Tilt Down, Pedestal Up, Pedestal Down,
Arc Shot, Tracking Shot, Static Shot, Shake Slightly, Shake Strongly, POV, Roll Clockwise,
Roll Counterclockwise. Add amplitude and speed when meaningful. Name the actor explicitly
so body motion and camera motion are distinct. A static camera is fixed WITHIN its shot;
another shot may use a different static camera position.

AUDIO FIELDS
overall_soundscape: 1-4 English sentences describing ambience, physical sounds and
nonverbal human sounds. Put dialogue, singing and in-world music on the shot timeline.
Use N/A for requested silence or a disabled soundscape setting.
non_diegetic_music: 1-3 English sentences about audience-only instrumentation, tempo,
rhythm and dynamics; N/A when absent or disabled. In-world music belongs on the timeline.
"""

# 462 tokens of speaker-ID and <d> mechanics. Dead weight when the video has no
# voice at all, which is most T2VA runs with dialogue_mode = none.
SPEAKER_RULES = """SPEAKERS AND DIALOGUE SYNTAX
Assign (S1), (S2), ... once in order of actual vocal events. A person's ID remains stable
across cuts. Subject numbers identify visual content and are independent of speaker IDs.
Use <Subject N> (Sx) when a speaker has a defined Subject; otherwise identify the speaker
in prose. Describe identity and delivery outside <d>[Language] spoken text</d>.
Bind each supplied voice reference to its actual target speaker, and cite the same
<Audio N> at each vocal event it governs. Reference indices are not speaker indices.
Describe only known voice features; distinguish requested delivery from unheard audio.
Separate dialogue lines are sequential unless the user explicitly requests group speech.
For unison, use one <d> block and the compound ID (S1,S2). For a line crossing a cut,
use <scenetrans> at the joining point in both parts and state that audio continues.
Use <cutoff> only for a requested interruption at the video end, not to fit excess text.
Voiceover uses says in an off-screen voiceover; if the corresponding character is visible,
state after </d> that their lips remain closed. Voice present only in a reused soundtrack
is identified by <Audio N>, without inventing an on-screen speaker.
"""


# ------------------------------------------------- director's constraints

CONSTRAINT_HEADER = """Apply the following only within the shot and reference role that requested them."""

CONSTRAINT_CAMERA_LOCK = """CAMERA LOCK
A fixed/static camera holds its position and framing within the specified shot. At a
requested cut, establish the next shot's new camera. Preserve one framing across the whole
video only when the user explicitly requests a global lock. A shot-local lock does not
override a later shot's camera settings."""

CONSTRAINT_OPERATOR = """CAMERA OPERATOR
Distinguish the recording viewpoint from a device visible as a prop. The viewpoint follows
the specified camera; a visible device moves as an object unless the brief links the two.
For POV, derive eye height and visible body parts from posture and gaze. Show only the
parts that fall within that view; retain any explicitly requested reflection."""

CONSTRAINT_PROHIBITION = """EXCLUSIONS
Express requested exclusions through a concrete allowed state where possible. Preserve
their meaning without adding unrelated limitations or repeating prohibited scene examples."""

CONSTRAINT_SUSTAINED = """REPEATING ACTION
Keep the requested action's physical relationships, direction and rhythm. Describe relevant
secondary motion without inventing escalation or completion. Distinguish moving elements
from stationary surroundings according to their actual materials and the requested scene."""

CONSTRAINT_NONVERBAL = """NONVERBAL SOUND
Describe requested breathing, laughter and other wordless vocal sounds in prose on the
timeline, with a stable speaker ID. The soundscape may summarize them. Wordless sound does
not require a language tag or invented syllables. Use <d> only for supplied vocal text,
dialogue or lyrics, under the selected dialogue policy."""

CONSTRAINT_VIEWPOINT = """VIEWPOINT CHANGE
At a requested viewpoint cut, establish whose view it is, eye height, gaze direction and
what is visible from there. Keep physical posture and relationships; recalculate screen
position, visible body surfaces and occlusion. A POV character's visible parts follow their
posture and gaze, not a fixed list. A cut need not move or rotate the characters."""

CONSTRAINT_REF_FRAMING = """REFERENCE ROLES
Content references supply only their assigned identity, wardrobe, pose, environment or
style. Compose the target view from the current shot's camera, not the source framing.
A concrete frame anchor fixes composition only at its assigned timestamp. Describe that
composition accurately there; place requested changes after a first anchor or before a
last anchor. Later unanchored shots can use different views of the same physical scene."""

CONSTRAINT_CONTINUITY = """CONTINUITY ACROSS CUTS
Keep identity, wardrobe, physical posture, ongoing action, room geometry and the actual
light sources unless the brief changes them. At each new camera position, recompute screen
left/right, foreground/background, scale, visible surfaces, occlusion and light direction
relative to the camera. Repeat only identifying details visible and relevant in that shot.
Describe each participant relative to the current camera when needed to disambiguate the
view. Reference pictures and previous shots do not lock later camera framing. New-scene
cards may change location/time; same-moment cards retain the physical scene and action,
not the previous camera or image-space coordinates."""

CONSTRAINT_TAIL = """Keep requested events complete; add only relevant, compatible visible or audible detail."""


# Every section above is conditional — each one opens with "Trigger: ...". They used to
# ship on every single run and cost about 2,400 tokens whether or not the brief had
# anything to do with them. The keywords below decide in Python instead, so a brief that
# never mentions the camera never pays for the camera-lock rules.

_TRIG = {
    "CAMERA_LOCK": (
        "카메라 고정", "카메라는 고정", "고정된 카메라", "고정 촬영", "구도 고정",
        "fixed camera", "camera is fixed", "static shot", "locked-off", "locked off",
        "no camera movement", "camera stays fixed"),
    "OPERATOR": (
        "촬영", "찍", "카메라를 들", "핸드폰", "폰으로", "캠", "1인칭", "시점",
        "filming", "records", "recording", "camera", "phone", "pov",
        "first-person", "viewfinder", "operator", "held by", "footage"),
    "PROHIBITION": (
        "안 ", "안하", "않", "말고", "마라", "마.", "없이", "금지", "절대",
        "빼고", "제외",
        "not ", "never", "without", "avoid", "must not", "do not", "don't",
        "no one", "nothing"),
    "SUSTAINED": (
        "계속", "반복", "내내", "유지", "지속", "리듬", "왕복", "규칙적",
        "continuous", "repeat", "rhythm", "keeps", "throughout", "steady",
        "over and over", "cycle", "sustained", "thrust"),
    "NONVERBAL": (
        "신음", "숨", "호흡", "헐떡", "웃", "울", "비명", "소리를 내", "목소리",
        "moan", "breath", "gasp", "pant", "laugh", "cry", "scream", "sigh",
        "groan", "whimper", "vocal", "voice"),
    "VIEWPOINT": (
        "시점 전환", "시점이 바", "시점으로 바", "pov로", "pov 로", "1인칭으로",
        "3인칭에서", "관찰 시점에서", "어깨너머로 바", "시점을 바",
        "viewpoint change", "switches to pov", "cuts to pov", "becomes pov",
        "back to third person", "point of view changes", "shifts to first-person"),
    "CONTINUITY": (
        "샷 2", "샷2", "컷 후", "다음 샷", "장면 유지", "구도 유지", "이어진다",
        "shot 2", "next shot", "after the cut", "continues across"),
    "REF_FRAMING": (
        "다른 각도", "각도로 촬영", "각도를 다르", "다른 앵글", "앵글로 촬영",
        "이미지와 다른", "레퍼런스와 다른", "사진과 다른", "구도로 다시",
        "different angle", "different framing", "not the same angle",
        "another angle", "re-frame", "reframed from"),
}

# A shot-spec choice can also switch a section on even when the brief is silent.
_AXIS_TRIG = {
    "camera_mount": {"tripod": "CAMERA_LOCK",
                     "in_scene": "OPERATOR", "mounted": "OPERATOR"},
    "pov_mode": {"pov": "OPERATOR", "subjective": "OPERATOR"},
    "performance": {"restrained": "SUSTAINED", "strong": "SUSTAINED"},
    # the Brief Composer's camera track sets these; a viewpoint that changes needs the
    # transition rules, and a content reference shot from a new angle needs section 7.
    "viewpoint_change": {"pov": "VIEWPOINT", "objective": "VIEWPOINT",
                         "subjective": "VIEWPOINT", "shoulder": "VIEWPOINT"},
    "ref_framing": {"new_angle": "REF_FRAMING", "content_only": "REF_FRAMING"},
    # the Shot Builder sets this whenever it emitted more than one shot
    "multi_shot": {"yes": "CONTINUITY"},
}


def build_constraints(brief="", shot_labels=None):
    """Only the constraint sections this brief actually needs."""
    low = (brief or "").lower()
    want = set()
    for key, words in _TRIG.items():
        if any(w in low for w in words):
            want.add(key)

    for axis, mapping in _AXIS_TRIG.items():
        lab = (shot_labels or {}).get(axis, "")
        for token, key in mapping.items():
            if token in str(lab).lower():
                want.add(key)

    if not want:
        return CONSTRAINT_HEADER + "\n" + CONSTRAINT_TAIL, []

    order = ["CAMERA_LOCK", "OPERATOR", "PROHIBITION", "SUSTAINED", "NONVERBAL",
             "VIEWPOINT", "REF_FRAMING", "CONTINUITY"]
    blocks = [CONSTRAINT_HEADER]
    for key in order:
        if key in want:
            blocks.append(globals()["CONSTRAINT_" + key])
    blocks.append(CONSTRAINT_TAIL)
    return "\n".join(blocks), [k for k in order if k in want]



# ---------------------------------------------------------------- per-mode

MODE_BLOCKS = {
    'T2VA': """MODE T2VA
Output integrated_multimodal_description, overall_soundscape, non_diegetic_music in that
order, each label followed by a colon. Start the description with [Shot 1], style and
initial composition. Establish the scene from the brief. There is no alignment line.""",
    'I2VA': """MODE I2VA
First output this alignment line:
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
Then output integrated_multimodal_description, overall_soundscape, non_diegetic_music.
Each label is followed by a colon. Start the description with [Shot 1], style, subjects,
composition and scene anchors actually visible in the first frame, followed by development.
The image fixes 0 seconds only. Changes occur on screen after that moment; later cuts may
use new camera positions. An incompatible request is a conflict, not permission to erase it.""",
    'FL2VA': """MODE FL2VA
First output this alignment line, with the actual final shot number:
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot {N}) aligns with the {S}-second mark of the target video.
Then output integrated_multimodal_description, overall_soundscape, non_diegetic_music.
Each label is followed by a colon. [Shot 1] starts with style and the first image's state.
Describe a plausible path to the final image at the end. Prefer one continuous shot unless
cuts are requested. The two anchors constrain their own timestamps, not all intervening views.
The final image takes precedence over a generic instruction to keep action unfinished.""",
    'L2VA': """MODE L2VA
First output this alignment line, with the actual final shot number:
How the reference pictures align with the target video — <Picture 1> (from [Shot {N}]) aligns with the {S}-second mark of the target video.
Then output integrated_multimodal_description, overall_soundscape, non_diegetic_music.
Each label is followed by a colon. [Shot 1] begins with style and a plausible preceding state.
The image fixes the END, not the opening. Place actions and camera changes before the final
moment so the last shot reaches the image's actual pose, composition and object state.
The final image takes precedence over a generic instruction to keep action unfinished.""",
    'REF2VA': """MODE REF2VA
{PICTURES}
Output six sections directly, in this order, with each label followed by a colon:
subject_definitions, summary, retention_analysis, detailed_description,
overall_soundscape, non_diegetic_music. There is no outer description label or alignment line.
Place the style in detailed_description BEFORE [Shot 1], then write shots in playback order.

REFERENCE DEFINITIONS
<Subject N> denotes referenced visible content, including people, props, environments or
attributes. One subject may use several assets; one asset may supply several subjects.
Define each separately tracked item once, state its sources and the assigned features.
Define <Picture N> separately only for a concrete frame or storyboard role; otherwise cite
it as a Subject's source. <Video N> denotes whole-video editing, continuation or structure.
<Audio N> denotes a supplied audio source, with its role and target. Use the supplied asset
numbers. Unreferenced people can be identified in prose, or assigned a stable Subject label
when necessary; state that they have no source and do not invent retention relationships.
For a POV person define only content applicable to their actual visible parts across shots.

SUMMARY AND RETENTION
summary starts with the applicable bracketed task types, joined by +:
reference generation / keyframe completion / video editing / video continuation /
audio reuse / audio reference. Include only actual relationships.
retention_analysis gives one line for each used reference label with its application and
relationship. Visual markers: fully_preserved / partially_preserved / attribute_transfer /
weak_reference. Judge retention within the declared role. A new camera angle does not by
itself change identity retention. attribute_transfer requires a real source and target;
state the property transferred and limit its scope. New unreferenced content has no marker.

DESCRIPTION
At first appearance, describe important identifying features, position and current action
within the actual view. Later shots use stable labels plus relevant visible details and
changes. Recompute framing from each shot's camera. A reference's framing applies only if
its assigned role is a frame or composition anchor at that point.
"""
}


# ------------------------------------------------- what the pictures ARE, per mode

# In I2VA / L2VA / FL2VA the supplied picture is a LITERAL FRAME of the target video.
# Calling it a "reference image" — which every part of this package used to do — primes
# the model into REF2VA behaviour: it treats the picture as loose inspiration for
# appearance and then stages its own opening frame. Only REF2VA has references.
_PICTURE_KIND = {
    "I2VA": {
        "noun": "first-frame picture",
        "label": "FIRST FRAME",
        "what": "<Picture 1> is the LITERAL FIRST FRAME of the target video, the image on "
                "screen at 0.00 seconds. It is not a reference, not inspiration and not a "
                "style sample. Whatever it shows IS the video at that instant.",
    },
    "L2VA": {
        "noun": "final-frame picture",
        "label": "FINAL FRAME",
        "what": "<Picture 1> is the LITERAL FINAL FRAME of the target video, the image on "
                "screen at the end. It is not a reference, not inspiration and not a style "
                "sample. Whatever it shows IS the video at that instant.",
    },
    "FL2VA": {
        "noun": "end-frame pictures",
        "label": "FIRST AND FINAL FRAMES",
        "what": "<Picture 1> is the LITERAL FIRST FRAME at 0.00 seconds and <Picture 2> is "
                "the LITERAL FINAL FRAME. They are not references, not inspiration and not "
                "style samples. Whatever they show IS the video at those two instants.",
    },
    "REF2VA": {
        "noun": "reference image",
        "label": "REFERENCES",
        "what": "Apply each image only within its assigned reference role. Content references "
                "guide identity or attributes; explicitly assigned frame anchors fix their timestamp.",
    },
}


ESTABLISH_BLOCK = """Establish the visible subjects, setting and composition appropriate to this shot.
The anchor fixes its own moment only. Later camera changes use the same scene viewed from
the new camera; source-image screen positions are not persistent world coordinates."""


def picture_kind(mode):
    """What the supplied pictures actually are in this mode."""
    return _PICTURE_KIND.get(mode, _PICTURE_KIND["REF2VA"])


def picture_noun(mode, n=1):
    k = picture_kind(mode)["noun"]
    return k if n == 1 else k + "s"


def _fmt_ts(seconds: float) -> str:
    """MM:SS.mmm — the cut-time format the spec requires."""
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    return "{:02d}:{:06.3f}".format(m, seconds - m * 60)


def _fmt_seconds(duration: float) -> str:
    return "{:.2f}".format(float(duration))


def build_system_prompt(mode: str, duration: float, shot_hint: int, style: dict,
                        dialogue_policy: str, soundscape_on: bool, music_on: bool,
                        extra_directives: str = "", dialogue_language: str = "English",
                        n_images: int = 0, template_prompt: str = "", roles_block: str = "",
                        shot_block: str = "", other_items=None, picture_numbers=None,
                        brief: str = "", shot_labels: dict = None,
                        skip_image_checklist: bool = False, max_words: int = 500,
                        has_audio_refs: bool = True, continuation: bool = False,
                        continuation_context: str = "") -> str:
    labels = dict(shot_labels or {})
    if shot_hint > 1:
        labels["multi_shot"] = "yes"
    cons, used = build_constraints(brief, labels)
    parts = [BASE_RULES, cons]
    if dialogue_policy != "none" or "NONVERBAL" in used:
        parts.append(SPEAKER_RULES)
    nums = list(picture_numbers or range(1, n_images + 1))
    pics = ("Available images: " + ", ".join("<Picture {}>".format(i) for i in nums)
            if n_images else "No images were supplied; use only known request content.")
    pics += "\n" + picture_kind(mode)["what"]
    block = MODE_BLOCKS.get(mode, MODE_BLOCKS["T2VA"])
    block = block.replace("{N}", str(shot_hint) if shot_hint > 0 else "N")
    block = block.replace("{S}", _fmt_seconds(duration)).replace("{PICTURES}", pics)
    parts.append(block)
    if n_images and mode != "REF2VA":
        parts.append(pics + "\n" + ESTABLISH_BLOCK)
    if roles_block:
        parts.append(roles_block)
    if other_items:
        parts.append("SUPPLIED NON-IMAGE ASSETS (not viewed or heard by the writer)\n"
                     + "\n".join(other_items)
                     + "\nUse their listed labels and user-assigned roles. Sharing an upload slot "
                     "does not establish a voice binding. Describe content only when supplied "
                     "by the user or an actual analysis, not from filenames.")
    if mode == "REF2VA" and has_audio_refs:
        parts.append("AUDIO REFERENCE RELATIONSHIPS\n"
                     "Define each used audio label and its role. For voice timbre, bind it to "
                     "the target speaker's existing ID, and cite it at governed vocal events. "
                     "Use fully_copy / partially_copy / reference / weak_reference according "
                     "to signal reuse. Put ambience relationships in overall_soundscape and "
                     "score relationships in non_diegetic_music. Use the same source label "
                     "for all assigned roles. Source words are used only when requested and "
                     "actually supplied; voice-timbre references do not supply target dialogue.")
    if shot_block:
        parts.append(shot_block)
    placement = "before [Shot 1] in detailed_description" if mode == "REF2VA" else "after [Shot 1]"
    if style and style.get("style_line"):
        sb = ["STYLE: place this style line " + placement + ": " + style["style_line"],
              "Apply preset tendencies only to choices left open by the shot and frame anchors."]
        for key in ("render", "lighting", "camera", "motion"):
            if style.get(key):
                sb.append(key + ": " + style[key])
        if soundscape_on and style.get("soundscape"):
            sb.append("soundscape tendency: " + style["soundscape"])
        if music_on and style.get("music"):
            sb.append("score tendency: " + style["music"])
        if style.get("avoid"):
            sb.append("preset exclusions: " + style["avoid"])
        parts.append("\n".join(sb))
    else:
        parts.append("STYLE: derive from frame images when anchored, otherwise the brief. "
                     "Place it " + placement + ".")
    tb = ["TIMING: full clip duration is {} seconds.".format(_fmt_seconds(duration))]
    if shot_hint > 0:
        tb.append("Write exactly {} shots. Preserve explicit cut times.".format(shot_hint))
        if shot_hint > 1:
            tb.append("For cuts with no assigned time, use these fallback times:")
            for i in range(1, shot_hint):
                tb.append("[Shot {}] At {},".format(i + 1, _fmt_ts(float(duration) * i / shot_hint)))
    else:
        tb.append("Honor all explicitly requested shot changes; otherwise prefer one continuous shot.")
    tb.append("Speech times are events, not cuts. Do not shorten or omit supplied lines to fit. "
              "Preserve explicit timings; conflicting timings require a report, not silent repair.")
    parts.append("\n".join(tb))
    if dialogue_policy == "none":
        parts.append("DIALOGUE: no words, singing or narration. Requested wordless sounds "
                     "remain prose events. Do not create <d> blocks.")
    else:
        lang = dialogue_language or "English"
        parts.append("DIALOGUE TARGET LANGUAGE: " + lang + ".\n"
                     "Apply this equally to dialogue typed in natural-language scene text and "
                     "dedicated dialogue rows. Preserve lines already in the target language, "
                     "including punctuation. Translate other lines into natural spoken " + lang +
                     " preserving meaning, tone and speaker. Wrap each line in <d>[" + lang +
                     "] ...</d>. Preserve every supplied line; do not shorten or delete it for "
                     "duration, translation difficulty or word limits. Describe delivery outside <d>. "
                     "Speech duration depends on language; English word counts do not measure Japanese.")
        if dialogue_policy == "speech":
            parts.append("Speech is requested. Use supplied lines; invent brief dialogue only "
                         "where speech is requested but no words were supplied.")
        elif dialogue_policy == "verbatim":
            parts.append("Use all supplied dialogue rows in order with their assigned speakers. "
                         "The target-language rule determines copying versus translation.")
        else:
            parts.append("Add speech only where the brief requests or clearly implies it.")
    if not soundscape_on:
        parts.append("overall_soundscape: N/A")
    if not music_on:
        parts.append("non_diegetic_music: N/A")
    if template_prompt.strip():
        parts.append(TEMPLATE_BLOCK.format(template=template_prompt.strip()))
    if continuation:
        parts.append(CHAIN_CONTINUATION)
        parts.append(continuation_context or "Context placement is unknown. Continue known state "
                     "at the start of the clip without assigning a numeric overlap offset.")
    if extra_directives.strip():
        parts.append("ADDITIONAL REQUEST (within the mode and shot scope):\n" + extra_directives.strip())
    hi = max(120, int(max_words or 500))
    parts.append("LENGTH: target at most {} English words, with no minimum. Prioritize actions, "
                 "camera, complete dialogue, reference bindings and relevant visible identity. "
                 "Scale detail to scene complexity; exceed the target only to retain required "
                 "content. Output only the finished prompt.".format(hi))
    return "\n\n".join(parts)



# 이어붙이기(H3 Project Suite 체인)가 켜진 클립에만 붙는 블록.
#
# 규칙은 ethanfel/ComfyUI-MiniMaxH3-Context-Loop 의 H3_CHAIN_FORMAT_GUIDE 에서 가져왔다:
# 겹치는 프레임은 모델이 이미 보고 있으니 다시 서술하지 않고, 진행 중이던 동작을 이어서
# 시작하고, 다음 클립이 이을 수 있게 동작이 진행 중인 채로 끝낸다.
#
# 원본 가이드는 규칙마다 예시 문장을 붙여 두었는데 여기서는 전부 뺐다. 가이드라인 안의
# 예시 문장은 출력에 그대로 복사돼 나온다. 금지문도 쓰지 않고, 무엇을 하라고만 적는다.
CHAIN_CONTINUATION = """CONTINUATION
[Shot 1] belongs to the new clip's timeline, starting at 0 seconds. All timestamps use
that full timeline. Continue known motion and physical state without replaying its onset.
Use the context placement supplied below; do not invent an overlap length.
An explicit final frame or requested completion determines the ending. Otherwise ongoing
action may continue through the end to support a following clip."""


TEMPLATE_BLOCK = """STRUCTURAL TEMPLATE
Use only the supplied template's field organization and sentence structure. The current
mode, shot settings, reference roles and brief determine content, language and timing.
Scene details, dialogue, indices and timestamps come from the current request.
<TEMPLATE>
{template}
</TEMPLATE>"""


ENGLISH_RETRY_DIRECTIVE = (
    "Your previous attempt contained non-English words outside <d>...</d> and outside "
    "\"quoted on-screen text\". That is the single worst failure mode. Write EVERY "
    "descriptive word in English this time. Translate the brief's meaning; do not echo "
    "its language.")

ENGLISH_REPAIR_SYSTEM = """Translate only non-English descriptive prose into English. Preserve all fields,
section order, shot labels, timestamps, reference labels and speaker IDs. Preserve text
inside <d> and quoted on-screen text exactly. Output only the prompt."""


def build_english_repair_message(prompt_text):
    return "Rewrite this prompt in English:\n\n" + prompt_text


def english_style_label(label):
    """Style labels are bilingual in the UI; send only the English half to the model."""
    if not label:
        return "auto"
    part = label.split(" - ", 1)[-1] if " - " in label else label
    part = part.split("(")[0]
    part = "".join(ch for ch in part if ord(ch) < 0x2E80)
    part = _LEADING_INDEX.sub("", part).strip(" -")
    return part or "auto"


def build_user_message(brief: str, mode: str, duration: float, dialogue_text: str,
                       dialogue_language: str, style_label: str,
                       skip_image_checklist: bool = False) -> str:
    lines = ["BRIEF — INPUT ONLY. It may be written in Korean or another language.",
             "Translate its intent; write the prompt itself in English.",
             "-----",
             brief.strip() if brief.strip() else "(empty — invent a simple, coherent scene)",
             "-----",
             "",
             "MODE: " + mode,
             "DURATION: {} seconds".format(_fmt_seconds(duration)),
             "STYLE: " + english_style_label(style_label),
             "OUTPUT LANGUAGE: English"]
    if dialogue_text and dialogue_text.strip():
        lines += ["", "DIALOGUE — the spoken lines, in order. Every one is wrapped as "
                      "<d>[{lang}] ...</d> and spoken in {lang}. Each line says whether to "
                      "copy it or translate it into {lang}:".format(
                          lang=dialogue_language or "English"),
                  dialogue_text.strip()]
    else:
        lines += ["DIALOGUE LANGUAGE (if any speech is written): {}".format(
            dialogue_language or "English")]
    if mode in ("I2VA", "FL2VA", "L2VA", "REF2VA"):
        _k = picture_kind(mode)
        lines += ["", "PICTURE(S) ATTACHED — " + _k["label"], _k["what"]]
        if skip_image_checklist:
            # A vision pass already produced a full inventory; repeating the checklist
            # here just spends tokens on instructions that have been carried out.
            lines += ["Work from the inventory supplied below rather than from your own "
                      "glance at the image."]
            return "\n".join(lines)
        lines += ["Use only visible evidence and assigned reference roles. Establish the "
                  "anchor composition at its timestamp. In later shots, preserve identity "
                  "and physical scene relationships but recompute the view from that shot's "
                  "camera. Include relevant visible features, not a full repeated inventory."]
    return "\n".join(lines)
