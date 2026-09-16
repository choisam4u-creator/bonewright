"""1단계 분석(토큰 0): 메시 크기·대칭·높이띠별 폭에서 관절 후보(어깨·골반·무릎·손)를 추정한다."""
import bpy
from mathutils import Vector
from _common import args, done, fresh, import_mesh, mesh_stats, topology, IMPORT_INFO
A = args(); fresh()
QUAD = A.get("preset") == "quadruped"
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"), quad=QUAD); st = mesh_stats(obj); st.update(topology(obj)); st["import"] = dict(IMPORT_INFO)
# 팔에 붙은 부품(bw_attachment 그룹)은 랜드마크 계산에서 뺀다 — 스키닝에는 그대로 들어간다
_att = obj.vertex_groups.get("bw_attachment"); _ai = _att.index if _att else None
vs = [obj.matrix_world @ v.co for v in obj.data.vertices if _ai is None or not any(g.group == _ai for g in v.groups)]
st["attachment_verts"] = len(obj.data.vertices) - len(vs)
if st["attachment_verts"]:   # 키·상자도 몸 기준으로(사슴뿔을 키에 넣으면 사족 정규화가 통째로 밀린다). 전체 상자는 full_bbox 에 남긴다
    st["full_bbox"] = {"min": st["min"], "max": st["max"], "height": st["height"]}
    xs_, ys_, zs_ = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
    st["min"], st["max"] = [min(xs_), min(ys_), min(zs_)], [max(xs_), max(ys_), max(zs_)]
    st["height"], st["width"], st["depth"] = max(zs_) - min(zs_), max(xs_) - min(xs_), max(ys_) - min(ys_)
