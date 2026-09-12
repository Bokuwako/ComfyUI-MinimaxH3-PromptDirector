# -*- coding: utf-8 -*-
"""Deterministic clean-up / validation of a MiniMax H3 prompt.

LLMs drift. This module repairs the mechanical parts of the spec (field layout,
shot numbering, cut timestamps, instruction line) and reports whatever it cannot
fix so the operator can see it.
"""

import re

FIELD_IMD = "integrated_multimodal_description"
FIELD_SS = "overall_soundscape"
FIELD_MUS = "non_diegetic_music"

SHOT_RE = re.compile(r"\[\s*Shot\s*(\d+)\s*\]", re.IGNORECASE)
_TS_CLOCK = re.compile(
    r"^\s*At\s+(\d{1,3}):(\d{1,2})(?:\.(\d{1,3}))?\s*(?:seconds?)?\s*,?\s*", re.IGNORECASE)
_TS_PLAIN = re.compile(
    r"^\s*At\s+(\d{1,3}(?:\.\d{1,3})?)\s*(?:s|sec|secs|seconds?)\s*,?\s*", re.IGNORECASE)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)

CUT_PHRASES = ("the camera cuts to", "the shot cuts to", "the shot transitions to",
               "the shot changes to", "the shot switches to")

INSTRUCTION_I2VA = ("For the target video, at 0.00 seconds into the target video, "
                    "<Picture 1> (from [Shot 1]) is fully referenced.")
INSTRUCTION_FL2VA = ("How the reference pictures align with the target video — Picture 1 "
                     "(from Shot 1) aligns with the 0.00-second mark of the target video; "
                     "Picture 2 (from Shot {n}) aligns with the {s}-second mark of the target video.")
INSTRUCTION_L2VA = ("How the reference pictures align with the target video — <Picture 1> "
                    "(from [Shot {n}]) aligns with the {s}-second mark of the target video.")


# Hangul (incl. jamo), kana, CJK ideographs, Cyrillic, Thai, Arabic, Hebrew, Devanagari.
_CJK_ETC = re.compile(
    "[ᄀ-ᇿ぀-ヿ㄰-㆏㐀-䶿一-鿿"
    "가-힯Ѐ-ӿ฀-๿؀-ۿ֐-׿ऀ-ॿ]+")


def find_non_english(text):
    """Non-Latin runs that sit OUTSIDE <d>...</d> and outside "quoted screen text"."""
    if not text:
        return []
    scrub = re.sub(r"<d>.*?</d>", " ", text, flags=re.DOTALL)
    scrub = re.sub(r"\"[^\"]*\"", " ", scrub)
    return _CJK_ETC.findall(scrub)


_SCRIPTS = {
    "hangul": re.compile("[가-힣ᄀ-ᇿ]"),
    "kana": re.compile("[぀-ヿ]"),
    "han": re.compile("[㐀-䶿一-鿿]"),
    "latin": re.compile("[A-Za-z]"),
    "cyrillic": re.compile("[Ѐ-ӿ]"),
}
_LANG_EXPECTS = (
    ("japan", "kana"), ("nihon", "kana"),
    ("korea", "hangul"), ("hangul", "hangul"),
    ("chin", "han"), ("mandarin", "han"), ("cantonese", "han"),
    ("english", "latin"), ("spanish", "latin"), ("french", "latin"),
    ("german", "latin"), ("portuguese", "latin"),
    ("russ", "cyrillic"),
)


def script_matches(text, language):
    """Is `text` already written in `language`?  None when we cannot tell.

    Used before the prompt is written, to decide whether a line the user typed on a
    shot card has to be translated into the chosen dialogue language or copied as is.
    """
    expect = next((s for k, s in _LANG_EXPECTS if k in (language or "").lower()), None)
    if not expect or not (text or "").strip():
        return None
    present = [name for name, rx in _SCRIPTS.items() if rx.search(text)]
    if not present:
        return None
    if expect in present:
        return True
    # Japanese written entirely in kanji is legal, so han alone is not a mismatch.
    if expect == "kana" and present == ["han"]:
        return True
    return False


def check_dialogue_languages(text):
    """Catch <d>[Japanese] 한국어…</d> — the tag says one language, the text is another."""
    problems = []
    for tag, body in re.findall(r"<d>\s*\[([^\]]+)\]\s*(.*?)</d>", text or "", re.DOTALL):
        lang = tag.strip().lower()
        expect = next((s for k, s in _LANG_EXPECTS if k in lang), None)
        if not expect:
            continue
        present = [name for name, rx in _SCRIPTS.items() if rx.search(body)]
        if expect in present:
            continue
        # Japanese written entirely in kanji is legal but rare in speech.
        if expect == "kana" and "han" in present and "hangul" not in present:
            continue
        problems.append('<d>[{}] but the text is {} — "{}"'.format(
            tag.strip(), "/".join(present) or "empty", body.strip()[:40]))
    return problems


# Speech in overall_soundscape, matched whole-word so inflections cannot slip by.
_SPEECH_WORDS = tuple(re.compile(r"\b" + p + r"\b") for p in (
    r"speak\w*", r"spoke\w*", r"spoken", r"say\w*", r"said", r"talk\w*",
    r"speech", r"conversation\w*", r"conversing", r"dialogue", r"dialog",
    r"chatter\w*", r"voices?", r"vocal\w*", r"sing\w*", r"sang", r"sung",
    r"whisper\w*", r"shout\w*", r"yell\w*", r"murmur\w*", r"mutter\w*",
    r"utter\w*", r"exclaim\w*", r"reply\w*", r"replies", r"replied",
))

REF2VA_SUBSECTIONS = ("subject_definitions", "summary", "retention_analysis",
                      "detailed_description")
_VISUAL_MARKERS = ("fully_preserved", "partially_preserved", "attribute_transfer",
                   "weak_reference")
