# -*- coding: utf-8 -*-
"""Physical-act vocabulary for the shot cards.

A bare label like "doggystyle" is not enough for MiniMax H3: it applies the label to
both people, and it picks a thrust direction from the camera rather than from the
bodies. So every entry here spells out, in this order:

  1. the name, so the model's own prior is still invoked;
  2. each person's posture SEPARATELY, so the two are not made identical;
  3. who moves, by name;
  4. the direction, anchored to the bodies and to gravity (back and forth along their
     axis / vertically / downward) and never to the frame. "horizontally" reads as
     screen left-right, so it is not used — doggy style may or may not be a side view.

Rules learned the hard way and applied throughout:
  - No pronouns. Repeat the label. "their hips" is the wording that makes the model
    attribute the motion to the wrong person.
  - No statements of absence ("no penetration"). They cost tokens and say nothing.
  - "thrusting" outperforms cruder verbs in practice, so it is the standard verb.
  - Nothing here tries to correct MiniMax by instructing the LLM — anything meant for
    the video model has to survive INTO the final prompt, so it lives in these strings.

Entry: (key, 한글 라벨, 한글 툴팁, 영어 지시문, 칸1 이름, 칸2 이름, 기본 무버)
  기본 무버: "a" | "b" | "both"    칸2 이름이 "" 이면 1인 행위입니다.
  지시문의 {A} / {B} 는 참여자 라벨로 치환됩니다.
"""

SOLO = ""

