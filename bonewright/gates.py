"""리그 게이트(토큰 0): 통계 JSON 을 기준값과 비교해 실패 목록을 돌려준다."""

# 사람 몸 치수를 전제로 만든 파이프라인이라, 그 전제가 깨진 메시에서는 결과가 조용히 엉망이 된다
# (실측: 로봇 키의 277%, 곤충 58%, 치비 28% 어긋난 리그를 아무 경고 없이 내놨다).
# 아래 기준은 자산 17종의 분석 신호와 정답 대조 오차를 맞춰 고른 것이다 —
# 이 규칙으로 7종(오차 1.6~7.4%)이 통과하고 10종(10.1% 이상)이 걸러진다.
BLOCKING_FALLBACKS = ("crotch", "hip", "knee", "ankle")   # 목(neck) 폴백만은 경고로 끝낸다(quaternius_ual 7.4% 는 쓸 만했다)


def preflight(landmarks: dict, stats: dict, preset: str, g: dict) -> tuple[list[str], list[str]]:
    """모델을 부르기 **전에** 이 메시가 이 프리셋에 맞는지 본다. (막는 이유, 경고) 를 돌려준다.
    여기서 막으면 토큰을 한 푼도 안 쓴다 — 리그 1건이 입력 8만 토큰이라 이게 실질적인 비용 절감이다."""
    block, warn = [], []
    H = landmarks.get("height") or 0.0
    lo, hi = g.get("min_height_m", 0.3), g.get("max_height_m", 20.0)
    if not (lo <= H <= hi):
        block.append(f"메시 크기 {H}m 가 캐릭터 범위({lo}~{hi}m) 밖이다 — 단위가 틀렸거나 캐릭터가 아니다"
                     " (안/밖 판정용 복셀이 1.2cm 라 이보다 작으면 측정 자체가 무의미하다)")
    if preset == "quadruped":
        q = landmarks.get("quad") or {}
        if not q.get("ok"):
            block.append("사족: 발 네 개를 못 찾았다 — " + ("; ".join(q.get("notes") or []) or "근거 없음"))
        warn.append("사족: 자산 11종 정답 대조 평균 오차는 키의 5.6% 다(늑대 3.2%, 소 7.4%). 개과·발굽 체형만 확인했다")
        return block, warn
    # 조각으로 만든 모델(로봇)은 실루엣으로 팔다리를 못 가르지만, **조각 자체가 마디라** 관절을 잴 수 있다.
    # 발목·무릎·고관절·팔 높이가 전부 조각에서 나왔으면 '근거 없음'이 아니다 → 막지 않고 경고로 넘긴다
    # (RobotExpressive: 이 경로로 키의 7.7%. 사람형 통과 무리가 1.6~7.4% 다)
    fs = landmarks.get("foot_split") or {}
    from_parts = all(fs.get(k) is not None for k in ("x", "ankle_z", "knee_z", "hip_z", "arm_z")) and (fs.get("leg_parts") or 0) >= 6
    if from_parts:
        warn.append(f"조각 구조에서 관절을 쟀다(다리 조각 {fs['leg_parts']}개) — 실루엣 근거가 아니므로 렌더를 꼭 확인하라")
    else:
        # 사람형: 팔·다리 중심선이 양쪽 다 있어야 한다. 하나라도 없으면 관절을 놓을 근거가 없다
        for part, ko, josa in (("arm", "팔", "을"), ("leg", "다리", "를")):
            miss = [s for s in ("L", "R") if not landmarks.get(f"{part}_axis_{s}")]
            if miss:
                block.append(f"{ko} 중심선 없음({'/'.join(miss)}쪽) — 이 메시에서 {ko}{josa} 못 찾았다")
    # 메시 **속**(_medial)에서 채운 관절도 근거다 — 지어낸 비율이 아니라 잰 값이다. 어디서 왔는지는 밝힌다
    med = landmarks.get("medial") or {}
    supplied = med.get("supplied") or []
    if supplied:
        warn.append("메시 속 중심선에서 채운 값이 있다(" + ", ".join(supplied) + ") — 실루엣 근거가 아니므로 렌더를 꼭 확인하라")
    # 속-읽기가 좌우로 어긋났으면 그 값으로 만든 중심선은 근거로 치지 않는다.
    # (godot_player: 어깨 견갑을 손으로 잡아 손 높이가 좌 0.73 / 우 1.96 — 그대로 통과시키면 오차 18%)
    if supplied and not med.get("consistent"):
        bad = [k for k in supplied if k.startswith("arm_axis")]
        if bad:
            block.append("메시 속에서 찾은 팔이 좌우로 어긋난다(" + ", ".join(bad) + ") — 자세가 있거나 좌우가 다른 메시다")
    fb = set(landmarks.get("ratio_fallbacks") or [])
    hard = [] if from_parts else sorted(fb & set(BLOCKING_FALLBACKS))
    if hard:
        block.append(f"관절을 메시에서 못 찾아 인체 비율로 때웠다: {', '.join(hard)}")
    if fb - set(BLOCKING_FALLBACKS):
        warn.append("인체 비율 폴백(경고): " + ", ".join(sorted(fb - set(BLOCKING_FALLBACKS))))
    if landmarks.get("chibi"):
        block.append(f"치비 비율(머리가 키의 {round((landmarks.get('head_ratio') or 0) * 100)}%) — 사람 비율 전제가 깨진다")
    sym = landmarks.get("symmetry_error") or 0.0
    tol = g.get("max_symmetry_error_ratio", 0.03) * (H or 1.8)
    if sym > tol:
        block.append(f"좌우 비대칭 {round(sym, 3)} > {round(tol, 3)} — T 포즈가 아니거나 좌우가 다른 메시다")
    return block, warn



