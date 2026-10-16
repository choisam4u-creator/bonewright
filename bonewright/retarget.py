"""BVH → Rigify 리타겟용 이름 매핑(토큰 0). 어느 BVH 관절이 우리 리그의 어느 FK 컨트롤을 움직이는지 정한다.

이름 규약은 BVH 마다 다르다(Mixamo: LeftUpLeg/LeftLeg, kimodo: LeftLeg/LeftShin). 벤치마크의 정규화(_norm/_cores)를
그대로 쓰되, 한 쪽에 'leg' 와 'shin' 이 같이 있으면 'leg' 는 허벅지로 본다 — 'leg' 하나만 있으면 정강이(JOINT_MAP 관습).
"""
import re

from .bench import JOINT_MAP, QUAD_MAP, _cores, _norm

# 우리 기준 이름 → Rigify FK 컨트롤. 척추 중간(spine.001~.003)은 chest 하나로 받는다
FK_TARGET = {
    "spine": "torso", "chest": "chest", "spine.004": "neck", "spine.006": "head", "shoulder": "shoulder",
    "upper_arm": "upper_arm_fk", "forearm": "forearm_fk", "hand": "hand_fk",
    "thigh": "thigh_fk", "shin": "shin_fk", "foot": "foot_fk",
}
# 사족(늑대 메타리그): QUAD_MAP 의 골반 키가 spine.004 이고 앞다리는 front_* 다. 목·머리는 QUAD_MAP 에 없어 여기서 보탠다
FK_TARGET_QUAD = {
    "spine.004": "torso", "chest": "chest", "neck": "neck", "head": "head",
    "front_thigh": "front_thigh_fk", "front_shin": "front_shin_fk", "front_foot": "front_foot_fk",
    "thigh": "thigh_fk", "shin": "shin_fk", "foot": "foot_fk",
}
QUAD_EXTRA = {"neck": ["neck"], "head": ["head"]}
# 꼬리: 늑대 메타리그의 꼬리 사슬은 골반 쪽부터 spine.003 → .002 → .001 → spine 이다(번호가 거꾸로 붙어 있다).
# 원본 꼬리 마디 수는 제각각이라(Quaternius 늑대 8마디) 길이 비례로 4개에 나눠 준다
TAIL_TARGETS = ["spine.003", "spine.002", "spine.001", "spine"]
SIDED = {"shoulder", "upper_arm_fk", "forearm_fk", "hand_fk", "thigh_fk", "shin_fk", "foot_fk",
         "front_thigh_fk", "front_shin_fk", "front_foot_fk"}
CHEST_WORDS = ("chest", "spine2", "spine3", "upperchest")
# 관절 이름 규약(SMPL·자세 추정 도구가 내보내는 BVH: L_Hip/L_Knee/L_Ankle, L_Collar/L_Shoulder/L_Elbow/L_Wrist).
# BVH 관절은 거기서 시작하는 뼈를 돌리므로 Hip=허벅지·Knee=정강이·Shoulder=위팔·Elbow=아래팔이다.
# 10/16 22회차 실측: 이 규약이면 팔다리 9개가 말없이 안 움직였다(Hip 은 골반, Shoulder 는 쇄골로 읽혔다)
KNEE_WORDS = {"hip": "thigh", "knee": "shin"}
ELBOW_WORDS = {"shoulder": "upper_arm", "elbow": "forearm"}