ACTS = [
    ("", "지정 안 함", "이 줄의 행위를 지정하지 않습니다.", "", "", "", ""),

    # ---------------------------------------------------------------- 삽입 · 정면
    ("missionary", "정상위 (다리 펴고)",
     "받는 쪽이 다리를 편 채 눕고, 하는 쪽이 그 위에 몸을 겹쳐 앞뒤로.",
     # "downward" 는 수직 피스톤으로 읽혀서 밀어 누르는 동작이 나왔습니다. 정상위의
     # 골반은 몸의 길이 방향으로 앞뒤로 움직입니다. 같은 파일의 lotus·wall·doggy 가
     # 이미 "back and forth" 를 쓰고 있어 정상위만 혼자 수직이었습니다. 축을 몸 기준
     # 으로 명시합니다 — 파일 머리의 "방향은 몸의 축 기준" 원칙 그대로입니다.
     "Missionary. {A} lies face up with legs apart. {B} lies over {A} between {A}'s "
     "spread legs, chest to chest and hips to hips, and thrusts into {A}, {B}'s hips "
     "driving forward and back along the line of {A}'s body. {A} stays lying beneath {B}.",
     "받는 쪽", "하는 쪽", "b"),
    # 위 항목은 다리를 편 채 몸이 완전히 포개진 형태로 그려집니다. 무릎 정보가 없어
    # 두 몸이 평면으로 겹치고, 그러면 앞뒤로 움직일 공간이 없어 방향 문구가 살아도
    # 수직 압박으로 나옵니다. 무릎을 세워 골반 사이에 공간을 주는 쪽을 따로 둡니다.
    #
    # "chest to chest" 는 빼면 안 됩니다. 한 번 빼고 체중 지지(팔뚝)로 대체했더니
    # 하는 쪽이 팔뚝과 골반으로만 남아 화면에서 사라지고 받는 쪽만 나왔습니다.
    # 두 몸이 닿는다는 진술이자 하는 쪽의 상체가 존재한다는 유일한 보증입니다.
    # 받는 쪽의 자세 설명이 길어져 하는 쪽의 첫 등장이 뒤로 밀리는 것도 같은 결과를
    # 냅니다 — 구도가 "누워 있는 한 사람" 으로 먼저 잡힙니다. 첫 문장은 짧게.
    # 다리 기하를 절로 나눠 지정하면 안 됩니다. 공중에 뜬다 / 하는 쪽 양옆이다 /
    # 무릎이 허리 높이다 / 허벅지가 옆구리에 닿는다 / 종아리가 뒤로 처진다 — 이렇게
    # 다섯 개를 걸었더니 모델이 그중 하나만 집었습니다. 같은 파일 lotus 가 쓰는
    # "legs around {B}'s waist" 가 그 다섯 개를 한 덩어리로 이미 담고 있습니다.
    # 아는 이름을 부르는 쪽이 기하를 받아쓰는 쪽보다 항상 낫습니다.
    #
    # "chest to chest" 는 상체만 보장합니다. 이것만 두면 골반 사이가 벌어진 채로
    # 그려집니다. 접촉면마다 따로 말해야 하므로 같은 구문을 이어 붙입니다.
    ("missionary_knees", "정상위 (다리 올림)",
     "받는 쪽이 다리를 들어 하는 쪽의 허리에 감고, 그 사이에서 앞뒤로.",
     "Missionary, legs raised. {A} lies face up beneath {B} with {A}'s legs raised and "
     "wrapped around {B}'s waist. {B} lies over {A} between {A}'s thighs, chest to "
     "chest and hips to hips, and thrusts into {A}, {B}'s hips driving forward and "
     "back along the line of {A}'s body. {A} stays lying beneath {B}.",
     "받는 쪽", "하는 쪽", "b"),
    ("mating_press", "굴곡위",
     "받는 쪽의 다리를 접어 올린 채 위에서 가파르게.",
     "Mating press. {A} lies face up. {B} kneels over {A} from above, leaning down "
     "with {B}'s weight, and presses {A}'s legs back toward {A}'s own shoulders. "
     "{B} thrusts steeply downward into {A}. {A} stays pinned under {B} and does not thrust; {A}'s hands and face are "
     "free.",
     "받는 쪽", "하는 쪽", "b"),
    ("side_front", "정면 측위",
     "둘 다 옆으로 누워 마주 본 채로.",
     "Side by side, facing. {A} and {B} both lie on their sides facing each other, "
     "legs interlocked. {B} thrusts into {A} with short strokes, back and forth. {A} stays "
     "on {A}'s side.",
     "받는 쪽", "하는 쪽", "b"),
    ("lotus", "대면 좌위",
     "앉아서 마주 보고 끌어안은 채로.",
     "Lotus, seated face to face. {B} sits with legs crossed. {A} sits in {B}'s lap "
     "facing {B}, legs around {B}'s waist, chests together. {A} thrusts vertically with "
     "short rises and drops onto {B}. {B} stays seated and does not thrust, holding {A}'s hips.",
     "위에 앉는 쪽", "아래 앉는 쪽", "a"),
    ("standing_front", "대면 입위",
     "서서 마주 본 채로.",
     "Standing, facing. {A} and {B} stand chest to chest and hips to hips, {A} with one "
     "leg raised and held by {B}. {B} thrusts upward into {A}. {A} stays standing and "
     "holds onto {B}.",
     "받는 쪽", "하는 쪽", "b"),
    ("carry", "배면 안고 서서",
     "하는 쪽이 받는 쪽을 뒤에서 안아 든 채로. 받는 쪽은 등을 맡기고 매달려 있다.",
     "Standing carry from behind. {B} stands upright and holds {A} up from behind by "
     "the backs of {A}'s thighs, {A}'s legs held apart and hanging over {B}'s forearms. "
     "{A} faces away from {B}, {A}'s back against {B}'s chest, and {A} does not hold "
     "onto {B}. {B} thrusts upward from below, lifting and dropping {A} onto {B}'s "
     "cock. {A} hangs in {B}'s arms and does not thrust.",
     "안기는 쪽", "안는 쪽", "b"),
    ("carry_front", "대면 안고 서서",
     "하는 쪽이 받는 쪽을 마주 본 채로 안아 든다. 받는 쪽이 다리와 팔로 매달린다.",
     # "{A}'s back is turned away from {B}" 를 지웠습니다. 마주 보고 안겨 있으면 등이
     # 반대쪽인 건 당연해서 정보가 없는데, 아래 '방향은 렌더링 지시가 아니다' 문단이
     # 경고하는 바로 그 형태라 뒷모습으로 그려질 위험만 있었습니다.
     "Standing carry, face to face. {B} stands upright and holds {A} up by the backs "
     "of {A}'s thighs. {A} faces {B}, chest to chest and hips to hips, {A}'s legs "
     "wrapped around {B}'s waist and {A}'s arms around {B}'s neck. {B} thrusts upward, "
     "lifting and dropping {A} onto {B}'s cock. {A} holds on and does not thrust.",
     "안기는 쪽", "안는 쪽", "b"),
    ("edge", "가장자리 걸치기",
     "받는 쪽이 침대·테이블 가장자리에 눕고 하는 쪽은 서서.",
     # 81단어에 하는 쪽이 30번째 단어에서야 나왔습니다 — 받는 쪽 혼자 그려지기 딱
     # 좋은 조건입니다. "cock is inside" 는 "thrusts into" 와 중복이고, "facing up
     # toward {B}" 와 "legs hanging off" 는 "hips at the edge" 에 이미 들어 있습니다.
     "On the edge of the bed. {A} lies face up with {A}'s hips at the edge and {A}'s "
     "legs apart. {B} stands on the floor between {A}'s legs, hips to hips, holding "
     "{A}'s thighs apart, and thrusts into {A}, {B}'s hips driving forward and back "
     "along the line of {A}'s body. {A} stays lying back; {A}'s hands and face are free.",
     "받는 쪽", "하는 쪽", "b"),

    # ---------------------------------------------------------------- 삽입 · 후면
    ("doggy", "후배위",
     "받는 쪽이 네 발로 엎드리고 하는 쪽이 뒤에서 무릎 꿇는다.",
     "Doggy style, from behind. {A} is on hands and knees, back arched, facing away "
     "from {B}. {B} kneels upright behind {A} and thrusts into {A} from behind, {B}'s "
     "hips driving back and forth along the line of {A}'s spine. {A} stays braced and does not thrust; {A}'s head and hands are free.",
     "받는 쪽", "하는 쪽", "b"),
    ("prone", "엎드린 자세",
     "받는 쪽이 배를 깔고 완전히 엎드린 채로.",
     # "downward and forward" 로 두 축을 동시에 걸면 모델은 하나만 집고, 집는 쪽은
     # 늘 수직입니다. 정상위가 겪은 문제와 같은 종류라 doggy 의 표현으로 맞춥니다.
     "Prone. {A} lies flat face down with legs together. {B} lies over {A}'s back, "
     "{B}'s hips against {A}'s buttocks, and thrusts into {A} from behind, {B}'s hips "
     "driving back and forth along the line of {A}'s spine. {A} stays flat underneath {B}.",
     "받는 쪽", "하는 쪽", "b"),
    ("spooning", "후면 측위",
     "둘 다 같은 방향으로 옆으로 누운 채로.",
     "Spooning. {A} and {B} both lie on their sides facing the same way, {B} behind "
     "{A}, {B}'s chest against {A}'s back and {B}'s hips against {A}'s buttocks. "
     "{B} thrusts into {A} from behind back and forth with shallow strokes. "
     "{A} stays curled on {A}'s side.",
     "앞쪽 (받는 쪽)", "뒤쪽 (하는 쪽)", "b"),
    ("seated_behind", "후면 좌위",
     "받는 쪽이 하는 쪽의 무릎 위에 등을 보이고 앉는다.",
     "Seated from behind. {B} sits upright. {A} sits down in {B}'s lap facing away "
     "from {B}, back against {B}'s chest. {A} thrusts vertically, rising and dropping "
     "onto {B}. {B} stays seated and holds {A}'s hips.",
     "앞쪽 (앉는 쪽)", "뒤쪽 (받쳐주는 쪽)", "a"),
    ("standing_behind", "후면 입위",
     "받는 쪽이 앞으로 숙이고 하는 쪽이 뒤에 서서.",
     "Standing from behind. {A} stands bent forward at the waist, hands braced on a "
     "surface, facing away from {B}. {B} stands behind {A} and thrusts into {A} "
     "back and forth. {A} stays braced and does not thrust; {A}'s head and hands are free.",
     "받는 쪽", "하는 쪽", "b"),
    ("wall", "벽 짚고",
     "받는 쪽이 벽을 짚고 서고 하는 쪽이 뒤에서.",
     "Against the wall. {A} stands facing the wall with both palms flat on it, hips "
     "pushed back. {B} stands behind {A}, pressed against {A}'s back, and thrusts into "
     "{A} forward and back, pressing {A} toward the wall. {A} stays braced against the wall.",
     "받는 쪽", "하는 쪽", "b"),

    # ------------------------------------------------------------ 삽입 · 받는 쪽 주도
    ("cowgirl", "기승위",
     "위에 탄 쪽이 마주 보고 주도한다.",
     # 2026-09-02: 배면과 구분하려고 얼굴 위치·무릎 방향·부정문을 쌓았다가 원본으로
     # 되돌렸습니다. 설명이 길어지면서 정작 "Cowgirl" 이라는 이름이 결과물의
     # detailed_description 에서 밀려 사라졌고 — 이름은 영상 모델이 그 자세에 대해
     # 이미 아는 것을 불러오는 열쇠입니다 — 늘린 문장들이 효과가 있었다는 증거도
     # 없었습니다. 검증된 것은 정지 범위를 골반으로 좁힌 것 하나뿐이라 그것만 남깁니다.
     "Cowgirl, facing. {B} lies face up. {A} straddles {B}'s hips upright, facing {B}. "
     "{A} thrusts vertically, raising and dropping onto {B}'s cock. "
     "{B} stays lying down and does not thrust; {B}'s hands and face are free.",
     "위 (타는 쪽)", "아래 (누운 쪽)", "a"),
    ("reverse_cowgirl", "배면 기승위",
     "위에 탄 쪽이 등을 보인 채 주도한다.",
     # 2026-09-02: 여기에 얼굴 위치·반 바퀴 회전·"틀린 자세" 부정문을 쌓았다가 원본으로
     # 되돌렸습니다. 730자까지 불어나면서 "Reverse cowgirl" 이라는 이름이 결과물 본문에서
     # 사라졌고(실측), 부정문은 확산 모델에서 오히려 그 개념을 불러올 위험이 있습니다.
     # 남은 실패(덜 도는 문제)의 진짜 원인은 문장 부족이 아니라, 누운 사람의 머리-발
     # 축이 어디를 향하는지 정하는 축이 없다는 것으로 보입니다.
     # "back to {B}" 를 뺐습니다. 그 단어가 이 문장에서 방향을 말하는 거의 유일한
     # 단어였고, back 은 몸의 관계("등이 그를 향한다")와 화면의 구도("뒷모습") 두 가지로
     # 읽힙니다. 카메라 지시가 약할 때 H3 는 구도 쪽으로 읽어서, 방향을 정면으로 줘도
     # 뒷모습이 나왔습니다. feet 는 같은 신체 부위지만 "발 시점" 같은 지배적 구도가
     # 없어서 카메라를 끌지 않습니다.
     "Reverse cowgirl. {B} lies face up. {A} straddles {B}'s hips upright, turned the "
     "opposite way round from {B}, facing {B}'s feet. {A} thrusts "
     "vertically, raising and dropping onto {B}'s cock. {B} stays lying down and does not "
     "thrust; {B}'s hands and face are free.",
     "위 (타는 쪽)", "아래 (누운 쪽)", "a"),

    # ---------------------------------------------------------------------- 구강
    ("blowjob", "펠라치오",
     "받는 쪽의 성기를 입으로.",
     "Blowjob. {B} stands upright with legs apart. {A} kneels on the floor in front "
     "of {B}, facing {B}, {A}'s head level with {B}'s hips. {A} takes {B}'s cock into "
     "{A}'s mouth and sucks it, {A}'s head bobbing vertically along its length, one of "
     "{A}'s hands gripping the base. {B} stands still and does not thrust.",
     "하는 쪽", "받는 쪽", "a"),
    ("cunnilingus", "쿤닐링구스",
     "받는 쪽의 성기를 혀로.",
     "Cunnilingus. {B} lies back with legs apart. {A} lies between {B}'s thighs and "
     "licks {B}'s pussy, {A}'s tongue moving in slow strokes. {B} stays lying back.",
     "하는 쪽", "받는 쪽", "a"),
    ("rimming", "애널링구스",
     "받는 쪽의 뒤를 혀로.",
     "Rimming. {B} is on hands and knees facing away. {A} kneels behind {B} and licks "
     "{B}'s asshole in slow strokes. {B} stays braced; {B}'s head and hands are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("sixtynine", "상호 구강 (69)",
     "서로 반대로 누워 동시에.",
     "69. {B} lies on {B}'s back. {A} lies on top of {B} inverted, head to hips, so "
     "each mouth is at the other's crotch. {A} and {B} go down on each other at the "
     "same time — neither is only receiving.",
     "대상 1", "대상 2", "both"),

    # ----------------------------------------------------------------------- 손
    ("handjob", "수기 (남성 대상)",
     "손으로 성기를 자극한다.",
     "Handjob. {B} stands upright. {A} kneels or sits beside {B}, facing {B}, {A}'s "
     "upper body turned toward {B}'s hips. {A} grips {B}'s cock in one hand and "
     "strokes it vertically, up and down, at a steady rhythm. {B} stands still and does not "
     "thrust; {B}'s hands and face are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("fingering", "핑거링",
     "손가락으로 삽입 자극.",
     "Fingering. {B} lies back with {B}'s legs apart and knees raised. {A} kneels or "
     "sits beside {B}, {A}'s hand between {B}'s spread legs. {A} works two fingers "
     "into {B}'s pussy and thrusts them in and out, {A}'s thumb on {B}'s clit. "
     "{B} stays lying back and open; {B}'s hands and face are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("rubbing", "수기 (여성 대상)",
     "손으로 문질러 자극한다.",
     "{B} lies back with {B}'s legs apart. {A} kneels or sits beside {B}, {A}'s hand "
     "between {B}'s spread legs. {A} rubs {B}'s pussy and clit with {A}'s fingers in "
     "small fast circles. {B} stays lying back; {B}'s hands and face are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("mutual_hands", "상호 수기",
     "서로 동시에 손으로.",
     "{A} and {B} sit or lie side by side facing each other, close enough to reach. "
     "Each has a hand between the other's legs — {A}'s hand on {B}'s crotch and {B}'s "
     "hand on {A}'s crotch — and both stroke steadily at the same time. Neither is "
     "only receiving.",
     "대상 1", "대상 2", "both"),

    # ------------------------------------------------------------------ 삽입 외 마찰
    ("titfuck", "파이즈리",
     "가슴 사이에 끼워 상하로.",
     "Titfuck. {B} stands upright. {A} kneels in front of {B}, facing {B}. {A} presses "
     "{A}'s breasts together around {B}'s cock with both hands and strokes {B}'s cock "
     "vertically, moving {A}'s chest up and down. {B} stands still and does not thrust; {B}'s hands are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("thighjob", "허벅지",
     "허벅지 사이에 끼워 앞뒤로.",
     "Thigh job. {A} stands or lies with {B} close behind {A}. {A} presses {A}'s "
     "thighs tightly together with {B}'s cock between them from behind. {B} thrusts "
     "back and forth between {A}'s thighs. {A} keeps the thighs closed and does not thrust; {A}'s "
     "hands and face are free.",
     "제공하는 쪽", "움직이는 쪽", "b"),
    ("footjob", "풋잡",
     "발로 자극한다.",
     "Footjob. {B} lies back on {B}'s elbows with legs apart. {A} sits facing {B}, "
     "leaning back on {A}'s hands, {A}'s legs extended toward {B}'s hips. {A} holds "
     "{B}'s cock between both of {A}'s feet and strokes it vertically, up and down. "
     "{B} stays lying back; {B}'s hands and face are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("intercrural", "소분",
     "다리 사이·아래에 끼운 채 앞뒤로.",
     "Intercrural. {A} lies on {A}'s side or stands bent forward, with {B} close "
     "behind {A}. {B}'s cock is between {A}'s legs from behind, sliding under {A} "
     "rather than inside. {B} thrusts back and forth. {A} stays braced.",
     "제공하는 쪽", "움직이는 쪽", "b"),
    ("frottage", "상호 마찰",
     "서로 몸을 밀착해 문지른다.",
     "{A} and {B} stand pressed together face to face, {A}'s chest against {B}'s "
     "chest and {A}'s crotch against {B}'s crotch. Both grind their hips against each "
     "other, moving in opposite time. Both are active.",
     "대상 1", "대상 2", "both"),
    ("tribadism", "여성 간 마찰",
     "서로의 성기를 맞대고 문지른다.",
     "Tribadism. {A} and {B} lie facing each other and press their pussies together, "
     "legs scissored, and grind against each other back and forth. Both are active.",
     "대상 1", "대상 2", "both"),

    # -------------------------------------------------------------------- 전희
    ("kiss", "키스 (상호)",
     "입을 맞춘다. 둘 다 능동.",
     "{A} and {B} are kissing, mouth to mouth, both actively — neither is only "
     "receiving.",
     "대상 1", "대상 2", "both"),
    ("neck_kiss", "목·쇄골 키스",
     "한쪽이 상대의 목과 쇄골에.",
     "{A} kisses along {B}'s neck and collarbone, slowly. {B} tilts {B}'s head back; "
     "{B}'s hands are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("breast_play", "가슴 애무",
     "가슴을 손과 입으로.",
     "{A} works on {B}'s breasts with {A}'s mouth and hands, sucking and squeezing. "
     "{B} holds still under {A}'s mouth and hands; {B}'s own hands and face are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("caress", "전신 애무",
     "몸 전체를 손으로 훑는다.",
     "{A} runs {A}'s hands over {B}'s body, shoulders to hips, slowly and continuously. "
     "{B} stays where {B} is; {B}'s hands and face are free.",
     "하는 쪽", "받는 쪽", "a"),
    ("embrace", "밀착 포옹",
     "몸을 붙여 끌어안는다.",
     "{A} and {B} hold each other tightly, bodies pressed together full length. Both "
     "are holding on.",
     "대상 1", "대상 2", "both"),

    # --------------------------------------------------------------------- 1인
    ("masturbate_m", "남성 자위",
     "혼자 손으로.",
     "{A} strokes {A}'s own cock vertically, up and down, at a steady rhythm.",
     "본인", SOLO, "a"),
    ("masturbate_f", "여성 자위",
     "혼자 손으로.",
     "{A} works {A}'s own fingers between {A}'s legs in small fast circles.",
     "본인", SOLO, "a"),
    ("mutual_watch", "상호 관찰 자위",
     "서로를 보며 각자 자위한다. 접촉 없음.",
     "{A} and {B} face each other and touch themselves while watching the other. {A} "
     "and {B} stay apart and do not touch each other.",
     "대상 1", "대상 2", "both"),
]

