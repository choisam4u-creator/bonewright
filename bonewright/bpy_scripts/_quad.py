"""사족 관절 찾기(토큰 0). 사람용 관절 찾기는 네 발 동물에서 무의미한 값을 낸다
(다리가 몸 한가운데 수직으로 서 있다고 가정한다) — 그래서 별도 경로가 필요하다.

무엇을 재고 무엇을 안 재는지 분명히 한다.
  · **잰다**: 발 네 개의 바닥 위치, 앞뒤 방향, 다리가 몸통에 합쳐지는 높이(배). 전부 메시 증거다.
  · **안 잰다**: 무릎·발목. 이 관절들은 몸 표면이 아니라 살 안쪽에 있어서 표면 추적으로는 닿지 않는다
    (실측: 늑대 고관절은 키의 66% 높이인데 다리가 합쳐지는 배는 그보다 한참 아래다). 대신
    **Rigify 늑대 메타리그의 다리 비율**을 쓴다 — 지어낸 '키의 몇 %' 상수가 아니라 실제 늑대를 본뜬
    해부 모델이고, 발을 우리가 잰 자리에 심으면 그 사이 관절은 비율대로 따라온다.
"""
from mathutils import Vector


def front_dir_from_mesh(vs, zmin, H):
    """사족의 앞쪽 방향(-1 이면 앞이 -Y). 머리는 몸의 한쪽 끝 위에 붙으므로 위쪽 점들의 y 무게중심이
    몸 전체 평균에서 치우친 쪽이 앞이다. 자산 10종 정답 뼈대와 대조해 10/10 맞은 규칙이다
    (사람 규칙인 '발이 앞으로 뻗는다'는 네 발 동물에선 앞뒤 양쪽에 발이 있어 흔들린다 — 시바견이 뒤집혔다)"""
    top = [v for v in vs if v.z > zmin + H * 0.75]
    if len(top) < 8:
        return None
    mean_y = sum(v.y for v in vs) / len(vs)
    return -1.0 if (sum(v.y for v in top) / len(top)) < mean_y else 1.0


def _centroid(pts):
    return sum(pts, Vector()) / len(pts)


def _split_y(pts, min_gap):
    """y 로 정렬해 가장 크게 벌어진 곳에서 둘로 가른다. 벌어짐이 min_gap 미만이면 실패(None)"""
    ys = sorted(v.y for v in pts)
    if len(ys) < 4:
        return None
    gap, gi = max(((ys[i + 1] - ys[i], i) for i in range(len(ys) - 1)))
    if gap < min_gap:
        return None
    cut = (ys[gi] + ys[gi + 1]) / 2
    lo = [v for v in pts if v.y <= cut]
    hi = [v for v in pts if v.y > cut]
    return (lo, hi) if len(lo) >= 3 and len(hi) >= 3 else None


def _belly_z(vs, zmin, ztop, gap_thr, slices=24):
    """다리가 몸통에 합쳐지는 높이. 각 높이에서 점들을 y 로 끊어 구간이 하나가 되는 첫 높이다
    (앞다리와 뒷다리 사이가 뚫려 있는 동안은 구간이 둘 이상이다)"""
    for i in range(slices):
        z0 = zmin + (ztop - zmin) * i / slices
        z1 = zmin + (ztop - zmin) * (i + 1) / slices
        sel = [v for v in vs if z0 <= v.z < z1]
        if len(sel) < 6:
            continue
        ys = sorted(v.y for v in sel)
        segs = []
        for y in ys:
            if segs and y - segs[-1][1] <= gap_thr: segs[-1][1] = y
            else: segs.append([y, y])
        if len(segs) < 2:
            return round((z0 + z1) / 2, 3)
    return None