_AUDIO_MARKERS = ("fully_copy", "partially_copy", "reference", "weak_reference")
_TASK_TYPES = ("reference generation", "keyframe completion", "video editing",
               "video continuation", "audio reuse", "audio reference")


def check_ref2va_sections(imd, n_images=0):
    """Structural checks for the REF2VA six-section layout."""
    out = []
    low = imd or ""

    present = [name for name in REF2VA_SUBSECTIONS
               if re.search(r"(?m)^\s*" + name + r"\s*:", low)]
    for name in REF2VA_SUBSECTIONS:
        if name not in present:
            out.append("missing sub-section '{}:'".format(name))
    # order
    if len(present) > 1:
        pos = [re.search(r"(?m)^\s*" + n + r"\s*:", low).start() for n in present]
        if pos != sorted(pos):
            out.append("sub-sections are out of order (must be {})".format(
                " -> ".join(REF2VA_SUBSECTIONS)))

    body = {}
    for i, name in enumerate(present):
        m = re.search(r"(?m)^\s*" + name + r"\s*:", low)
        nxt = None
        for other in present[i + 1:]:
            mm = re.search(r"(?m)^\s*" + other + r"\s*:", low)
            if mm and mm.start() > m.end():
                nxt = mm.start()
                break
        body[name] = low[m.end(): nxt if nxt else len(low)].strip()

    subs = re.findall(r"<Subject\s*(\d+)\s*>", low)
    if not subs:
        out.append("no <Subject N> label anywhere — REF2VA needs at least one")

    if "subject_definitions" in body:
        if not body["subject_definitions"]:
            out.append("subject_definitions is empty")
        elif not re.search(r"<(?:Subject|Audio|Video|Picture)\s*\d+\s*>\s+is\b",
                           body["subject_definitions"]):
            out.append("subject_definitions lines should read '<Subject N> is ...'")
        # An audio bound to a speaker up top and never cited in the body has no point
        # of application — the binding is declared and then goes unused.
        if "detailed_description" in body:
            declared = set(re.findall(r"<Audio\s*(\d+)\s*>", body["subject_definitions"]))
            used = set(re.findall(r"<Audio\s*(\d+)\s*>", body["detailed_description"]))
            idle = sorted(declared - used, key=int)
            if idle:
                out.append("<Audio {}> defined but never cited in detailed_description — "
                           "cite it at the vocal event it governs"
                           .format(">, <Audio ".join(idle)))

    if "summary" in body and body["summary"]:
        if not re.match(r"\s*\[", body["summary"]):
            out.append("summary must open with a bracketed task type, e.g. "
                       "'[reference generation]'")
        else:
            tag = body["summary"].split("]")[0].strip("[ ").lower()
            if not any(t in tag for t in _TASK_TYPES):
                out.append("unknown task type '[{}]' in summary".format(tag))

    if "retention_analysis" in body:
        ra = body["retention_analysis"]
        if not ra:
            out.append("retention_analysis is empty — identity will drift between shots")
        elif not any(mk in ra for mk in set(_VISUAL_MARKERS) | set(_AUDIO_MARKERS)):
            out.append("retention_analysis has no retention marker "
                       "(fully_preserved / partially_preserved / attribute_transfer / "
                       "weak_reference)")
        elif "attribute_transfer" in ra:
            # A pose/style reference leaks identity unless the line also says what
            # must NOT come across.
            for ln in ra.splitlines():
                if "attribute_transfer" not in ln:
                    continue
                low = ln.lower()
                if not any(w in low for w in ("not ", "no ", "never", "do not", "discard",
                                              "without", "exclud")):
                    out.append("an attribute_transfer line does not say what must NOT "
                               "transfer — identity from that reference will leak")
                    break

    # Cited pictures that were never supplied — the picture-6 hallucination.
    if n_images:
        cited = sorted({int(x) for x in re.findall(r"<Picture\s*(\d+)\s*>", low)})
        over = [c for c in cited if c > n_images]
        if over:
            out.append("cites <Picture {}> but only {} image(s) were sent to the model"
                       .format(">, <Picture ".join(str(c) for c in over), n_images))
    return out


_FRAME_MODES = ("I2VA", "FL2VA", "L2VA")
_STATE_JUMP = re.compile(
    r"\b(?:but|however|instead)\b[^.]{0,90}?\b(?:now|already)\b"
    r"|\bis now\b|\bare now\b|\bhas (?:become|changed)\b"
    r"|\bnow actively\b|\binstead of\b", re.IGNORECASE)
_REF_WORDING = re.compile(r"\bpreserv\w+\s+(?:her|his|their|its)\b", re.IGNORECASE)