# 화면 기준 위치만 둡니다. 몸의 위·아래·앞·뒤는 행위 지시문이 이미 정하고 있어서,
# 여기서 또 고르게 하면 두 지시가 충돌합니다.
POSITION = [
    ("", "위치 지정 안 함", "프레임 안 위치를 지정하지 않습니다.", ""),
    ("left", "화면 왼쪽", "프레임 왼쪽에 둡니다.", "in the left of frame"),
    ("right", "화면 오른쪽", "프레임 오른쪽에 둡니다.", "in the right of frame"),
    ("center", "화면 가운데", "프레임 가운데에 둡니다.", "in the centre of frame"),
    ("top", "화면 위쪽", "프레임 위쪽에 둡니다.", "in the upper part of frame"),
    ("bottom", "화면 아래쪽", "프레임 아래쪽에 둡니다.", "in the lower part of frame"),
    ("near", "화면 앞쪽", "카메라에 가까운 쪽에 둡니다.", "nearest the camera"),
    ("far", "화면 뒤쪽", "카메라에서 먼 쪽에 둡니다.", "furthest from the camera"),
]

MOVER = [
    ("", "행위 기본값", "행위마다 정해진 기본 무버를 씁니다.", ""),
    ("a", "칸 1", "첫 번째 참여자가 움직입니다.", ""),
    ("b", "칸 2", "두 번째 참여자가 움직입니다.", ""),
    ("both", "양쪽", "둘 다 능동적으로 움직입니다.", ""),
]