def quad_landmarks(vs, st, spacing):
    """사족 랜드마크. 못 찾은 항목은 넣지 않고 notes 에 이유를 남긴다(추측해서 채우지 않는다)"""
    zmin = st["min"][2]
    H = st["height"]
    notes = []
    gap_thr = max(spacing * 2.5, H * 0.005)

    # 앞뒤 방향: 머리는 몸의 한쪽 끝 위에 붙는다 → 위쪽 점들의 평균 y 가 몸 전체 평균에서 치우친 쪽이 앞이다.
    # 두 번째 근거(가장 높은 점)와 어긋나면 방향을 못 믿는다는 뜻이므로 notes 에 남긴다
    front_dir = front_dir_from_mesh(vs, zmin, H)
    if front_dir is None:
        notes.append("앞뒤 방향: 위쪽 점이 부족하다")
        front_dir = -1.0
    else:
        mean_y = sum(v.y for v in vs) / len(vs)
        highest = max(vs, key=lambda v: v.z)   # 두 번째 근거. 어긋나면 방향을 못 믿는다는 뜻이라 남긴다
        if (-1.0 if highest.y < mean_y else 1.0) != front_dir:
            notes.append("앞뒤 방향 근거가 엇갈린다(위쪽 무게중심 ↔ 최고점)")

    # 발 네 개: 바닥 근처 점을 좌우로 가르고, 각 쪽을 앞뒤로 다시 가른다
    slab = [v for v in vs if v.z < zmin + H * 0.12]
    feet = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        pts = [v for v in slab if v.x * sx > spacing * 0.5]
        if len(pts) < 8:
            notes.append(f"{side}: 바닥 점이 부족하다")
            continue
        pair = _split_y(pts, H * 0.04)
        if pair is None:
            notes.append(f"{side}: 앞뒤 다리가 안 갈라진다")
            continue
        lo, hi = pair
        front, hind = (lo, hi) if front_dir < 0 else (hi, lo)
        for which, grp in (("front", front), ("hind", hind)):
            c = _centroid(grp)
            feet[f"{which}_{side}"] = [round(c.x, 3), round(c.y, 3), round(zmin, 3)]

    out = {"front_dir": front_dir, "feet": feet, "notes": notes, "ok": len(feet) == 4}
    belly = _belly_z(vs, zmin, zmin + H * 0.9, gap_thr)
    if belly is not None:
        out["belly_z"] = belly
    # 등 높이: 고관절·어깨 자리(앞뒤 y)에서 몸의 윗면이 얼마나 높은가. 총키로 재면 목 긴 알파카·뿔 달린 사슴이 어긋난다
    # (정답 11종 대조: 고관절/등 = 0.79±0.06 으로 고관절/키 0.59±0.08 보다 두 배 일정하다). 다리 사슬 높이의 기준이 된다.
    # 꼭대기 한 점 대신 띠 안 상위 5% 지점을 쓴다 — 뿔·귀·등의 돌기 하나에 휘둘리지 않게
    if len(feet) == 4:
        hy = (feet["hind_L"][1] + feet["hind_R"][1]) / 2
        fy = (feet["front_L"][1] + feet["front_R"][1]) / 2
        bl = hy - fy
        # 띠 위치·폭은 정답 대조로 비율을 잰 그 조건 그대로여야 한다(띠가 달라지면 등 높이가 달라져 비율이 안 맞는다)
        for tag, y in (("back_hind_z", hy - 0.15 * bl), ("back_front_z", fy + 0.10 * bl)):
            band = sorted(v.z for v in vs if abs(v.y - y) < abs(bl) * 0.10)
            if len(band) >= 20:
                out[tag] = round(band[int(len(band) * 0.95)], 4)
            else:
                notes.append(f"{tag}: 띠 안 점이 부족하다")
        # 앞다리 기울기: 앞발 기둥이 위로 갈수록 뒤로 얼마나 기우는가(몸 길이 비). 개과는 팔꿈치가 높고 다리가 뒤로 꺾여 0.089~0.133,
        # 발굽 동물(소·말·사슴·알파카)은 수직 기둥이라 -0.05~0.066 — 자산 11종에서 0.08 을 경계로 완전히 갈린다.
        # 이 한 값으로 팔꿈치 높이 비율과 앞다리 굽힘을 무리별로 고를 수 있다(메타리그 한 종 비율의 한계를 메시 측정으로 넘는다)
        fx = abs(feet["front_L"][0]); lean = None
        for f in (0.15, 0.20, 0.25, 0.30):
            z = zmin + f * H
            col = [v for v in vs if abs(abs(v.x) - fx) < fx * 0.6 and abs(v.y - fy) < abs(bl) * 0.25 and abs(v.z - z) < H * 0.02]
            if len(col) >= 6:
                v_ = (sum(v.y for v in col) / len(col) - fy) / bl
                lean = v_ if lean is None else max(lean, v_)
        if lean is not None:
            out["front_lean"] = round(lean, 4)
        else:
            notes.append("앞다리 기울기: 기둥 점이 부족하다")
    return out