def check_frame_anchor(imd, mode):
    """
    In I2VA / FL2VA / L2VA a picture IS a frame of the video. A body that opens by
    describing a state change ('but she is now ...') asks for something that happened
    before 0.00 s — the model then drops the frame anchor entirely and the reference
    image stops being honoured.
    """
    if mode not in _FRAME_MODES or not imd:
        return []
    m = re.search(r"\[Shot\s*1\](.{0,700})", imd, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    head = m.group(1)
    out = []
    hit = _STATE_JUMP.search(head)
    if hit:
        out.append('[Shot 1] opens with "{}" — in {} the picture IS the frame at that '
                   "moment, so nothing on screen may differ from it at the start. Describe "
                   "the change happening ON SCREEN instead, or switch to REF2VA."
                   .format(hit.group(0).strip()[:50], mode))
    if mode == "I2VA":
        # There used to be a check here demanding the literal "<Picture 1>" inside
        # [Shot 1]. It fired on prompts that described the opening frame perfectly well
        # without citing the label, and the spec does not require the citation — the
        # instruction line above the fields already carries it. Whether the picture's
        # content actually reached the prompt is measured properly by
        # check_inventory_coverage(), against what the vision pass really saw.
        ref = _REF_WORDING.search(head)
        if ref:
            out.append('REF2VA wording in an I2VA prompt ("{}") — the picture is not a '
                       "reference to preserve attributes from, it is the opening frame"
                       .format(ref.group(0)))
    return out


def _fmt_ts(seconds):
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    s = seconds - m * 60
    return "{:02d}:{:06.3f}".format(m, s)


def strip_wrapper(text):
    """Remove reasoning blocks, code fences and chatty preamble/postamble."""
    if not text:
        return ""
    t = _THINK.sub("", text)
    t = t.strip()
    m = _FENCE.match(t)
    if m:
        t = m.group(1).strip()
    t = t.replace("```", "").strip()

    # Drop anything before the instruction line or the first real field.
    anchors = []
    for pat in (r"For the target video,", r"How the reference pictures align",
                FIELD_IMD + r"\s*:"):
        mm = re.search(pat, t)
        if mm:
            anchors.append(mm.start())
    if anchors:
        t = t[min(anchors):]

    return t.strip()


def _first_paragraph(text):
    """A field value is a single paragraph; drop anything after the first blank line."""
    if not text:
        return ""
    return re.split(r"\n\s*\n", text.strip(), 1)[0].strip()


# The model sometimes emits the whole field block twice, or repeats the
# reference-alignment instruction line inside the body. Both have to be cut before
# anything else is parsed, or the repairs below faithfully preserve the damage.

_FIELD_HEADER = re.compile(
    r"(?m)^\s*(?:" + FIELD_IMD + r"|" + FIELD_SS + r"|" + FIELD_MUS + r")\s*:")

# "For the target video, at 0.00 seconds into the target video, <Picture 1> (from
# [Shot 1]) is fully referenced."  /  "How the reference pictures align with ..."
# [^.]* cannot be used here: the sentence contains "0.00 seconds".
_INSTRUCTION_ECHO = re.compile(
    r"\s*(?:For the target video[\s\S]{0,240}?is fully referenced\.|"
    r"How the reference pictures align with the target video[\s\S]{0,400}?"
    r"mark of the target video\.|"
    # sentences copied verbatim out of the mode block in the system prompt
    r"<?Picture \d+>? is the literal (?:first|final) frame[^.]{0,90}\.|"
    r"<?Picture \d+>? is the FINAL frame and belongs to the LAST shot[^.]{0,40}\.|"
    r"Picture 1 is the opening, Picture 2 is the ending\.)",
    re.IGNORECASE)


def _cut_at_next_field(text):
    """Truncate a field's value at the next field header, if the model repeated one."""
    m = _FIELD_HEADER.search(text or "")
    return (text[:m.start()] if m else (text or "")).strip()


def strip_instruction_echo(imd):
    """Remove a reference-alignment line that leaked into the description body."""
    cleaned, n = _INSTRUCTION_ECHO.subn(" ", imd or "")
    if not n:
        return imd, 0
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    # "[Shot 1]  [Shot 2] ..." — a shot left empty by the removal is dropped.
    cleaned = re.sub(r"\[Shot\s+\d+\]\s*(?=\[Shot\s+\d+\])", "", cleaned)
    return cleaned.strip(), n




# The reference-alignment line, when the model actually produced one.
_INSTRUCTION_HEAD = re.compile(
    r"^\s*(For the target video[\s\S]{0,240}?is fully referenced\.|"
    r"How the reference pictures align with the target video[\s\S]{0,400}?"
    r"mark of the target video\.)", re.IGNORECASE)


def _split_instruction(pre):
    """'<instruction line>\n\n<body>' -> (instruction, body)."""
    m = _INSTRUCTION_HEAD.match(pre or "")
    if not m:
        return "", (pre or "").strip()
    return m.group(1).strip(), pre[m.end():].strip()



def _split_fields(text):
    """Return (instruction, imd, soundscape, music).

    The description carries NO label outside REF2VA, so it is simply whatever sits
    between the instruction line and the first audio field. The two audio fields are
    located by their labels, in whatever order the model happened to emit them — an
    earlier version assumed spec order and returned an empty description whenever a
    stray "integrated_multimodal_description:" turned up after "overall_soundscape:".
    """
    heads = []
    for name in (FIELD_IMD, FIELD_SS, FIELD_MUS):
        for m in re.finditer(r"(?m)^[ \t]*" + name + r"\s*:", text or ""):
            heads.append((m.start(), m.end(), name))
    heads.sort()

    vals = {FIELD_IMD: "", FIELD_SS: "", FIELD_MUS: ""}
    for i, (_s0, e0, name) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        chunk = (text[e0:end] or "").strip()
        if not vals[name]:                      # first non-empty occurrence wins
            vals[name] = chunk

    pre = (text[:heads[0][0]] if heads else text).strip()
    instruction, body = _split_instruction(pre)

    imd = vals[FIELD_IMD] or body
    return (instruction,
            imd.strip(),
            _first_paragraph(vals[FIELD_SS]),
            _first_paragraph(vals[FIELD_MUS]))


def _parse_shots(imd):
    """Split the description body into [(shot_number, body_text), ...]."""
    marks = [m for m in SHOT_RE.finditer(imd)
             if not re.search(r"\(\s*from\s*$", imd[max(0, m.start() - 12):m.start()],
                              re.IGNORECASE)]
    if not marks:
        return [], imd
    preamble = imd[:marks[0].start()].strip()
    shots = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(imd)
        shots.append([int(m.group(1)), imd[m.end():end].strip()])
    return shots, preamble


def _pop_timestamp(body):
    m = _TS_CLOCK.match(body)
    if m:
        mins = int(m.group(1))
        secs = int(m.group(2))
        ms = int((m.group(3) or "0").ljust(3, "0"))
        return mins * 60 + secs + ms / 1000.0, body[m.end():].lstrip()
    m = _TS_PLAIN.match(body)
    if m:
        return float(m.group(1)), body[m.end():].lstrip()
    return None, body


def _rebuild_shots(shots, duration, report):
    """Renumber shots and enforce legal, strictly increasing cut times."""
    n = len(shots)
    times = []
    bodies = []
    for i, (_num, body) in enumerate(shots):
        ts, rest = _pop_timestamp(body)
        if i == 0 and ts is not None:
            report.append("[fix] removed the timestamp from [Shot 1] (Shot 1 never carries one).")
            ts = None
        times.append(ts)
        bodies.append(rest)

    if n > 1:
        dur = float(duration)
        lo, hi = 1.0, max(1.2, dur - 0.8)
        min_gap = 0.8
        if dur / float(n) < min_gap:
            report.append(
                "[warn] {} shots in {:.2f}s leaves under {:.1f}s per shot — reduce shot_count."
                .format(n, dur, min_gap))
        need_redistribute = False
        prev = 0.0
        for i in range(1, n):
            t = times[i]
            if t is None or t < lo or t > hi or (t - prev) < min_gap:
                need_redistribute = True
                break
            prev = t
        if need_redistribute:
            for i in range(1, n):
                t = dur * i / float(n)
                times[i] = round(min(max(t, lo), hi), 3)
            # guarantee strict increase even after clamping
            for i in range(2, n):
                if times[i] <= times[i - 1]:
                    times[i] = round(times[i - 1] + 0.2, 3)
            report.append(
                "[fix] cut times were missing, out of order, too close together or outside the "
                "{:.2f}s duration — redistributed evenly.".format(dur))

    out = []
    for i in range(n):
        body = bodies[i]
        if i == 0:
            out.append("[Shot 1] " + body)
        else:
            if not any(p in body.lower() for p in CUT_PHRASES) and not re.match(
                    r"(?i)\s*(the\s+)?(camera|shot|view|frame)\b", body):
                body = "the camera cuts to " + body[0].lower() + body[1:] if body else \
                    "the camera cuts to the next moment."
                report.append("[fix] added a cut phrase to [Shot {}].".format(i + 1))
            out.append("[Shot {}] At {}, {}".format(i + 1, _fmt_ts(times[i]), body))
    return out


def _expected_instruction(mode, duration, shot_count):
    n = max(1, shot_count)
    s = "{:.2f}".format(float(duration))
    if mode == "I2VA":
        return INSTRUCTION_I2VA
    if mode == "FL2VA":
        return INSTRUCTION_FL2VA.format(n=n, s=s)
    if mode == "L2VA":
        return INSTRUCTION_L2VA.format(n=n, s=s)
    return ""


def _soft_checks(imd, ss, mus, report, dialogue_expected):
    if imd.count("<d>") != imd.count("</d>"):
        report.append("[warn] unbalanced <d> / </d> tags.")
    for blk in re.findall(r"<d>(.*?)</d>", imd, re.DOTALL):
        if not re.match(r"\s*\[[^\]]+\]", blk):
            report.append("[warn] a <d> block is missing its [Language] tag: "
                          + blk.strip()[:60])
    if "off-screen voiceover" in imd:
        for m in re.finditer(r"off-screen voiceover.*?</d>(.{0,120})", imd, re.DOTALL):
            if "lips remain" not in m.group(1):
                report.append("[warn] a voiceover <d> block is not followed by a "
                              "'lips remain completely closed' statement.")
                break
    if not dialogue_expected and "<d>" in imd:
        report.append("[warn] dialogue was set to 'none' but <d> blocks are present.")

    # Two <d> blocks joined by an overlap word. Separate lines are separate moments;
    # stacking two voices makes the model smear them into one and the timbre binding
    # is lost. Real unison is a compound ID on a single line.
    for m in re.finditer(r"</d>(.{0,120}?)<d>", imd, re.DOTALL):
        joiner = m.group(1).lower()
        overlap = [w for w in ("simultaneous", "at the same time", "meanwhile",
                               "as she speaks", "as he speaks", "as they speak",
                               "while she says", "while he says", "in unison",
                               "over her", "over his", "overlapping")
                   if w in joiner]
        if overlap:
            report.append("[warn] two dialogue lines are joined as overlapping speech "
                          "({}) — they must be sequential, or one line with a compound "
                          "(S1,S2) ID.".format(", ".join(overlap)))
            break
    for p in check_dialogue_languages(imd):
        report.append("[warn] dialogue language mismatch: " + p)

    # Non-English leakage outside <d> and quoted on-screen text.
    bad = find_non_english(imd) + find_non_english(ss) + find_non_english(mus)
    if bad:
        report.append("[warn] non-English text outside <d>/\"...\": " + ", ".join(bad[:5]))

    for name, val in ((FIELD_SS, ss), (FIELD_MUS, mus)):
        if not val:
            report.append("[fix] {} was empty — set to N/A.".format(name))

    # Speech never belongs in overall_soundscape — not the words and not the act of
    # talking. The writer keeps slipping "the sound of two women speaking" past the
    # "do not repeat dialogue" rule, because it repeats no dialogue.
    if ss and ss.strip() != "N/A":
        low = ss.lower()
        # Matched on word boundaries: "as the women speak" walked past a plain
        # substring list that only carried "speaks" and "speaking".
        speech = sorted({m.group(0) for pat in _SPEECH_WORDS
                         for m in re.finditer(pat, low)})
        speech += [t for t in ("(s1)", "(s2)", "(s3)", "(s4)") if t in low]
        if speech:
            report.append("[warn] {} mentions speech, which belongs only in the "
                          "description: {}".format(FIELD_SS, ", ".join(speech)))
    if mus and mus.strip() != "N/A":
        moody = [w for w in ("melancholy", "hopeful", "tense atmosphere", "emotional",
                             "nostalgic", "uplifting", "haunting", "evoking", "conveying")
                 if w in mus.lower()]
        if moody:
            report.append("[warn] non_diegetic_music uses abstract mood wording: "
                          + ", ".join(moody))


def normalize(raw, mode="T2VA", duration=6.0, dialogue_expected=True,
              enforce_instruction=True, ref2va_sections=False, n_images=0,
              expected_shots=0):
    """Return (clean_prompt, report_text)."""
    report = []
    text = strip_wrapper(raw)
    if not text:
        return "", "[error] the model returned nothing."

    instruction, imd, ss, mus = _split_fields(text)
    if not imd:
        return "", "[error] could not locate integrated_multimodal_description."

    imd, echoes = strip_instruction_echo(imd)
    if echoes:
        report.append("[fix] removed {} copy of the reference-alignment instruction line "
                      "from inside the description.".format(echoes)
                      if echoes == 1 else
                      "[fix] removed {} copies of the reference-alignment instruction line "
                      "from inside the description.".format(echoes))

    # REF2VA keeps its sub-sections verbatim; only the detailed_description gets shot repair.
    sub_prefix = ""
    body_for_shots = imd
    if ref2va_sections:
        m = re.search(r"(?m)^\s*detailed_description\s*:", imd)
        if m:
            sub_prefix = imd[:m.end()].rstrip() + "\n"
            body_for_shots = imd[m.end():].strip()
        else:
            report.append("[warn] REF2VA mode but no 'detailed_description:' sub-section found.")
        for problem in check_ref2va_sections(imd, n_images=n_images):
            report.append("[warn] REF2VA: " + problem)

    shots, preamble = _parse_shots(body_for_shots)
    if not shots:
        report.append("[fix] no [Shot n] marker found — wrapped the body as [Shot 1].")
        rebuilt = "[Shot 1] " + body_for_shots.strip()
        shot_count = 1
    else:
        if preamble:
            report.append("[fix] moved stray text before [Shot 1] into [Shot 1].")
            shots[0][1] = (preamble + " " + shots[0][1]).strip()
        # The node asked for a specific shot count. Extra shots are folded into the
        # last kept one — their cut marker and cut phrase go, their content stays.
        if expected_shots and len(shots) > expected_shots:
            extra = shots[expected_shots:]
            keep = shots[:expected_shots]
            tail = []
            for _num, bodytext in extra:
                bodytext = _TS_CLOCK.sub("", bodytext, count=1)
                bodytext = _TS_PLAIN.sub("", bodytext, count=1)
                bodytext = re.sub(
                    r"^\s*,?\s*the (?:camera|shot) (?:cuts|transitions|changes|switches)"
                    r"\s+to\s*", "", bodytext, count=1, flags=re.IGNORECASE)
                if bodytext.strip():
                    tail.append(bodytext.strip())
            if tail:
                keep[-1][1] = (keep[-1][1].rstrip() + " " + " ".join(tail)).strip()
            report.append(
                "[fix] {} shot(s) were written but shot_count is {} — the extra shot(s) "
                "were merged into [Shot {}] instead of cutting.".format(
                    len(shots), expected_shots, expected_shots))
            shots = keep

        rebuilt_list = _rebuild_shots(shots, duration, report)
        rebuilt = " ".join(rebuilt_list)
        shot_count = len(rebuilt_list)

    new_imd = (sub_prefix + rebuilt) if sub_prefix else rebuilt

    if not ss:
        ss = "N/A"
    if not mus:
        mus = "N/A"
    _soft_checks(new_imd, ss, mus, report, dialogue_expected)

    for problem in check_frame_anchor(new_imd, mode):
        report.append("[warn] frame anchor: " + problem)

    # Instruction line
    expected = _expected_instruction(mode, duration, shot_count) if enforce_instruction else ""
    if expected:
        if instruction.strip() != expected:
            if instruction.strip():
                report.append("[fix] rewrote the reference-alignment instruction line.")
            else:
                report.append("[fix] inserted the missing reference-alignment instruction line.")
        instruction = expected
    else:
        if instruction.strip():
            report.append("[fix] removed an instruction line ({} does not use one).".format(mode))
        instruction = ""

    parts = []
    if instruction:
        parts.append(instruction)
    # Only REF2VA labels the description. Everywhere else the label is omitted entirely:
    # a label the model never has to write is a label it can never misplace, and a
    # misplaced one used to make the whole repair pass give up.
    if ref2va_sections:
        parts.append("{}: {}".format(FIELD_IMD, new_imd))
    else:
        parts.append(new_imd)
    parts.append("{}: {}".format(FIELD_SS, ss))
    parts.append("{}: {}".format(FIELD_MUS, mus))
    clean = "\n\n".join(parts).strip() + "\n"

    if not report:
        report.append("[ok] prompt matches the specification; no repairs needed.")
    header = "mode={}  duration={:.2f}s  shots={}".format(mode, float(duration), shot_count)
    return clean, header + "\n" + "\n".join(report)


# --------------------------------------------------------- camera lock lint

# Phrases in the brief that mean "the camera does not move". Korean first, then English.
_LOCK_HINTS = (
    "카메라는 고정", "카메라 고정", "고정된 카메라", "카메라를 고정",
    "카메라 이동 없", "카메라를 움직이지", "카메라는 움직이지", "화면 고정",
    "앵글 고정", "구도 고정", "절대로 바꾸지", "절대 바꾸지", "바꾸지마", "바꾸지 마",
    "fixed camera", "camera is fixed", "locked camera", "locked-off", "locked off",
    "static camera", "camera does not move", "do not move the camera",
    "no camera movement", "never move the camera", "camera stays fixed",
)

# Words that unlock the camera. "static shot" and "shake slightly" stay legal — a
# handheld operator holding position is exactly what the brief usually means.
_MOVE_WORDS = re.compile(
    r"\b(zoom(?:s|ing)?\s+(?:in|out)|push(?:es|ing)?\s+in|pull(?:s|ing)?\s+(?:out|back)"
    r"|pan(?:s|ning)?\s+(?:left|right|across|slowly|up|down)|truck(?:s|ing)?\s+(?:left|right)"
    r"|tilt(?:s|ing)?\s+(?:up|down)|pedestal(?:s|ing)?\s+(?:up|down)"
    r"|arc(?:s|ing)?\s+(?:shot|around)|tracking\s+shot|track(?:s|ing)?\s+(?:with|alongside)"
    r"|doll(?:y|ies|ying)\s+(?:in|out|left|right)|orbit(?:s|ing)?"
    r"|crane(?:s|ing)?\s+(?:up|down)|roll(?:s|ing)?\s+(?:clock|counter))\b",
    re.IGNORECASE)

# Reveal phrasings that are a camera move wearing a disguise.
# "The shot opens on X" is standard opening-frame prose, NOT a camera move, so
# "opens" is only a violation for the framing/view, never for the shot.
_REVEAL = re.compile(
    r"\b(the (?:framing|view) (?:opens|widens|expands|shifts|changes)"
    r"|the shot (?:widens|expands|shifts|changes)"
    r"|we (?:now )?see|the camera (?:finds|discovers|reveals|moves|drifts toward|settles on)"
    r"|widen(?:s|ing)? to (?:include|reveal)|reframes?)\b", re.IGNORECASE)


def brief_locks_camera(brief):
    """True when the brief asked for a fixed camera."""
    low = (brief or "").lower()
    return any(h.lower() in low for h in _LOCK_HINTS)


def check_camera_lock(prompt, brief):
    """Warnings for camera moves in a prompt whose brief demanded a locked camera."""
    if not brief_locks_camera(brief):
        return []
    problems = []
    hits = sorted({m.group(0).lower() for m in _MOVE_WORDS.finditer(prompt or "")})
    if hits:
        problems.append(
            "the brief locks the camera, but the prompt contains camera motion: "
            + ", ".join(hits[:6])
            + ". Those words alone unlock the camera — remove them.")
    reveals = sorted({m.group(0).lower() for m in _REVEAL.finditer(prompt or "")})
    if reveals:
        problems.append(
            "reveal phrasing acts as a camera move: " + ", ".join(reveals[:4])
            + ". Describe what is already in the fixed frame instead.")
    # Count DISTINCT shot numbers inside the body only. The I2VA/FL2VA/L2VA
    # instruction line also contains "[Shot 1]", which made a one-shot prompt look
    # like two.
    body = prompt or ""
    m = re.search(r"integrated_multimodal_description\s*:", body, re.IGNORECASE)
    if m:
        body = body[m.end():]
    cuts = len(set(re.findall(r"\[Shot\s+(\d+)\]", body)))
    if cuts > 1 and not re.search(r"identical|unchanged|same fixed|does not change",
                                  body, re.IGNORECASE):
        problems.append(
            "{} shots with a locked camera, and no shot restates that the framing is "
            "unchanged. Either write it as one shot, or say at every cut that the camera "
            "position and framing are identical.".format(cuts))
    return problems


# ------------------------------------------------- inventory coverage lint

# Headings from the vision pass whose content MUST survive into the prompt. The
# action always survives — the model is writing about it. What silently vanishes is
# the space the action happens in and the structure of the shot.
# What the writer is held to. CLOTHING and PHYSIQUE are the two that vanish most
# often and were previously unchecked, so an inventory could describe a body in
# detail and the prompt could still say "slender" with nothing flagged.
_COVER_HEADINGS = ("SETTING", "LAYERS", "PEOPLE", "CLOTHING", "PHYSIQUE",
                   "EXPRESSION", "TEXT AND UI")

_STOP = set("""a an the and or of in on at to from with without into onto over under this
that these those is are was were be been being it its his her their there here what which
who whom whose not no none nothing visible plain single scene image picture frame shot
person people one two three left right top bottom front back side middle centre center
around across through above below near far very quite some any each both all more most
other another same different such only just also then than as by for but if so
colour color colours colors light dark bright dim soft hard small large big long short
seen shown showing appears appear apparent partially fully entirely mostly slightly""".split())


def _content_words(text):
    out = set()
    for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text or ""):
        w = w.lower()
        if w not in _STOP:
            out.add(w)
    # numerals and quoted strings are content too — "22", "REC", "OPEN"
    for w in re.findall(r"\d{1,4}", text or ""):
        out.add(w)
    return out


