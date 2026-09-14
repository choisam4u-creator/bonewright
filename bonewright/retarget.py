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
SIDED = {"shoulder", "upper_arm_fk", "forearm_fk", "hand_fk", "thigh_fk", "shin_fk", "foot_fk",
         "front_thigh_fk", "front_shin_fk", "front_foot_fk"}
CHEST_WORDS = ("chest", "spine2", "spine3", "upperchest")


def bvh_mapping(bvh_names: list[str], preset: str = "humanoid") -> dict[str, str]:
    """BVH 관절 이름 → 우리 FK 본 이름. 못 옮기는 관절은 빼고, 같은 목표에 둘이 오면 먼저 온 쪽을 둔다"""
    quad = preset == "quadruped"
    joint_map = {**QUAD_MAP, **QUAD_EXTRA} if quad else JOINT_MAP
    fk_target = FK_TARGET_QUAD if quad else FK_TARGET
    want = {c: base for base, cands in joint_map.items() for c in cands}
    norm = {n: _norm(n) for n in bvh_names}
    # 'leg' 와 'shin' 이 같은 쪽에 함께 있으면 leg=허벅지
    has_shin = {side for n, (core, side) in norm.items() if "shin" in _cores(core)}
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
    return out