zmin, zmax = st["min"][2], st["max"][2]; H = st["height"]
el0 = sorted((obj.data.vertices[e.vertices[0]].co - obj.data.vertices[e.vertices[1]].co).length for e in obj.data.edges[:4000])
spacing_gap = (el0[len(el0) // 2] if el0 else 0.01) * 1.5
bands = 40; rows = []
for i in range(bands):
    z0, z1 = zmin + H * i / bands, zmin + H * (i + 1) / bands
    sel = [v for v in vs if z0 <= v.z < z1]
    if not sel:
        rows.append({"z": round((z0 + z1) / 2, 3), "width": 0, "left": 0, "right": 0, "gap": 0}); continue
    xs = sorted(v.x for v in sel)
    # 다리가 갈라지는 띠: x 분포의 가운데 빈 구간 크기
    gap = 0.0
    if len(xs) > 4:
        mid = [x for x in xs if abs(x) < st["width"] / 2]
        neg = [x for x in xs if x < 0]; pos = [x for x in xs if x > 0]
        if neg and pos: gap = min(pos) - max(neg)
    rows.append({"z": round((z0 + z1) / 2, 3), "width": round(xs[-1] - xs[0], 3), "left": round(xs[0], 3), "right": round(xs[-1], 3), "gap": round(max(gap, 0), 3)})
sym = sum(abs(r["left"] + r["right"]) for r in rows) / max(1, len(rows))
fallbacks = []   # 메시 증거로 못 찾아 인체 비율로 때운 항목(보고서에 남긴다)
# 몸통 반폭: 각 띠에서 x 를 정렬해 일정 간격 이상 벌어진 곳을 끊으면 구간이 나온다. 0 을 품은 가운데 구간이 몸통, 바깥 구간이 팔이다.
# 끊는 간격은 정점 간격(중앙값 변 길이)의 2.5배 이상이어야 한다. 복셀 리메시처럼 정점이 3cm 격자면 2cm 기준으로는 모든 정점이 따로 끊긴다
ymin_all = min(v.y for v in vs)
el = sorted((obj.data.vertices[e.vertices[0]].co - obj.data.vertices[e.vertices[1]].co).length for e in obj.data.edges[:4000])
spacing = el[len(el) // 2] if el else 0.01; gap_thr = max(0.02, spacing * 2.5)
def segments(z0, z1):
    xs = sorted(v.x for v in vs if z0 <= v.z < z1); segs = []
    for x in xs:
        if segs and x - segs[-1][1] <= gap_thr: segs[-1][1] = x
        else: segs.append([x, x])
    return segs
for r in rows:
    segs = segments(r["z"] - H / bands / 2, r["z"] + H / bands / 2)
    mid = [sg for sg in segs if sg[0] <= 0 <= sg[1]]
    # 좌우로 갈라진 띠(=다리 사이) 판정: 몸 한가운데(x=0)를 앞뒤로 관통하는 광선을 쏴 본다.
    # 다리 사이는 뻥 뚫려 있어 아무것도 안 맞고, 몸통은 저폴리라 단면에 틈이 보여도 앞·뒤 벽에 맞는다.
    # (틈 크기로만 재면 성긴 몸통 단면의 3~4cm 틈과 진짜 가랑이 틈을 구별할 수 없다 — 벤치마크로 확인)
    hit, _, _, _ = obj.ray_cast(Vector((0.0, ymin_all - 0.1, r["z"])), Vector((0.0, 1.0, 0.0)))
    r["center_open"] = not hit
    r["center_split"] = bool(r["center_open"] and r["left"] < -spacing and r["right"] > spacing)
    if not mid: mid = [min(segs, key=lambda sg: min(abs(sg[0]), abs(sg[1])))] if segs else []
    r["torso_hw"] = round((mid[0][1] - mid[0][0]) / 2, 3) if mid else 0
    r["arm_segments"] = len(segs) - 1
# 가랑이 = 바닥에서 이어지는 "갈라진 띠 구간"의 꼭대기. 다리는 바닥까지 계속 갈라져 있으므로,
# 어떤 띠까지 볼 때 갈라진 띠 비율이 60% 아래로 떨어지면 거기서 끊는다. 저폴리 단면이 한두 띠 튀어도 견딘다(높이 상수 없음)
split = [r for r in rows if r["center_split"]]
crotch = None
# 바로 아래 4개 띠 중 60% 이상이 함께 갈라져 있어야 인정한다. 저폴리 단면이 가슴에서 한 띠만 갈라져 보이는
# 가짜 신호를 막고, 허벅지가 잠깐 붙었다가 다시 갈라지는 캐릭터도 살린다(바닥부터 누적 비율은 그걸 못 살렸다)
for i, r in enumerate(rows):
    if not r["center_split"]: continue
    # 바로 아래 두 띠도 갈라져 있어야 한다. 허리에서 잘린 상반신 모델은 속이 빈 통이라 맨 아래 한 띠만
    # 뚫린 것으로 읽히는데, 그걸 가랑이로 잡으면 다리 관절이 전부 바닥에 몰려 Rigify 가 실패한다(벤치마크로 확인)
    if i < 2 or not (rows[i - 1]["center_split"] and rows[i - 2]["center_split"]): continue
    win = rows[max(0, i - 4):i]
    if sum(1 for w in win if w["center_split"]) / len(win) >= 0.6:
        crotch = r
if crotch is None: fallbacks.append("crotch")
cz = crotch["z"] if crotch else zmin + H * 0.47

def torso_percentile(lo, hi):
    """구간 안 띠들의 몸통 반폭 하위 25%(팔이 붙는 띠는 넓게 나오므로 중앙값 대신 하위값)"""
    v = sorted(r["torso_hw"] for r in rows if lo < r["z"] < hi and r["torso_hw"] > 0)
    return round(v[len(v) // 4], 3) if v else round(st["width"] / 6, 3)
torso_hw = torso_percentile(cz, zmax)   # 1차: 가랑이 위 전체
# 어깨 기본값: 팔을 못 찾는 메시(사족·상자·팔 없는 캐릭터)에서도 죽지 않게 가랑이 위에서 가장 넓은 띠를 쓴다.
# v0.2 에서 이 기본값이 빠져 여우·RiggedFigure·RobotExpressive 분석이 NameError 로 죽었다(벤치마크가 잡음)
shoulder = max([r for r in rows if r["z"] > cz] or rows, key=lambda r: r["width"])
# 팔이 있는 띠: 몸통 밖 구간이 따로 있거나(A 포즈), 한 덩어리지만 몸통보다 2.6배 넓다(T 포즈, 어깨 높이)
arm_rows = [r for r in rows if r["z"] > cz and (r["arm_segments"] > 0 or r["width"] > torso_hw * 2 * 2.6)]
tip = max(arm_rows, key=lambda r: r["right"]) if arm_rows else shoulder
if arm_rows:   # 어깨 높이는 팔이 처음 나타나는(가장 높은) 띠
    shoulder = max(arm_rows, key=lambda r: r["z"])
# 팔 중심선: 몸통 밖 정점을 어깨점→팔끝 방향으로 8칸에 나눠 칸마다 무게중심·반지름을 잰다(팔꿈치·손목을 중심선 위에 두기 위한 표본)
def arm_axis(sign):
    pts = [v for v in vs if v.x * sign > torso_hw + spacing * 0.5 and v.z > cz]
    if len(pts) < 20: return []
    S = Vector((sign * torso_hw, sum(v.y for v in pts) / len(pts), shoulder["z"])); Tp = Vector((sign * tip["right"], S.y, tip["z"]))
    out = []
    for _ in range(2):   # 2회: 첫 결과의 양 끝으로 방향을 다시 잡으면 칸이 팔에 수직에 가까워진다
        d = (Tp - S); Ln = d.length; d.normalize(); out = []
        # 몸통 옆면 정점이 팔 칸에 섞이지 않게 어깨→팔끝 직선에서 길이의 15% 이상 떨어진 점은 뺀다
        near = [v for v in pts if ((v - S) - (v - S).dot(d) * d).length < max(0.06, Ln * 0.15)]
        for i in range(8):
            t0, t1 = Ln * i / 8, Ln * (i + 1) / 8
            sel = [v for v in near if t0 <= (v - S).dot(d) < t1]
            if len(sel) < 6: continue
            c = sum(sel, Vector()) / len(sel)
            off = [((v - c) - (v - c).dot(d) * d).length for v in sel]; med = sorted(off)[len(off) // 2]
            keep = [v for v, o in zip(sel, off) if o <= med * 2.0 + 1e-6]   # 칸 안의 이상점(중앙값의 2배 밖) 제거 후 다시 잰다
            if len(keep) >= 6:
                sel = keep; c = sum(sel, Vector()) / len(sel)
            rad = sum(((v - c) - (v - c).dot(d) * d).length for v in sel) / len(sel)
            out.append([round(c.x, 3), round(c.y, 3), round(c.z, 3), round(rad, 3)])
        if len(out) < 3: return out
        S, Tp = Vector(out[0][:3]), Vector(out[-1][:3])
    # 반지름이 표본 중앙값의 2배를 넘는 표본은 몸통이 섞인 것 → 뺀다
    rmed = sorted(p[3] for p in out)[len(out) // 2]
    out = [p for p in out if p[3] <= rmed * 2.0]
    if len(out) < 3: return out
    # 어깨 관절: 첫 표본에서 팔 안쪽으로 그 표본 굵기의 1배만 되짚는다.
    # 예전에는 몸통 폭까지 밀어 넣었는데, 정답 뼈대 대조에서 그게 오히려 6cm 오차를 만드는 걸 확인했다(bench 2026-09-15).
    if abs(out[1][0] - out[0][0]) > 1e-4:
        d = [out[1][i] - out[0][i] for i in range(3)]
        ln = sum(v * v for v in d) ** 0.5
        k = (out[0][3] * 1.0) / ln if ln > 1e-6 else 0
        out.insert(0, [round(out[0][i] - d[i] * k, 3) for i in range(3)] + [out[0][3]])
    return out
axes = {"arm_axis_L": arm_axis(1), "arm_axis_R": arm_axis(-1)}
# 어깨 관절 높이는 중심선 첫 표본(팔 뿌리)에서 잰다. 실루엣 띠로는 팔이 몸통과 붙는 높이밖에 못 잡는다
roots = [ax[0] for ax in axes.values() if ax]
if roots:
    sz = sum(p[2] for p in roots) / len(roots)
    shoulder = min(rows, key=lambda r: abs(r["z"] - sz)); shoulder = dict(shoulder, z=round(sz, 3))
# 2차 몸통 반폭: 어깨 아래~가랑이 위 구간만 본다(머리·팔이 섞이지 않는다)
torso_hw = torso_percentile(cz, shoulder["z"])

# 다리 중심선: 팔과 같은 방식으로 가랑이 아래를 세로로 8칸 나눠 칸마다 무게중심·반지름·앞뒤 길이를 잰다.
# 무릎·발목을 "키의 몇 %" 가 아니라 이 프로필의 모양으로 찾는다
def leg_axis(sign, lo=None, hi=None):
    pts = [v for v in vs if v.z < cz and v.x * sign > spacing * 0.5]
    if len(pts) < 20: return []
    lo = min(v.z for v in pts) if lo is None else lo
    hi = cz if hi is None else min(hi, cz); out = []
    for i in range(8):
        z0, z1 = lo + (hi - lo) * i / 8, lo + (hi - lo) * (i + 1) / 8
        sel = [v for v in pts if z0 <= v.z < z1]
        if len(sel) < 6: continue
        c = sum(sel, Vector()) / len(sel)
        rad = sum(((v - c) - Vector((0, 0, v.z - c.z))).length for v in sel) / len(sel)
        out.append([round(c.x, 3), round(c.y, 3), round(c.z, 3), round(rad, 3), round(max(v.y for v in sel) - min(v.y for v in sel), 3)])
    return out
legs = {"leg_axis_L": leg_axis(1), "leg_axis_R": leg_axis(-1)}   # 1차: 발목 찾기용(발 포함)
prof = legs["leg_axis_L"] or legs["leg_axis_R"]

# 다리 중심선을 못 찾은 메시(로봇처럼 다리가 떨어진 상자거나 실루엣에서 몸통과 붙어 보이는 경우)라도,
# **바닥 근처는 거의 언제나 두 발로 갈라져 있다**. 맨 아래 띠에서 x 를 묶어 좌우 한 덩어리씩이면 그게 두 발이다.
# 이 값은 거절 게이트를 통과시키는 데 쓰지 않는다(여전히 '중심선 없음'으로 막힌다) — 손으로 고칠 출발점을 낫게 하는 용도다
foot_split = None
if not (legs["leg_axis_L"] and legs["leg_axis_R"]):
    lowest = [v for v in vs if v.z < zmin + H * 0.08]
    xs = sorted(v.x for v in lowest)
    if len(xs) >= 12:
        gs, cur = [], [xs[0]]
        for x in xs[1:]:
            if x - cur[-1] > gap_thr * 2: gs.append(cur); cur = [x]
            else: cur.append(x)
        gs.append(cur)
        gs = [g for g in gs if len(g) >= 6]
        if len(gs) == 2 and (gs[0][0] + gs[0][-1]) / 2 < 0 < (gs[1][0] + gs[1][-1]) / 2:
            fx = round((gs[1][0] + gs[1][-1]) / 2, 3)          # 왼발(+X) 중심
            band = [v for v in lowest if v.x > 0] or lowest
            foot_split = {"x": fx, "top_z": round(max(v.z for v in band), 3)}
            fallbacks.append("leg_axis(발 위치만 잼)")
            # 관절 높이: 실루엣이 다리와 몸통을 못 가르는 메시(로봇)라도, **조각으로 만든 모델이면 조각 자체가 마디다**.
            # 발 x 와 같은 줄에 있는 느슨한 조각들을 높이로 묶으면 그 뭉치 중심이 발목·무릎·고관절이다
            # (RobotExpressive 실측 0.111 / 0.900 / 1.672 — 정답 0.025 / 0.935 / 1.537, 키의 2.2 / 0.9 / 3.4%)
            par = list(range(len(obj.data.vertices)))
            def _root(i):
                while par[i] != i: par[i] = par[par[i]]; i = par[i]
                return i
            for e in obj.data.edges:
                a, b = _root(e.vertices[0]), _root(e.vertices[1])
                if a != b: par[a] = b
            isl = {}
            for i in range(len(obj.data.vertices)):
                isl.setdefault(_root(i), []).append(i)
            leg_parts = []
            for members in isl.values():
                if len(members) < 6: continue
                pl = [vs[i] for i in members]
                cx = sum(p.x for p in pl) / len(pl); cz_ = sum(p.z for p in pl) / len(pl)
                if fx * 0.45 < abs(cx) < fx * 1.6 and cz_ < zmin + H * 0.78:   # 발과 같은 줄
                    leg_parts.append((cz_, len(members)))
            leg_parts.sort()
            clusters, cur_ = [], []
            for cz_, n in leg_parts:   # 높이로 묶는다: 키의 8% 이상 벌어지면 다른 마디
                if cur_ and cz_ - cur_[-1][0] > H * 0.08: clusters.append(cur_); cur_ = []
                cur_.append((cz_, n))
            if cur_: clusters.append(cur_)
            zs_ = [round(sum(c * n for c, n in g) / sum(n for _, n in g), 3) for g in clusters][:3]   # 아래 3뭉치 = 발목·무릎·고관절
            if len(zs_) >= 2:
                foot_split["ankle_z"], foot_split["hip_z"] = zs_[0], zs_[-1]
                foot_split["knee_z"] = zs_[1] if len(zs_) == 3 else round(zs_[0] + (zs_[-1] - zs_[0]) * 0.5, 3)
                foot_split["leg_parts"] = len(leg_parts)
                # 가운데 줄(몸통) 조각도 같은 방식으로 묶는다: 골반·가슴·머리가 뭉치로 나온다
                # (로봇 실측 1.312 / 2.101 / 3.045 — 정답 Hips 1.344 / Torso 2.148 / Head 3.038)
                mid_parts = []
                for members in isl.values():
                    if len(members) < 6: continue
                    pl = [vs[i] for i in members]
                    cx = sum(p.x for p in pl) / len(pl); cz_ = sum(p.z for p in pl) / len(pl)
                    if abs(cx) < fx * 0.45: mid_parts.append((cz_, len(members)))
                mid_parts.sort()
                mc, cur_ = [], []
                for cz_, n in mid_parts:
                    if cur_ and cz_ - cur_[-1][0] > H * 0.08: mc.append(cur_); cur_ = []
                    cur_.append((cz_, n))
                if cur_: mc.append(cur_)
                cz_list = [round(sum(c * n for c, n in g) / sum(n for _, n in g), 3) for g in mc]
                if cz_list:
                    foot_split["center_z"] = cz_list
                    foot_split["pelvis_z"] = min(cz_list, key=lambda z: abs(z - foot_split["hip_z"]))
                # 팔 높이: **가장 멀리 나간 조각**(손)이 팔의 높이를 알려 준다. 실루엣 팔 중심선은 머리 둘레의
                # 장식 고리를 팔로 오해하기 쉽다(로봇: 3.23m 를 어깨로 잡았다. 정답 2.44m, 손 조각은 2.473m)
                far = None
                for members in isl.values():
                    if len(members) < 6: continue
                    pl = [vs[i] for i in members]
                    cx = sum(p.x for p in pl) / len(pl)
                    if abs(cx) > fx * 1.2 and (far is None or abs(cx) > far[0]):
                        far = (abs(cx), sum(p.z for p in pl) / len(pl), max(abs(p.x) for p in pl))
                if far:
                    az_ = round(far[1], 3)
                    near = min(rows, key=lambda r: abs(r["z"] - az_))
                    foot_split["arm_z"] = az_
                    foot_split["arm_tip_x"] = round(far[2], 3)
                    # 어깨의 좌우 거리는 최소한 다리 줄만큼은 된다 — 그 높이의 몸통 반폭이 더 좁게 읽히면 다리 줄을 쓴다
                    foot_split["arm_root_x"] = round(max(near.get("torso_hw") or 0.0, fx), 3)

# 발목 = 발 덩어리의 꼭대기. "발"은 다리 중심선에서 앞뒤(y)로 굵기의 1.5배 넘게 튀어나온 점들이다(발끝·발등).
# 부츠를 신어도 발끝은 앞으로 튀어나오므로 신발 종류와 무관하다
def radius_at(z):
    if not prof: return 0.0
    lo, hi = prof[0], prof[-1]
    if z <= lo[2]: return lo[3]
    if z >= hi[2]: return hi[3]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        if a[2] <= z <= b[2]:
            t = (z - a[2]) / (b[2] - a[2]) if b[2] > a[2] else 0
            return a[3] + (b[3] - a[3]) * t
    return hi[3]
def center_y_at(z):
    if not prof: return 0.0
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        if a[2] <= z <= b[2]:
            t = (z - a[2]) / (b[2] - a[2]) if b[2] > a[2] else 0
            return a[1] + (b[1] - a[1]) * t
    return prof[-1][1]
foot_z = []
for v in vs:
    if v.z >= cz: continue
    r = radius_at(v.z)
    if r > 0 and abs(v.y - center_y_at(v.z)) > r * 1.5: foot_z.append(v.z)
foot_z.sort()
ankle_z = round(foot_z[int(len(foot_z) * 0.97)], 3) if len(foot_z) >= 10 else None
if ankle_z is None or ankle_z > cz * 0.5:
    ankle_z = zmin + H * 0.05; fallbacks.append("ankle")   # 최후 폴백(인체 비율)

# 무릎 = 엉덩관절과 발목의 중간. 이건 사람 키 비례가 아니라 "두 마디 팔다리는 위·아래 마디 길이가 비슷하다"는 구조 사실이다
# (넓다리뼈 ≈ 정강뼈). 그 근처에서 다리가 가장 잘록한 칸이 있으면 그쪽으로 붙인다
knee_z = None   # 엉덩관절 계산 뒤에 채운다

# 엉덩관절: 가랑이보다 허벅지 굵기만큼 위(넙다리뼈 머리 위치). 키 비례가 아니라 다리 굵기 기준이다
thigh_r = max((sg[3] for sg in prof if sg[2] > (ankle_z + cz) / 2), default=0)
hip_z = round(cz + thigh_r, 3) if thigh_r else round(cz + H * 0.05, 3)
if not thigh_r: fallbacks.append("hip")

# 2차 다리 중심선: 발목~가랑이 구간만 담고(발의 앞쪽 치우침이 발목 좌표를 끌어당기는 걸 막는다),
# 마지막 두 표본의 방향으로 엉덩관절 높이까지 한 점을 연장한다(모델이 허벅지를 놓을 근거가 생긴다)
def leg_axis_fit(sign):
    out = leg_axis(sign, ankle_z, cz)
    if len(out) >= 2 and hip_z > out[-1][2]:
        a, b = out[-2], out[-1]
        # 기울기로 늘리면 표본 잡음이 증폭된다(실측: 엉덩이 x 가 0.124 → 0.173 으로 튐). 위쪽 다리는 거의 수직이므로 마지막 두 표본의 평균 위치를 쓴다
        out.append([round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3), round(hip_z, 3), b[3], b[4]])
    return out
legs = {"leg_axis_L": leg_axis_fit(1), "leg_axis_R": leg_axis_fit(-1)}

leg_len = hip_z - ankle_z
mid_knee = (hip_z + ankle_z) / 2
near = [sg for sg in prof if abs(sg[2] - mid_knee) < leg_len * 0.15]
if len(near) >= 3:   # 중간 근처에서 가장 가는 칸(무릎)으로 보정
    knee_z = round(min(near, key=lambda sg: sg[3])[2], 3)
else:
    knee_z = round(mid_knee, 3)
    if not prof: fallbacks.append("knee")

# 목: 어깨 위에서 몸통 반폭이 가장 좁아지는 띠. 머리가 크면 그 위에서 다시 넓어지므로 전환점이 곧 목이다
# 목 = 어깨 위에서 몸통 반폭이 가장 좁은 띠. 정수리는 항상 좁아지므로 맨 위 두 띠는 후보에서 뺀다.
# 머리가 크면 목 위에서 폭이 다시 넓어지고, 그 최소점이 곧 목이다(키의 몇 % 라는 가정 없음)
above = [r for r in rows if r["z"] > shoulder["z"] and r["torso_hw"] > 0]
neck_z = None
if len(above) >= 4:
    cand = above[:-2]
    m = min(cand, key=lambda r: r["torso_hw"])
    if any(r["torso_hw"] > m["torso_hw"] * 1.1 for r in above if r["z"] > m["z"]):   # 그 위에 머리 덩어리가 있어야 목이다
        neck_z = m["z"]
if neck_z is None:
    neck_z = round(zmax - H * 0.12, 3); fallbacks.append("neck")

head_len = round(zmax - neck_z, 3)
# 머리 폭: 목 위 띠들의 최대 몸통 반폭(목 추정이 폴백이면 이 값도 못 믿는다)
upper_hw = max((r["torso_hw"] for r in rows if r["z"] > neck_z), default=0)
# 치비 판정은 목을 메시 증거로 찾았을 때만 한다. 못 찾았으면 "모름"(None) — 추측해서 단정하지 않는다
neck_ok = "neck" not in fallbacks
chibi = bool(head_len / H > 0.35) if neck_ok else None
# 분석 신뢰도: 하나라도 걸리면 결과를 믿지 말고 --pin 으로 관절을 고정하라고 알린다
suspect = []
if not neck_ok: suspect.append("목 추정 실패")
if not (axes["arm_axis_L"] and axes["arm_axis_R"]): suspect.append("팔 중심선 없음")
if not (legs["leg_axis_L"] and legs["leg_axis_R"]): suspect.append("다리 중심선 없음")
if fallbacks: suspect.append("인체 비율 폴백: " + ",".join(fallbacks))
if chibi: suspect.append("치비 비율(머리가 키의 35% 초과)")
land = {"height": round(H, 3), "ground_z": round(zmin, 3), "top_z": round(zmax, 3),
        "shoulder_z": shoulder["z"], "shoulder_halfwidth": round(shoulder["width"] / 2, 3),
        "crotch_z": round(cz, 3), "hip_z": hip_z, "knee_z": round(knee_z, 3), "ankle_z": round(ankle_z, 3),
        "head_top_z": round(zmax, 3), "neck_z": round(neck_z, 3), "head_length": head_len,
        "head_ratio": round(head_len / H, 3), "head_halfwidth": round(upper_hw, 3), "chibi": chibi, "suspect": suspect,
        "neck_from": "fallback" if "neck" in fallbacks else "evidence",
        "torso_halfwidth": torso_hw, "arm_tip_x": tip["right"], "arm_tip_z": tip["z"],
        "vertex_spacing": round(spacing, 4), "symmetry_error": round(sym, 3),
        "pose_guess": "A" if tip["z"] < shoulder["z"] - (shoulder["z"] - cz) * 0.15 else "T",
        "ratio_fallbacks": fallbacks, "foot_split": foot_split, **axes, **legs}
if QUAD:   # 사족은 사람용 관절 추정이 무의미하다(다리가 몸 한가운데 수직으로 섰다고 본다) → 발 위치를 따로 잰다
    from _quad import quad_landmarks
    land["quad"] = quad_landmarks(vs, st, spacing)
    if not land["quad"]["ok"]:
        land["suspect"].append("사족 발 검출 실패: " + "; ".join(land["quad"]["notes"])[:80])
bpy.ops.wm.save_as_mainfile(filepath=A["blend"])
done({"stats": st, "bands": rows, "landmarks": land, "blend": A["blend"]}, A["result"])