def _inventory_sections(text):
    """Split one vision-pass inventory into {HEADING: value}."""
    out, cur, buf = {}, None, []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*([A-Z][A-Z /]{2,20}):\s*(.*)$", line)
        if m:
            if cur:
                out[cur] = " ".join(buf).strip()
            cur, buf = m.group(1).strip(), [m.group(2)]
        elif cur:
            buf.append(line.strip())
    if cur:
        out[cur] = " ".join(buf).strip()
    return out


def check_inventory_coverage(prompt, inventories):
    """Name the things the vision pass saw that never reached the prompt.

    Deliberately reports the MISSING WORDS rather than matching against a list of
    things worth keeping. A fixed list of 'important' features would bias every
    future image toward the features of the images that produced the list.
    """
    problems = []
    body = _content_words(prompt)
    for idx, inv in enumerate(inventories or [], start=1):
        secs = _inventory_sections(inv)
        for head in _COVER_HEADINGS:
            val = secs.get(head, "")
            if not val or re.match(r"^\s*(not visible|n/?a|none)\b", val, re.IGNORECASE):
                continue
            want = _content_words(val)
            if len(want) < 3:
                continue
            missing = sorted(want - body)
            if len(missing) >= 3:
                problems.append("<Picture {}> {} — missing: {}{}".format(
                    idx, head, ", ".join(missing[:8]),
                    " (+{} more)".format(len(missing) - 8) if len(missing) > 8 else ""))
    return problems