_ACT = {a[0]: a for a in ACTS}
_POS = {p[0]: p for p in POSITION}


def act_row(key):
    """key -> the raw tuple, or None."""
    return _ACT.get(key or "")


def slot_labels(key):
    """key -> (칸1 이름, 칸2 이름). 칸2 가 '' 이면 1인 행위입니다."""
    a = _ACT.get(key or "")
    return (a[4], a[5]) if a else ("대상 1", "대상 2")


def is_solo(key):
    a = _ACT.get(key or "")
    return bool(a) and not a[5]


def position_phrase(key):
    p = _POS.get(key or "")
    return p[3] if p else ""


def rows(table):
    """UI 로 내보낼 형태. 칸 이름과 기본 무버까지 같이 보냅니다."""
    out = []
    for t in table:
        r = {"key": t[0], "ko": t[1], "tip": t[2]}
        if len(t) > 6:
            r["slot_a"], r["slot_b"], r["mover"] = t[4], t[5], t[6]
        out.append(r)
    return out


def pov_slots_unknown(card, pov_target):
    """참가자 칸이 비어서 POV 인물의 참여 여부를 알 수 없는가.

    `pov_target` 이 어느 칸에도 없다는 사실은 두 가지를 뭉뚱그립니다 — 칸이 채워져
    있는데 그 안에 없는 경우(정말 참여 안 함)와, 칸이 비어 있는 경우(모름). 예전에는
    둘 다 "참여 안 함" 으로 처리해서, 첫 샷 첫 줄을 비워 두면 브리프가 "이 사람은 위
    행위에 아무 관여도 하지 않는다" 고 단정했습니다. 사용자가 내용 칸에 "자신의 상체도
    보인다" 라고 쓰면 그게 더해지는 게 아니라 그 단정과 싸우게 됩니다.
    """
    if not pov_target:
        return False
    lines = act_lines(card)
    if not lines:
        return False
    if any(pov_target in (l["a"], l["b"]) for l in lines):
        return False
    return any(not l["a"] or (not l["b"] and not is_solo(l["act"])) for l in lines)


def act_lines(card):
    """[{at, act, a, a_pos, b, b_pos, mover}] for this card, blank rows dropped."""
    out = []
    for ln in (card.get("acts") or []):
        if not isinstance(ln, dict):
            continue
        key = (ln.get("act") or "").strip()
        if not key or key not in _ACT:
            continue
        out.append({
            "at": _seconds(ln.get("at")),
            "act": key,
            "a": (ln.get("a") or "").strip(),
            "a_pos": (ln.get("a_pos") or "").strip(),
            "b": (ln.get("b") or "").strip(),
            "b_pos": (ln.get("b_pos") or "").strip(),
            "mover": (ln.get("mover") or "").strip(),
        })
    return out


