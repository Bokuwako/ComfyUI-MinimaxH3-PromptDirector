"""Read-only diagnostics for card metadata; never rewrite action descriptions."""
import math
import string

from . import acts


def seconds(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def card_problems(cards, duration=0):
    problems = []
    formatter = string.Formatter()
    for index, card in enumerate(cards):
        label = "샷 {}".format(index + 1)
        start = 0.0 if index == 0 else seconds(card.get("at"))
        end = seconds(cards[index + 1].get("at")) if index + 1 < len(cards) else (duration or None)
        seen, positions = set(), {}
        for number, line in enumerate(card.get("acts") or [], 1):
            if not isinstance(line, dict):
                problems.append(label + ": 행위 입력 형식을 확인하세요.")
                continue
            key = line.get("act") or ""
            if not key:
                continue
            prefix = "{} 행위 {}: ".format(label, number)
            row = acts.act_row(key)
            if row is None:
                problems.append(prefix + "알 수 없는 프리셋 ID입니다. 입력을 확인하세요.")
                continue
            a, b = line.get("a") or "", line.get("b") or ""
            if not a or (row[5] and not b):
                problems.append(prefix + "필수 참여자가 지정되지 않았습니다.")
            if row[5] and a and a == b:
                problems.append(prefix + "서로 다른 두 역할에 같은 참여자가 지정됐습니다.")
            if not row[5] and b:
                problems.append(prefix + "1인 프리셋에 이전 두 번째 참여자 값이 남아 있습니다.")
            mover = line.get("mover") or row[6]
            if mover not in ("a", "b", "both"):
                problems.append(prefix + "움직이는 참여자 선택값이 올바르지 않습니다.")
            elif not row[5] and mover != "a":
                problems.append(prefix + "1인 프리셋과 움직이는 참여자 선택이 충돌합니다.")
            elif mover != row[6]:
                problems.append(prefix + "기본 설명과 다른 움직임 주체를 선택했습니다. 기존 묘사와 변경 지시의 충돌을 확인하세요. 자동 수정하지 않습니다.")
            try:
                fields = {name for _, name, _, _ in formatter.parse(row[3]) if name is not None}
                if fields - {"A", "B"}:
                    problems.append(prefix + "설명에 지원하지 않는 치환 변수가 있습니다.")
            except ValueError:
                problems.append(prefix + "설명의 치환 괄호 형식이 올바르지 않습니다.")
            raw = line.get("at")
            at = seconds(raw)
            if raw not in (None, "") and at is None:
                problems.append(prefix + "시각은 전체 영상 기준의 0 이상 유한한 초 값이어야 합니다.")
            elif at is not None and ((start is not None and at < start) or (end is not None and at >= end)):
                problems.append(prefix + "시작 시각이 해당 샷 구간 밖입니다. 전체 영상 기준 초를 사용하세요.")
            effective_at = at if at is not None else start
            identity = (key, a, b, effective_at, mover)
            if identity in seen:
                problems.append(prefix + "동일한 참여자·프리셋·시각의 중복 행입니다. 자동 삭제하지 않습니다.")
            seen.add(identity)
            for who, position in ((a, line.get("a_pos")), (b, line.get("b_pos"))):
                if not who:
                    continue
                coordinate = (who, effective_at)
                prior = positions.get(coordinate)
                if prior and (prior[0] != key or (position and prior[1] and position != prior[1])):
                    problems.append(prefix + "같은 시각의 참여자에게 다른 행위 또는 화면 위치가 지정됐습니다. 양립 가능성을 확인하세요. 자동 재배치하지 않습니다.")
                positions[coordinate] = (key, position)
    return problems


def reference_problems(refs, cards, mode=None, picture_numbers=None):
    problems, frames, assigned = [], {}, {}
    targets = {str(line.get(k)) for card in cards for line in (card.get("acts") or [])
               if isinstance(line, dict) for k in ("a", "b") if line.get(k)}
    targets.update(str(line.get("who")) for card in cards for line in (card.get("lines") or [])
                   if isinstance(line, dict) and line.get("who"))
    for ref in refs or []:
        role, n = ref.get("role") or "", ref.get("n")
        if not role:
            continue
        prefix = "이미지 {}: ".format(n)
        scoped = ref.get("shots") or []
        if not isinstance(scoped, list) or any(not isinstance(i, int) or isinstance(i, bool) or not 1 <= i <= len(cards) for i in scoped):
            problems.append(prefix + "적용 샷 번호가 현재 카드 범위를 벗어납니다.")
            scoped = []
        if picture_numbers is not None and n not in picture_numbers:
            problems.append(prefix + "역할을 지정했지만 Writer에 전달된 이미지 목록에 없습니다. 연결과 번호를 확인하세요.")
        if role in ("first_frame", "last_frame"):
            frames.setdefault(role, []).append(n)
            if mode:
                compatible = {"first_frame": ("I2VA", "FL2VA", "REF2VA"),
                              "last_frame": ("L2VA", "FL2VA", "REF2VA")}
                if mode not in compatible[role]:
                    problems.append(prefix + "지정한 프레임 역할과 생성 모드 {}가 맞지 않습니다.".format(mode))
                elif mode != "REF2VA" and picture_numbers:
                    expected = picture_numbers[-1] if role == "last_frame" else picture_numbers[0]
                    if expected != n:
                        problems.append(prefix + "이 모드의 실제 프레임 입력 번호는 {}입니다.".format(expected))
                elif mode == "REF2VA":
                    problems.append(prefix + "프레임 역할은 텍스트 참조 지시입니다. 실제 키프레임 조건 연결 여부는 생성 노드에서 확인하세요.")
        if role in ("pov_self", "ots_self"):
            vp = "pov" if role == "pov_self" else "shoulder"
            if not any(c.get("viewpoint") == vp and c.get("vp_target") == "pic:{}".format(n)
                       and (not scoped or i in scoped) for i, c in enumerate(cards, 1)):
                problems.append(prefix + "지정한 POV/어깨너머 시점과 일치하는 샷이 없습니다.")
        if role in ("face", "pose", "outfit", "expression") and not ref.get("target") and len(targets) > 1:
            problems.append(prefix + "인물이 여러 명입니다. 참조를 적용할 대상을 지정하세요.")
        target = ref.get("target") or ""
        if target and role in ("face", "pose", "outfit", "expression", "prop"):
            for shot in scoped or range(1, len(cards) + 1):
                token = (target, role, shot)
                if token in assigned and assigned[token] != n:
                    problems.append(prefix + "같은 샷·대상·속성에 복수 이미지가 지정됐습니다. 우선할 참조를 확인하세요.")
                assigned[token] = n
    for role, numbers in frames.items():
        if len(set(numbers)) > 1:
            problems.append("{}: 서로 다른 이미지가 같은 프레임 역할로 지정됐습니다: {}".format(role, numbers))
    return problems