# ------------------------------------------------- camera vocabulary lint

# The H3 motion types. A camera clause built out of anything else renders as nothing.
_MOTION_TYPES = re.compile(
    r"\b(zoom(?:s|ing)?\s+(?:in|out)|push(?:es|ing)?\s+in|pull(?:s|ing)?\s+(?:out|back)"
    r"|pan(?:s|ning)?\s+\w+|truck(?:s|ing)?\s+\w+|tilt(?:s|ing)?\s+\w+"
    r"|pedestal(?:s|ing)?\s+\w+|arc\s+shot|tracking\s+shot|static\s+shot"
    r"|shake(?:s|ing)?\s+(?:slightly|strongly)|shakes?\s+\w*\s*slightly"
    r"|roll(?:s|ing)?\s+(?:clock|counter)|\bPOV\b)", re.IGNORECASE)

# Wordings that sound like camera direction but name no motion the model knows.
_FAKE_MOTION = re.compile(
    r"(handheld[- ]style|as if (?:held|carried|shot|filmed)|the frame breathes"
    r"|natural hand(?:held)? (?:movement|motion|drift)|documentary[- ]style"
    r"|floating,? dreamlike|organic camera|subtle camera life|micro[- ]drift"
    r"|slight(?:ly)? (?:drifts?|sway)\b)", re.IGNORECASE)