def _seconds(v):
    if v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip()):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def _fmt_at(sec):
    f = float(sec)
    return str(int(f)) if f == int(f) else ("%g" % f)


def act_block(card, label_fn, pov_target=None):
    """The card's acts as brief text. `label_fn(target)` -> '이미지 1의 인물'.

    Rows sharing a timestamp are SIMULTANEOUS — the opposite of dialogue rows, which
    are strictly sequential. When such rows also share a person, that person has one
    body and both descriptions have to hold at once; the model will otherwise draw
    them twice or alternate. That paragraph is emitted automatically.
    """
    lines = act_lines(card)
    if not lines:
        return ""

    rows_out, timed = [], False
    pov_in_act = bool(pov_target) and any(pov_target in (l["a"], l["b"]) for l in lines)
    for i, ln in enumerate(lines, start=1):
        a = _ACT[ln["act"]]
        la = "<{}>".format(label_fn(ln["a"])) if ln["a"] else "<사람 A>"
        lb = "<{}>".format(label_fn(ln["b"])) if ln["b"] else "<사람 B>"
        head = "  {}) {}".format(i, a[1])
        if ln["at"] is not None:
            head = "  {}) [{}초 시작] {}".format(i, _fmt_at(ln["at"]), a[1])
            timed = True
        body = ["     " + a[3].format(A=la, B=lb)]

        mv = ln["mover"] or a[6]
        if ln["mover"] and ln["mover"] != a[6]:
            # 무버를 바꾸면 위 지시문에 박힌 "누가 정지한다" 와 정면으로 부딪힙니다.
            # 예전에는 모순되는 문장을 그냥 덧붙였고, 두 줄 떨어진 두 지시가 서로를
            # 부정한 채로 모델에 갔습니다. 이제 앞 문장을 무효로 만든다고 못박습니다 —
            # 가까운 지시가 이기므로 이 줄이 마지막에 와야 합니다.
            # 움직이는 쪽이 바뀌면 방향도 바뀝니다. 기승위에서 남자가 주도하면 그는
            # 누운 채로 골반을 위로 쳐올리지, 위 문장에 적힌 "올라탔다 내려앉는" 움직임을
            # 하지 않습니다. 그래서 "위에 적힌 방향대로" 라고 하면 안 되고, 움직임이
            # 어느 몸에서 나오는지를 다시 말해 줘야 합니다.
            if mv == "both":
                body.append(
                    "     OVERRIDE the sentence above about either of them holding "
                    "still: HERE BOTH {} AND {} MOVE. {} drives as described, and {} "
                    "works {}'s own hips against that from the position {} is already "
                    "in, meeting every stroke so the two bodies come together harder "
                    "than either alone.".format(la, lb, la, lb, lb, lb))
            else:
                mover, held = (la, lb) if mv == "a" else (lb, la)
                body.append(
                    "     OVERRIDE the sentence above about who moves: HERE IT IS {} "
                    "WHO DRIVES THE MOTION. The movement now comes from {}'s own body, "
                    "{} working {}'s hips against {} from the position {} is already in "
                    "— do NOT reuse the direction the sentence above gave {}, that "
                    "described {}'s motion and {} is no longer the one moving. {} stays "
                    "in place and does not thrust; {}'s hands and face stay free."
                    .format(mover, mover, mover, mover, held, mover,
                            held, held, held, held, held))

        for who, pos in ((la, ln["a_pos"]), (lb, ln["b_pos"])):
            ph = position_phrase(pos)
            if ph and who:
                body.append("     {} is {}.".format(who, ph))
        rows_out.append(head)
        rows_out.extend(body)

    tail = []
    unknown = pov_slots_unknown(card, pov_target)
    if unknown:
        # 참여하는지 안 하는지 모르니, 어느 쪽이든 참인 것만 적습니다. 참여 여부에
        # 대한 주장이 없으므로 사용자가 내용 칸에 무엇을 쓰든 부딪히지 않습니다.
        me = "<{}>".format(label_fn(pov_target))
        tail.append(
            "{me} IS THE CAMERA IN THIS SHOT. Whatever parts of {me}'s own body fall "
            "within {me}'s line of sight in the posture above are drawn, foreshortened "
            "as seen looking down {me}'s own body. {me}'s face, head and back never "
            "are.".format(me=me))
    if pov_target and not pov_in_act and not unknown:
        # 관찰자가 어느 행위에도 없으면 예전에는 이 문단 전체가 생략됐습니다. 그러면
        # 남는 건 "팔과 손이 프레임 가장자리로 들어온다" 뿐인데, 눈높이에서 다리를
        # 벌리고 누운 사람을 내려다보는 화면에 팔이 들어오면 그건 학습 데이터에서
        # "내가 하고 있다" 그 자체입니다 — 실제로 관찰자와 행위자가 합쳐졌습니다.
        # 참여하지 않는다는 것을 명시적으로 적어야 갈라집니다.
        me = "<{}>".format(label_fn(pov_target))
        doers = []
        for l in lines:
            for t in (l["a"], l["b"]):
                if t:
                    lab = "<{}>".format(label_fn(t))
                    if lab not in doers:
                        doers.append(lab)
        # 예전에는 여기서 "팔과 손이 프레임 가장자리로 들어오면 그건 놀고 있는 것"
        # 이라고 했습니다. 조건절이라 약한 데다, 다른 네 곳이 "팔은 반드시 프레임에
        # 들어와야 한다" 를 의무로 말하고 있어서 3:1 로 졌습니다 — 그래서 게임 POV
        # 처럼 팔이 항상 나왔고, 나온 팔이 할 일을 찾아 상대를 만졌습니다.
        # 이제 팔을 아예 약속하지 않고, 있는 자리를 말합니다.
        tail.append(
            "{me} IS THE CAMERA IN THIS SHOT AND TAKES NO PART IN THE ACTION ABOVE. "
            "{me} is not one of the people described above — every one of them is a "
            "separate person, fully drawn, doing what is written to each other and not "
            "to {me}. {me} only watches, and {me}'s arms rest out of frame at {me}'s "
            "sides. {me}'s face, head and back are never drawn — the body over "
            "{doers2} is the person named above, not {me}.".format(
                me=me, doers2=doers[0] if doers else "them"))
    if pov_in_act:
        # 카메라 블록은 "이 사람은 형체로 보이지 않는다" 라고 하고, 자세 문장은 "무릎을
        # 꿇고 엉덩이를 움직인다" 라고 합니다. 둘 다 지키라고 하면 모델이 두 해석을
        # 뭉개 버립니다 — 실제로 그렇게 나왔습니다. 자세 문장이 '그리라' 가 아니라
        # '어디에 있다' 라는 뜻임을 못박아 겹치지 않게 합니다.
        me = "<{}>".format(label_fn(pov_target))
        others = []
        for l in lines:
            for t in (l["a"], l["b"]):
                if t and t != pov_target:
                    lab = "<{}>".format(label_fn(t))
                    if lab not in others:
                        others.append(lab)
        # POV 인물이 자기만의 1인 행위를 가진 경우 — 관음자가 보면서 자위하는 구도가
        # 대표적입니다 — 위 문단이 그 동작까지 "그리는 게 아니라 위치를 말하는 것" 으로
        # 지워 버립니다. 그러면 손이 프레임에 들어오긴 하는데 무엇을 하는지가 사라집니다.
        # 그릴 수 있다고 이미 허용한 부위(팔뚝·손·허벅지·골반)로 하는 동작이니, 그건
        # 예외로 빼서 명시적으로 그리라고 해야 합니다.
        own = [l for l in lines if is_solo(l["act"]) and l["a"] == pov_target]
        # 보이는 부위를 목록으로 못박으면 자세마다 틀립니다 — 누워 있으면 가슴·배가
        # 보이고, 서서 앞을 보면 거의 안 보입니다. 예전 목록은 팔뚝·손·허벅지·골반
        # 이었는데 "except" 로 묶여 있어서, 누워 있는 사람의 시야를 채우는 가슴과
        # 배가 통째로 지워졌습니다 (torso 를 '안 보이는 것' 으로 분류한 탓입니다.
        # 자기 눈에서 자세와 무관하게 안 보이는 건 얼굴·머리·등, 이 셋뿐입니다).
        # 그래서 보이는 쪽은 자세에서 끌어오고, 안 보이는 쪽만 고정합니다.
        tail.append(
            "{me} IS THE CAMERA IN THIS SHOT. Whatever parts of {me}'s own body fall "
            "within {me}'s line of sight in the posture above — chest, stomach, hips, "
            "thighs — are drawn, foreshortened as seen looking down {me}'s own body. "
            "{me}'s face, head and back never are. {others} {verb} fully visible, seen "
            "from {me}'s own eyes.".format(
                me=me, others=", ".join(others) or "The other person",
                verb="are" if len(others) > 1 else "is"))
        # 팔은 일이 있을 때만 시야에 들어옵니다. 그 일은 자기 행위나 '추가 동작' 에서
        # 오지, 여기서 보장하지 않습니다. 둘 다 없으면 팔이 있는 자리를 적어 줍니다 —
        # "팔을 그리지 마라" 가 아니라 위치를 말하는 문장이라야 지켜집니다.
        if not own and not (card.get("extra") or "").strip():
            tail.append("{me}'s arms rest out of frame at {me}'s sides.".format(me=me))
        if own:
            tail.append(
                "EXCEPTION for {me}'s own action listed above: that one IS DRAWN. "
                "{me}'s forearms, hands, hips and the part of {me}'s body they are "
                "working on fill the near foreground along the bottom edge of the "
                "frame, seen from {me}'s own eyes looking down at them, and they carry "
                "out that action visibly and continuously for the whole shot. {me}'s "
                "face, head and back stay undrawn.".format(me=me))
    if timed:
        tail.append("같은 시각이 적힌 줄은 동시에 일어난다. 순서대로가 아니다.")
    shared = _shared_at_same_time(lines, label_fn)
    if shared:
        tail.append(shared)
    # subject_definitions 규칙은 시스템 프롬프트에 있지만 22,000자짜리 REF2VA 블록
    # 안에 묻혀서 실제로는 무시됐습니다 — 남자와 관찰자가 번호를 못 받았고, 그 결과
    # 관찰자의 손이 남자 손으로 적히고 "카메라의 팔뚝" 같은 문장까지 나왔습니다.
    # 일반 규칙 대신 이 샷에 실제로 있는 사람의 이름을 세어서 브리프에 박습니다.
    everyone = []
    for ln in lines:
        for t in (ln["a"], ln["b"]):
            if t and t not in everyone:
                everyone.append(t)
    if pov_target and pov_target not in everyone:
        everyone.append(pov_target)
    if len(everyone) > 1:
        names = ", ".join("<{}>".format(label_fn(t)) for t in everyone)
        # 총원을 단정하면 안 됩니다. 행위 줄에 없이 '내용' 칸에만 적힌 사람이 있으면
        # 숫자가 틀리고, 틀린 숫자는 그 사람을 빼도 된다는 신호가 됩니다.
        line = ("이 샷의 행위에 참여하는 인물은 {} 이다. 이들은 한 사람도 빠짐없이 "
                "각자의 <Subject N> 을 subject_definitions 에 받는다. 위 '내용' 에 "
                "이들 말고 다른 사람이 더 적혀 있으면 그 사람도 번호를 받는다. "
                "레퍼런스 이미지가 없는 사람도 번호를 받는다 — 번호가 없으면 그 "
                "사람의 손과 동작이 다른 사람에게 잘못 붙는다.".format(names))
        if pov_target:
            line += (" 카메라인 <{}> 도 번호를 받되, 그 줄에는 그 자세에서 자기 시야에 "
                     "들어오는 자기 몸의 부위와, 얼굴·머리·등은 그려지지 않는다는 것만 "
                     "적는다.".format(label_fn(pov_target)))
        tail.append(line)

    # 행위 문장의 방향은 전부 몸 기준입니다. 그런데 "등을 ~로 돌린다", "가슴이 ~를
    # 향한다" 같은 표현은 렌더링 지시로도 읽혀서, 카메라를 어디에 두든 그 면이 보이게
    # 그려지는 일이 있었습니다 — 배면 기승위가 늘 뒷모습으로만 나오는 식으로요.
    # 두 축을 갈라 두는 문장을 행위 블록 끝에 한 번만 붙입니다.
    tail.append("위 행위 문장에서 '~쪽을 향한다', '등을 ~로 돌린다', '가슴이 ~를 향한다' "
                "같은 표현은 두 몸이 서로에 대해 어떻게 놓였는지를 말하는 것이지, "
                "카메라가 어느 면을 보는지가 아니다. 무엇이 화면에 보이는지는 카메라 "
                "지시만 정한다 — 몸의 방향에 맞춰 카메라를 옮기지 마라.")

    # 두 사람 중 한쪽만 돌아가는 문제. 행위 문장은 한 사람을 절대 기준으로 두고
    # (예: "{B} lies face up") 다른 사람을 그 사람 기준으로 적습니다 — 사슬입니다.
    # 그런데 그 절대 기준이 위아래만 정하고 방 안에서 어느 쪽을 향해 누웠는지는
    # 정하지 않아, 두 사람 덩어리 전체가 자유롭게 돌 수 있는 상태로 남습니다.
    #
    # 거기에 카메라 지시가 한 사람의 이름만 부르면("seen from behind <A>"), 모델은
    # 덩어리를 돌리는 대신 이름이 불린 그 사람만 돌려서 지시를 만족시킵니다. 나머지
    # 한 사람은 자기 문장이 따로 있어서 그대로 남고, 둘의 관계가 깨집니다.
    #
    # 카메라는 프레임 그 자체라 유일하게 회전할 수 없는 기준입니다. 두 사람을 서로가
    # 아니라 카메라에 각각 매달면 자유 변수가 사라지고, 한쪽만 만만해지는 비대칭도
    # 없어집니다. 기하는 모델이 풀 수 있습니다 — 적지 않아서 날아갔을 뿐입니다.
    pair = [ln for ln in lines if not is_solo(ln["act"]) and ln["a"] and ln["b"]]
    if pair and (card.get("facing") or card.get("angle")):
        who = []
        for ln in pair:
            for t in (ln["a"], ln["b"]):
                lab = "<{}>".format(label_fn(t))
                if lab not in who:
                    who.append(lab)
        tail.append(
            "카메라 지시는 사람을 돌리라는 뜻이 아니라 카메라가 어디에 서는지를 말하는 "
            "것이다. 카메라 자리를 먼저 확정하고, 위 행위의 두 사람을 그 프레임 안에 "
            "놓아라. 그리고 프롬프트 본문에 {} 이 각각 카메라에 대해 어느 쪽을 향하고 "
            "있는지를 한 문장씩 따로 적어라 — 누가 렌즈를 보고, 누가 등을 보이고, 누가 "
            "머리를 카메라 쪽에 두는지. 한 사람만 적고 나머지를 짐작에 맡기면, 적힌 "
            "사람만 돌아가고 다른 사람은 원래 자세로 남아 둘의 관계가 깨진다."
            .format(", ".join(who)))
    if any(ln["a_pos"] or ln["b_pos"] for ln in lines):
        tail.append("화면 위치는 이 샷의 프레임 기준이다.")
    # 자세 이름이 detailed_description 에서 통째로 사라지고 있었습니다 — "Reverse
    # cowgirl" 이 summary 에만 남고 본문에는 기하학 서술만 실렸습니다. 이름은 영상
    # 모델이 그 자세에 대해 이미 아는 것을 불러오는 열쇠라, 풀어 쓴 문장 700자보다
    # 그 단어 두 개가 더 셀 수 있습니다. 이름을 먼저 쓰고 설명이 뒤따르게 못박습니다.
    names = []
    for ln in lines:
        nm = _ACT[ln["act"]][3].split(".")[0].strip()
        if nm and nm not in names:
            names.append(nm)
    if names:
        tail.append(
            "각 행위의 영어 이름({})을 detailed_description 본문에 그대로 남겨라. "
            "이름이 사라지고 자세 설명만 남는 일이 잦았다 — 이름이 있어야 영상 모델이 "
            "그 자세에 대해 이미 아는 것을 불러온다. 그 자세를 처음 쓸 때 이름을 먼저 "
            "적고, 그 뒤에 위의 자세 설명을 이어 붙여라."
            .format(", ".join('"{}"'.format(n) for n in names)))
    tail.append("위 행위 지시는 전부 프롬프트에 그대로 반영하라. 요약하거나 순화하지 "
                "말고, 두 행위를 한 문장으로 합치지 마라.")
    return "\n".join(["행위:"] + rows_out + tail)