def rig_gates(stats: dict, g: dict, verts: int, source_symmetry: float = 0.0) -> list[str]:
    fails = []
    # 가중치 없는 정점은 fit_generate 가 가장 가까운 본으로 메운다 → 메운 수(filled_unweighted)로 판정한다. 메운 뒤에도 남으면 그것도 실패
    holes = stats["unweighted_verts"] + stats.get("filled_unweighted", 0)
    if verts and holes / verts > g["max_unweighted_ratio"]:
        fails.append(f"가중치 없는 정점 {holes}/{verts} (가까운 본으로 메운 {stats.get('filled_unweighted', 0)}개 포함)")
    if stats["weight_sum_min"] < g["weight_sum_min"] or stats["weight_sum_max"] > g["weight_sum_max"]:
        fails.append(f"가중치 합 범위 {stats['weight_sum_min']}~{stats['weight_sum_max']} (허용 {g['weight_sum_min']}~{g['weight_sum_max']})")
    # 변형 본 최소치는 사람 메타리그(410본) 기준이다. 원본 뼈대를 그대로 베낀 **일반 리그**는 본 수가
    # 원본을 따라가므로(관절 4개짜리 블롭도 있다) 그 기준을 그대로 대면 멀쩡한 리그가 실패로 찍힌다.
    # 일반 리그에서는 "원본 본이 전부 변형 본이 됐는가"로 대신 본다
    src_bones = stats.get("generic_source_bones")
    if src_bones:
        if stats["deform_bones"] < src_bones:
            fails.append(f"일반 리그: 변형 본 {stats['deform_bones']} < 원본이 살을 움직이던 본 {src_bones} — 옮겨지지 않은 본이 있다")
    elif stats["deform_bones"] < g["deform_bones_min"]:
        fails.append(f"변형 본 {stats['deform_bones']} < {g['deform_bones_min']}")
    # 일반 리그는 원본 뼈대를 **그대로** 베낀다 — 본이 메시 밖에 있다면 원작자가 거기에 둔 것이지 우리가 옮긴 게 아니다
    # (Quaternius 유령: 꼬리 끝 Body3/Body4 가 반투명 부분이라 메시 없이 본만 있다). 실패가 아니라 경고로 남긴다
    if len(stats["bones_outside_bbox"]) > g["max_bones_outside_bbox"] and not src_bones:
        fails.append(f"메시 상자 밖 변형 본 {len(stats['bones_outside_bbox'])}: {stats['bones_outside_bbox'][:5]}")
    tol = g["symmetry_max_error"] * max(0.2, stats.get("height", 1.8) / 1.8)   # 키 비례(1.8m 기준값)
    # --from-skeleton 은 원본 뼈대 좌표를 그대로 쓴다. 원본이 이미 비대칭이면 그 비대칭은 우리 오차가 아니다
    # (three.js RobotExpressive 어깨 6.7cm, Quaternius 알파카 앞다리 8.5cm) → 원본만큼은 봐준다.
    # 사슬 아래로 내려가며 조금 커지므로(알파카 8.5 → 발끝 9.7cm) 1/4 을 더 둔다
    tol = max(tol, source_symmetry * 1.25)
    out_mesh = stats.get("deform_outside_mesh", 0)
    if out_mesh > g.get("max_deform_outside_mesh", 0) and not src_bones:
        fails.append(f"메시 밖 변형 본 {out_mesh}: {stats.get('deform_outside_mesh_bones', [])[:4]}")
    tv = stats.get("weight_leak_torso_verts", 0)
    # 표본이 너무 적으면 비율을 판단할 수 없다 — 저폴리 캐릭터는 몸통 한가운데 띠에 정점이 열두어 개뿐이다
    # (cesium_man 12개). 30개 미만이면 이 검사를 건너뛰고, 그 위에서는 정점 하나를 잡음으로 보고 비율과 함께 본다
    if tv >= 30 and stats.get("weight_leak_arm_torso", 0) > max(1, tv * g.get("max_weight_leak_ratio", 0.005)):
        fails.append(f"팔 본이 몸통으로 샌 정점 {stats['weight_leak_arm_torso']}/{tv}")
    if stats["symmetry_max_error"] > tol:
        fails.append(f"좌우 대칭 오차 {stats['symmetry_max_error']} > {round(tol, 4)} (최악 {stats.get('symmetry_worst')})")
    return fails


def judge_gates(judge: dict) -> list[str]:
    fails = []
    if judge.get("bones_outside_mesh"):
        fails.append("시각 판정: 메시 밖 본 " + ", ".join(judge["bones_outside_mesh"][:5]))
    if judge.get("proportions_ok") is False:
        fails.append("시각 판정: 비율 이상 — " + (judge.get("notes") or "")[:120])
    return fails