def check_camera_vocabulary(prompt):
    """Warn when the camera is described by analogy instead of by a listed motion."""
    text = prompt or ""
    problems = []
    fakes = sorted({m.group(0).lower() for m in _FAKE_MOTION.finditer(text)})
    if fakes:
        problems.append(
            "the camera is described by analogy: " + ", ".join(fakes[:4])
            + ". That names no motion the model can render, so the camera usually ends "
              "up completely still. Use a listed motion type with amplitude and speed "
              "instead — for a held camera that is \"shakes slightly with small "
              "amplitude at slow speed\".")
    if fakes and not _MOTION_TYPES.search(text):
        problems.append(
            "no listed motion type appears anywhere in the prompt (Static Shot, Shake "
            "Slightly, Push In, Pan Left, ...). The camera has no instruction it "
            "recognises.")
    return problems


# ------------------------------------- camera verbs used on people and objects

# Only the unambiguous camera forms. "tilts her head" is ordinary English and is left
# alone; "tilts down" is the camera instruction.
_RESERVED_VERB = re.compile(
    r"\b(shakes?\s+(?:slightly|strongly)|pans?\s+(?:left|right)"
    r"|zooms?\s+(?:in|out)|pushes?\s+in\b|pulls?\s+(?:out|back)\b"
    r"|trucks?\s+(?:left|right)|pedestals?\s+(?:up|down)"
    r"|tilts?\s+(?:up|down)\b|rolls?\s+(?:clockwise|counterclockwise)"
    r"|arcs?\s+around|tracking\s+shot|arc\s+shot)", re.IGNORECASE)