def _shared_at_same_time(lines, label_fn):
    by_time = {}
    for ln in lines:
        by_time.setdefault(ln["at"], []).append(ln)
    names = []
    for group in by_time.values():
        if len(group) < 2:
            continue
        seen = {}
        for ln in group:
            for t in (ln["a"], ln["b"]):
                if t:
                    seen[t] = seen.get(t, 0) + 1
        names += [t for t, n in seen.items() if n > 1]
    if not names:
        return ""
    uniq = []
    for t in names:
        if t not in uniq:
            uniq.append(t)
    who = ", ".join("<{}>".format(label_fn(t)) for t in uniq)
    # "두 자세가 동시에 성립하도록 배치하라" 는 불가능한 요구였습니다. 행위 문장은
    # 저마다 완결된 자세를 적고 있어서 — 기승위는 "올라타 있다", 펠라치오는 "바닥에
    # 무릎 꿇는다" — 겹치면 한 사람이 두 자세를 동시에 가져야 합니다. 실제로 결과에
    # 두 자세가 나란히 적혔습니다. 그래서 어느 쪽이 자세를 정하는지 못박고, 나머지
    # 줄에서는 접촉만 가져오게 합니다. 자세를 바꿔야 하는 쪽은 상대입니다.
    return ("{who} 은(는) 같은 시각의 두 줄에 모두 등장하지만 몸은 하나다. "
            "{who} 의 자세는 첫 번째 줄이 정한다. 뒤에 오는 줄에서 {who} 에게 적힌 "
            "자세(무릎을 꿇는다·눕는다·선다 같은 것)는 버리고, 그 줄에서는 {who} 가 "
            "무엇으로 무엇에 닿는지만 가져와라. 그 접촉이 첫 번째 자세 그대로 "
            "가능하도록 상대 쪽을 옮겨라 — 상대가 {who} 에게 다가가는 것이지 "
            "{who} 가 자세를 바꾸는 것이 아니다. "
            # 버려지는 자세 문장 안에 '어떻게 닿는가' 가 같이 들어 있습니다. 정상위로
            # 누운 사람이 머리맡에 선 사람에게 입으로 닿으려면 고개를 뒤로 젖혀야
            # 하는데, 그 한 문장이 사라지면 두 몸이 떨어진 채로 그려집니다.
            "{who} 가 그 자세 그대로 어떻게 닿는지를 한 문장으로 적어라 — 고개를 "
            "뒤로 젖힌다, 얼굴을 옆으로 돌린다, 팔을 뻗는다 처럼 몸의 어느 부분을 "
            "어떻게 돌리는지까지. "
            # 방향도 마찬가지입니다. "머리가 위아래로" 는 무릎 꿇은 자세를 전제한
            # 문장이라, 누워서 고개를 젖힌 몸에는 맞지 않습니다.
            "그리고 그 줄에 적힌 움직임의 방향은 {who} 의 실제 자세를 기준으로 다시 "
            "정하라. 원래 문장에 적힌 방향(위아래·앞뒤)을 그대로 베끼지 마라 — 그 "
            "방향은 버려진 자세를 전제로 쓰인 것이다. "
            "각 인물이 서로에 대해 어디에 있는지 "
            "적고, 같은 인물을 두 번 그리거나 두 행위를 번갈아 보여주지 "
            "마라.".format(who=who))