def bvh_mapping(bvh_names: list[str], preset: str = "humanoid") -> dict[str, str]:
    """BVH 관절 이름 → 우리 FK 본 이름. 못 옮기는 관절은 빼고, 같은 목표에 둘이 오면 먼저 온 쪽을 둔다"""
    quad = preset == "quadruped"
    joint_map = {**QUAD_MAP, **QUAD_EXTRA} if quad else JOINT_MAP
    fk_target = FK_TARGET_QUAD if quad else FK_TARGET
    want = {c: base for base, cands in joint_map.items() for c in cands}
    norm = {n: _norm(n) for n in bvh_names}
    # 'leg' 와 'shin' 이 같은 쪽에 함께 있으면 leg=허벅지
    has_shin = {side for n, (core, side) in norm.items() if "shin" in _cores(core)}
    # 관절 이름 규약: 무릎·팔꿈치가 있는 쪽만(Mixamo 의 LeftShoulder=쇄골, 골반 Hips 는 그대로). 위팔 이름(arm·upperarm)이 따로 있으면 그쪽이 위팔
    has_knee = {side for n, (core, side) in norm.items() if side and "knee" in _cores(core)}
    arm_named = {side for core, side in norm.values() if _cores(core) & {"arm", "upperarm"}}
    has_elbow = {side for core, side in norm.values() if side and "elbow" in _cores(core)} - arm_named
    elbow_words = {"shoulder": "front_thigh", "elbow": "front_shin"} if quad else ELBOW_WORDS   # 사족은 앞다리
    # 가슴: chest 라는 이름이 없으면(Mixamo: Spine/Spine1/Spine2, Quaternius 동물: Torso/Torso2/Torso3) 번호가 가장 큰 척추 관절을 가슴으로 본다.
    # _norm 이 끝 번호를 지우므로 원래 이름에서 따로 본다
    raw = {n: re.sub(r"[^a-z0-9]", "", n.lower().split(":")[-1]) for n in bvh_names}
    spines = [n for n in bvh_names if re.fullmatch(r"(spine|torso)\d*", raw[n])]
    chest_name = next((n for n in bvh_names if any(w in _cores(norm[n][0]) for w in CHEST_WORDS)), None)
    if chest_name is None and len(spines) >= 2:
        chest_name = spines[-1]
    out, taken = {}, set()
    for n in bvh_names:
        core, side = norm[n]
        cores = _cores(core)
        base = None
        if "leg" in cores and side in has_shin:
            base = "thigh"
        elif side in has_knee and (hit := next((KNEE_WORDS[c] for c in cores if c in KNEE_WORDS), None)):
            base = hit
        elif side in has_elbow and (hit := next((elbow_words[c] for c in cores if c in elbow_words), None)):
            base = hit
        elif n == chest_name:
            base = "chest"
        else:
            base = next((want[c] for c in cores if c in want), None)
        if base is None or base not in fk_target:
            continue
        tgt = fk_target[base]
        if tgt in SIDED:
            if side is None:
                continue
            tgt = f"{tgt}.{side}"
        if tgt in taken:
            continue
        out[n] = tgt; taken.add(tgt)
    if quad:
        tails = sorted((n for n in bvh_names if re.fullmatch(r"tail\d*", raw[n])),
                       key=lambda n: int(re.search(r"\d+", raw[n]).group() or 0) if re.search(r"\d+", raw[n]) else 0)
        if tails:   # 원본 마디가 4개보다 적으면 밑동부터 순서대로, 많으면 고르게 골라 4개에 나눈다
            n = min(len(TAIL_TARGETS), len(tails))
            for tgt, src_name in zip(TAIL_TARGETS, [tails[i * len(tails) // n] for i in range(n)]):
                if tgt not in taken and src_name not in out:
                    out[src_name] = tgt; taken.add(tgt)
    return out


def bvh_rest_joints(path: str) -> dict[str, list[float]]:
    """BVH 의 HIERARCHY 만 읽어 관절의 쉬는 자세 좌표를 만든다(OFFSET 누적). End Site 는 부모이름+'_end'."""
    pos, stack, name = {}, [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            tok = raw.split()
            if not tok:
                continue
            w = tok[0].upper()
            if w in ("ROOT", "JOINT") and len(tok) > 1:
                name = tok[1]
            elif w == "END":
                name = (stack[-1] if stack else "root") + "_end"
            elif w == "OFFSET" and name and len(tok) >= 4:
                base = pos.get(stack[-1], [0.0, 0.0, 0.0]) if stack else [0.0, 0.0, 0.0]
                pos[name] = [base[i] + float(tok[i + 1]) for i in range(3)]
            elif w == "{":
                stack.append(name)
            elif w == "}":
                if stack:
                    stack.pop()
            elif w == "MOTION":
                break
    return pos


def detect_bvh_up(path: str, preset: str = "humanoid") -> str:
    """BVH 의 위 축을 알아낸다. 규약은 Y 위지만 블렌더가 내보낸 파일은 Z 가 위다.
    틀리면 조용히 망가진다(늑대 걷기: 방향 오차 2.75° → 14.9°, 발이 바닥에서 1m 뜸) — 그래서 이름이 아니라
    **머리가 발보다 위에 있는 축**으로 정한다. 머리·발을 못 찾으면 규약대로 'y'."""
    joint_map = {**QUAD_MAP, **QUAD_EXTRA} if preset == "quadruped" else JOINT_MAP
    want_top = set(joint_map.get("spine.006", []) + joint_map.get("head", []) + ["neck"])
    want_low = set(joint_map.get("foot", []) + joint_map.get("front_foot", []) + ["toe", "ankle"])
    pos = bvh_rest_joints(path)
    top, low = [], []
    for n, p in pos.items():
        cores = _cores(_norm(n.removesuffix("_end"))[0])
        if cores & want_top:
            top.append(p)
        if cores & want_low:
            low.append(p)
    if not (top and low):
        return "y"
    scores = {ax: min(t[ax] for t in top) - max(l[ax] for l in low) for ax in (1, 2)}
    return "z" if scores[2] >= scores[1] else "y"