_IS_CAMERA = re.compile(r"\b(camera|shot|view|frame|lens|viewpoint)\b", re.IGNORECASE)


def check_reserved_camera_verbs(prompt):
    """Camera vocabulary attached to a subject moves the whole frame."""
    text = prompt or ""
    hits = []
    for m in _RESERVED_VERB.finditer(text):
        # Look back over the clause for the thing doing it.
        start = text.rfind(".", 0, m.start()) + 1
        start = max(start, text.rfind(";", 0, m.start()) + 1,
                    text.rfind(",", 0, m.start()) + 1)
        subject = text[start:m.start()]
        if _IS_CAMERA.search(subject):
            continue
        hits.append((subject.strip()[-40:], m.group(0)))
    if not hits:
        return []
    return ["camera vocabulary used on something that is not the camera: "
            + "; ".join('"{} {}"'.format(sub, verb) for sub, verb in hits[:4])
            + ". The model reads these as camera instructions and moves the entire "
              "frame. Use an ordinary verb for people and objects (moves, shifts, "
              "sways, rocks, leans, trembles)."]


# ------------------------------------------------- structural contradictions

_MOVE_AND_CUT = re.compile(
    r"[^.]*\b(?:camera|shot)\b[^.]*?\b(?:pulls?|pushes?|tilts?|pans?|trucks?|arcs?|"
    r"zooms?|dollies|cranes?)\b[^.]*?\b(?:the (?:shot|camera) (?:cuts|transitions|"
    r"changes|switches) to)\b[^.]*\.", re.IGNORECASE)

# "the shot cuts to" sitting inside a shot body instead of opening [Shot N].
_INLINE_CUT = re.compile(
    r"(?<!\])\s(?:the (?:shot|camera) (?:cuts|transitions|changes|switches) to)\b",
    re.IGNORECASE)

# Content words describing something the writer could not have seen.
#
# NAMING a role is not describing content. "<Audio 1> is the voice-timbre reference for
# <Subject 1>" is the required form — it binds the file to a speaker without claiming to
# know what it sounds like. Only a CLAIM about the contents counts: "a soft breathy
# voice", "an upbeat melody". So role phrasing is excluded before the check runs.
_ROLE_PHRASE = re.compile(
    r"\b(?:voice-timbre|voice timbre|timbre)\s+reference\b"
    r"|\breference\s+for\s+<Subject"
    r"|\b(?:its|their)\s+(?:vocal\s+)?timbre\s+guides\b"
    r"|\bin\s+the\s+voice\s+timbre\s+referenced\s+from\b"
    r"|\bwith\s+(?:her|his|their)\s+voice\s+timbre\b", re.IGNORECASE)

_UNSEEN_DESC = re.compile(
    r"<(?:Video|Audio)\s*\d+>[^.]{0,160}?\b("
    r"mov\w+|sway\w*|rhythm\w*|dexterity|gestur\w*|walk\w*|danc\w*|"
    r"voice is|sounds? like|tone is|pitch|timbre|melody|breath\w*)\b", re.IGNORECASE)