# ---------------------------------------------------------------------------
# 전개 (progression) — "다음 동작" 을 이름 대신 빈칸으로 지정합니다
# ---------------------------------------------------------------------------
# 동작 이름을 적으면 모델은 그것만 반복합니다 ("가슴을 만진다" -> 계속 가슴만).
# 아무것도 안 적으면 아무 일도 일어나지 않습니다. 가운데가 없었습니다.
#
# 그래서 무엇을 할지가 아니라 어디가 비었는지를 지정합니다: 언제 / 누가 / 어느
# 부위로 / 어디를 향해. 노드가 시드로 굴려서 브리프에 박고, 구체적인 동작은 모델이
# 채웁니다. 시드를 바꾸면 조합이 바뀌므로 매 실행이 실제로 달라집니다 — 모델에게
# 고르라고 하면 매번 가장 무난한 답으로 수렴해서 안 달라집니다.

# 굴릴 수 있는 부위는 손·입·시선·숨 넷뿐입니다. 허리와 다리는 어떤 행위든 이미
# 쓰고 있어서, 굴리면 자세와 정면으로 부딪힙니다 — 추가 동작이 행위를 못 이긴다는
# 규칙과 같은 이유입니다. 실제로 필요했던 것도 "팔의 움직임" 쪽이었습니다.
# 각 부위는 향할 수 있는 곳이 다릅니다. 숨이 "주변을 향한다" 는 말이 안 됩니다.
PART = [
    ("손",   "손과 팔",       ("자기", "상대", "주변")),
    ("입",   "입과 혀",       ("자기", "상대")),
    ("시선", "시선과 표정",   ("상대", "주변")),
    ("숨",   "호흡과 목소리", ()),
]

