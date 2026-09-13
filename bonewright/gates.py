"""리그 게이트(토큰 0): 통계 JSON 을 기준값과 비교해 실패 목록을 돌려준다."""


def rig_gates(stats: dict, g: dict, verts: int) -> list[str]:
    fails = []
    if verts and stats["unweighted_verts"] / verts > g["max_unweighted_ratio"]:
        fails.append(f"가중치 없는 정점 {stats['unweighted_verts']}/{verts}")
    if stats["weight_sum_min"] < g["weight_sum_min"] or stats["weight_sum_max"] > g["weight_sum_max"]:
        fails.append(f"가중치 합 범위 {stats['weight_sum_min']}~{stats['weight_sum_max']} (허용 {g['weight_sum_min']}~{g['weight_sum_max']})")
    if stats["deform_bones"] < g["deform_bones_min"]:
        fails.append(f"변형 본 {stats['deform_bones']} < {g['deform_bones_min']}")
    if len(stats["bones_outside_bbox"]) > g["max_bones_outside_bbox"]:
        fails.append(f"메시 상자 밖 변형 본 {len(stats['bones_outside_bbox'])}: {stats['bones_outside_bbox'][:5]}")
    tol = g["symmetry_max_error"] * max(0.2, stats.get("height", 1.8) / 1.8)   # 키 비례(1.8m 기준값)
    tv = stats.get("weight_leak_torso_verts", 0)
    if tv and stats.get("weight_leak_arm_torso", 0) / tv > g.get("max_weight_leak_ratio", 0.005):
        fails.append(f"팔 본이 몸통으로 샌 정점 {stats['weight_leak_arm_torso']}/{tv}")
    if stats["symmetry_max_error"] > tol:
        fails.append(f"좌우 대칭 오차 {stats['symmetry_max_error']} > {round(tol, 4)}")
    return fails


def judge_gates(judge: dict) -> list[str]:
    fails = []
    if judge.get("bones_outside_mesh"):
        fails.append("시각 판정: 메시 밖 본 " + ", ".join(judge["bones_outside_mesh"][:5]))
    if judge.get("proportions_ok") is False:
        fails.append("시각 판정: 비율 이상 — " + (judge.get("notes") or "")[:120])
    return fails