def check_structure(imd):
    """Contradictions the spec forbids but the model produces anyway."""
    out = []
    body = imd or ""

    for m in _MOVE_AND_CUT.finditer(body):
        out.append('a camera move and a cut in one sentence — "{}"'.format(
            m.group(0).strip()[:110]))

    shots = SHOT_RE.findall(body)
    inline = list(_INLINE_CUT.finditer(body))
    if inline and len(shots) <= len(inline):
        out.append(
            "{} cut phrase(s) written inside a shot body instead of opening a new "
            "[Shot N] — the model was told to write fewer shots than the brief needs. "
            "Raise shot_count.".format(len(inline)))

    # Blank out the legitimate role phrasing first, keeping the string length so the
    # remaining offsets still line up with the text the user reads.
    scrub = _ROLE_PHRASE.sub(lambda m: " " * len(m.group(0)), body)
    for m in _UNSEEN_DESC.finditer(scrub):
        out.append('describes the contents of an unseen reference — "{}"'.format(
            body[m.start():m.end()].strip()[:110]))
    return out


# ------------------------------------- can the lines fit in the running time?

# 두 번 겪었습니다. 일본어 대사 62자를 10초에 넣었더니 초당 6.2자로 발음이 뭉개졌고,
# 음성인식으로 되받아 보니 先生(센세이)이 センス(센스)로, お願いします가
# オネガタカラのシマス로 나왔습니다. 가이드라인에는 "2.5-3 spoken words per second"
# 라는 규칙이 있는데, 그건 영어 단어 기준이라 일본어·한국어에는 맞지 않습니다 —
# 같은 뜻을 옮기면 음절 수가 두 배가 됩니다. 그래서 문자 체계별로 따로 셉니다.
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
_SPEAKABLE = re.compile(r"[^\w\s]", re.UNICODE)

# 초당 편하게 발음되는 양. 넘으면 뭉개지기 시작합니다.
_RATE_CJK = 4.5          # 글자(모라)
_RATE_LATIN = 2.8        # 단어


def _spoken_cost(body):
    """대사 한 줄 -> (읽는 데 걸리는 초, 사람이 읽을 설명)."""
    text = _SPEAKABLE.sub("", body or "").strip()
    if not text:
        return 0.0, ""
    if _CJK.search(text):
        n = len(re.sub(r"\s+", "", text))
        return n / _RATE_CJK, "{}자".format(n)
    n = len(text.split())
    return n / _RATE_LATIN, "{}단어".format(n)


def check_dialogue_rate(prompt, duration):
    """대사가 영상 길이에 들어가는가.

    들어가지 않으면 모델은 말을 빨리 하는 게 아니라 음절을 삼킵니다. 결과물을 보기
    전에는 알 수 없고, 보고 나면 이미 늦습니다.
    """
    secs = float(duration or 0)
    if secs <= 0:
        return []
    lines = re.findall(r"<d>\s*(?:\[[^\]]*\]\s*)?(.*?)</d>", prompt or "", re.DOTALL)
    if not lines:
        return []
    total, parts = 0.0, []
    for body in lines:
        cost, label = _spoken_cost(body)
        total += cost
        if label:
            parts.append(label)
    if total <= 0:
        return []
    # 줄 사이 쉼과 앞뒤 여유. 한 줄이면 쉼이 없습니다.
    total += 0.5 * max(0, len(lines) - 1) + 1.5
    if total <= secs:
        return []
    need = int(total + 0.999)
    fit = secs / total
    return ["대사가 영상 길이에 들어가지 않습니다 — {} ({}줄) 을 편하게 읽으면 약 "
            "{:.0f}초가 필요한데 영상은 {:.0f}초입니다. 모델은 빨리 읽는 게 아니라 "
            "음절을 삼켜서, 발음이 뭉개지고 자막으로 받아적으면 다른 말이 됩니다. "
            "영상을 {}초 이상으로 늘리거나, 대사를 지금의 {:.0f}% 로 줄이세요."
            .format(" + ".join(parts), len(lines), total, secs, need, fit * 100)]


# ------------------------------------- is the order of events actually pinned?

# 도시 -> 터널 -> 사막 순으로 쓰고 싶었는데 도시 -> 사막 -> 터널로 나왔습니다.
# 프롬프트를 보니 "before", "once the line ends" 로 순서를 잡고 있었는데, 그런
# 상대 표현은 모델이 순서를 바꿔도 어긴 것이 아닙니다. 시각은 못 바꿉니다.
_REL_ORDER = re.compile(
    r"\b(before|after(?:wards)?|then|next|later|subsequently|meanwhile"
    # "once the line ends", "as soon as she finishes speaking" — 사이에 몇 단어가
    # 끼든 잡아야 합니다. 예전에는 한 단어만 허용해서 정작 겪은 문장을 놓쳤습니다.
    r"|once\s+(?:\w+\s+){0,4}?(?:ends?|finishes|is\s+over|has\s+spoken)"
    r"|as\s+soon\s+as|following\s+that|at\s+the\s+end\s+of\s+(?:the\s+)?line)\b",
    re.IGNORECASE)
_EVENT_TS = re.compile(r"\bAt\s+\d\d:\d\d\.\d{3}", re.IGNORECASE)


def check_event_order(imd):
    """한 샷 안에서 사건 순서를 상대 표현으로만 잡고 있는가."""
    body = imd or ""
    out = []
    cuts = [m.start() for m in SHOT_RE.finditer(body)] + [len(body)]
    for i in range(len(cuts) - 1):
        chunk = body[cuts[i]:cuts[i + 1]]
        words = sorted({m.group(0).lower() for m in _REL_ORDER.finditer(chunk)})
        # 샷을 여는 "At MM:SS.mmm" 은 컷 시각이라 사건 순서를 정하지 않습니다.
        stamps = len(_EVENT_TS.findall(chunk)) - (1 if i > 0 else 0)
        if len(words) >= 2 and stamps <= 0:
            out.append(
                '샷 {} 은 사건 순서를 "{}" 같은 상대 표현으로만 잡고 있습니다. '
                '모델이 순서를 바꿔도 지시를 어긴 것이 아니라서 실제로 뒤바뀝니다. '
                '순서가 중요하면 "At 00:05.000," 처럼 시각을 박으세요.'
                .format(i + 1, '", "'.join(words[:3])))
    return out