TOWARD = {
    "자기": "자기 몸",
    "상대": "상대의 몸",
    "주변": "주변의 물건이나 바닥·벽·옷",
}

# POV 인물은 얼굴이 안 그려집니다. 시선과 입은 보여줄 방법이 없으니 뺍니다.
_POV_PARTS = ("손", "숨")


def _josa(word, with_batchim, without):
    """한글 조사. 받침이 있으면 앞것, 없으면 뒷것. '입과 혀이' 같은 걸 막습니다."""
    for ch in reversed(word or ""):
        if "가" <= ch <= "힣":
            return with_batchim if (ord(ch) - 0xAC00) % 28 else without
        if ch.isalnum():
            break
    return without


def _roll(seed, salt, n):
    """시드에서 결정적으로 하나를 고릅니다. random 모듈을 쓰지 않는 이유는
    ComfyUI 가 전역 시드를 여기저기서 건드려서 재현이 깨지기 때문입니다.

    예전에는 `(h >> 7) % n` 으로 줄였는데 그 비트가 균일하지 않아, 후보가 4개일 때
    마지막 항목이 25% 가 아니라 36% 로 나왔습니다 (호흡·목소리가 유독 자주 나오던
    이유). 이제 전체 32비트를 곱셈-시프트로 축약합니다.
    """
    h = (int(seed) & 0xFFFFFFFF) ^ ((int(salt) * 2654435761) & 0xFFFFFFFF)
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 3266489917) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 668265263) & 0xFFFFFFFF
    h ^= h >> 16
    return (h * max(1, n)) >> 32


def progression_block(card, label_fn, seed, count, duration, pov_target=None,
                      target=""):
    """행위 참가자에서 뽑은 축을 굴려 '다음 동작' 지시를 만듭니다.

    `target` 이 지정되면 그 사람만 움직입니다. 비어 있으면 행위 참가자 중에서
    시드로 뽑습니다 — 다만 참가자가 한 명뿐인 카드(한 칸을 비워둔 경우)에서는
    랜덤이라도 항상 그 한 명이 나옵니다.

    대상을 아예 알 수 없으면 아무것도 내보내지 않습니다 — 누가 움직이는지 없이
    "뭔가 일어난다" 만 적으면 모델이 장면을 새로 지어냅니다.
    """
    count = max(0, int(count or 0))
    if count <= 0:
        return ""
    if target:
        # 사용자가 직접 고른 대상은 행위 줄에 없어도 그대로 씁니다. 누가 움직이는지
        # 명시된 이상, 굴릴 이유도 막을 이유도 없습니다.
        people = [target]
    else:
        people = []
        for ln in act_lines(card):
            for t in (ln["a"], ln["b"]):
                if t and t not in people:
                    people.append(t)
    if not people:
        return ""

    dur = float(duration or 0) or 6.0
    out, seen = [], set()
    for k in range(count):
        # 구간을 나눠 하나씩 배치합니다. 3초짜리에 두 번이 겹치면 뭉갭니다.
        at = dur * (k + 1) / (count + 1)
        who = people[_roll(seed, 101 + k * 7, len(people))]
        is_pov = bool(pov_target) and who == pov_target
        pool = [p for p in PART if (not is_pov) or p[0] in _POV_PARTS]
        # 같은 사람의 같은 부위가 두 번 굴려지면 "같은 일이 두 번" 이 되어 전개가
        # 아닙니다. 겹치면 후보 목록을 한 칸씩 밀어 아직 안 쓴 조합을 찾습니다.
        pi = _roll(seed, 211 + k * 7, len(pool))
        for step in range(len(pool)):
            cand = pool[(pi + step) % len(pool)]
            if (who, cand[0]) not in seen:
                pi = (pi + step) % len(pool)
                break
        part = pool[pi]
        seen.add((who, part[0]))
        me = "<{}>".format(label_fn(who))
        line = "  {:.1f}초쯤, {}{} 먼저 움직인다.".format(
            at, me, _josa(label_fn(who), "이", "가"))
        if is_pov:
            line += " (이 인물은 카메라라 몸이 그려지지 않는다 — 팔·손만 보인다)"
        line += " {}의 {}{} 새로 관여한다.".format(
            me, part[1], _josa(part[1], "이", "가"))
        if part[2]:
            tw = part[2][_roll(seed, 307 + k * 7, len(part[2]))]
            line += " 향하는 곳은 {}이다.".format(
                me if tw == "자기" else TOWARD[tw])
        out.append(line)
    # 꼬리에서 "위의 행위" 를 가리키는데, 행위 줄이 없는 샷이면 가리킬 블록이 없습니다.
    # 이 기능은 야스 전용이 아니고 대상만 고르면 어떤 장면에서도 쓰이므로, 무엇이
    # 계속되는지를 실제로 있는 블록 이름으로 말합니다.
    keeps = "위의 행위는" if act_lines(card) else "위에 적힌 내용과 동작은"
    return ("전개 — 아래는 동작의 '빈칸' 이다. 무엇을 할지는 정해두지 않았다:\n"
            + "\n".join(out) + "\n"
            "지금 화면에서 그 부위가 실제로 어디에 있는지 보고, 거기서 자연스럽게 "
            "이어지는 동작을 하나씩 네가 정해서 써라. 각 변화는 한 번만 일어난다.\n"
            + keeps + " 그동안 그대로 계속된다. 자세·카메라·구도는 바뀌지 않고, "
            "컷도 넣지 마라. 위에 이미 지시된 내용과 겹치면 그 줄은 건너뛰어라.")
