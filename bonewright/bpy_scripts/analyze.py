"""1단계 분석(토큰 0): 메시 크기·대칭·높이띠별 폭에서 관절 후보(어깨·골반·무릎·손)를 추정한다."""
import bpy
from mathutils import Vector
from _common import args, done, fresh, import_mesh, mesh_stats, topology, IMPORT_INFO
A = args(); fresh()
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto")); st = mesh_stats(obj); st.update(topology(obj)); st["import"] = dict(IMPORT_INFO)
vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
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
# 후보: 가장 넓은 띠(상단 45% 안) = 어깨/팔 높이, 갈라짐이 시작되는 띠 = 가랑이
top = [r for r in rows if r["z"] > zmin + H * 0.55]
shoulder = max(top, key=lambda r: r["width"]) if top else rows[-1]
# 가랑이: 실루엣이 둘로 갈라진 띠 중 가장 높은 것(아래에서 첫 띠를 잡으면 두 발 사이 틈을 가랑이로 오인한다)
split = [r for r in rows if r["gap"] > max(0.02, spacing_gap) and r["z"] < zmin + H * 0.6]   # 격자 간격만큼의 틈은 갈라진 게 아니다
crotch = max(split, key=lambda r: r["z"]) if split else None
sym = sum(abs(r["left"] + r["right"]) for r in rows) / max(1, len(rows))
# 몸통 반폭: 각 띠에서 x 를 정렬해 0.02 이상 벌어진 곳을 끊으면 구간이 나온다. 0 을 품은 가운데 구간이 몸통, 바깥 구간이 팔이다
cz = crotch["z"] if crotch else zmin + H * 0.47
# 끊는 간격은 정점 간격(중앙값 변 길이)의 2.5배 이상이어야 한다. 복셀 리메시처럼 정점이 3cm 격자면 2cm 기준으로는 모든 정점이 따로 끊긴다
el = sorted((obj.data.vertices[e.vertices[0]].co - obj.data.vertices[e.vertices[1]].co).length for e in obj.data.edges[:4000])
spacing = el[len(el) // 2] if el else 0.01; gap_thr = max(0.02, spacing * 2.5)
def segments(z0, z1):
    xs = sorted(v.x for v in vs if z0 <= v.z < z1); segs = []
    for x in xs:
        if segs and x - segs[-1][1] <= gap_thr: segs[-1][1] = x
        else: segs.append([x, x])
    return segs
center_hw = []
for r in rows:
    segs = segments(r["z"] - H / bands / 2, r["z"] + H / bands / 2)
    mid = [sg for sg in segs if sg[0] <= 0 <= sg[1]] or ([min(segs, key=lambda sg: min(abs(sg[0]), abs(sg[1])))] if segs else [])
    r["torso_hw"] = round((mid[0][1] - mid[0][0]) / 2, 3) if mid else 0
    r["arm_segments"] = len(segs) - 1
    if cz + H * 0.05 < r["z"] < zmin + H * 0.85 and r["torso_hw"] > 0: center_hw.append(r["torso_hw"])
center_hw.sort(); torso_hw = round(center_hw[len(center_hw) // 4], 3) if center_hw else round(st["width"] / 6, 3)   # 하위 25%: 팔이 붙는 띠는 넓게 나온다
# 팔이 있는 띠: 몸통 밖 구간이 따로 있거나(A 포즈), 한 덩어리지만 몸통보다 2.6배 넓다(T 포즈, 어깨 높이)
arm_rows = [r for r in rows if zmin + H * 0.45 < r["z"] < zmax - H * 0.08 and (r["arm_segments"] > 0 or r["width"] > torso_hw * 2 * 2.6)]
tip = max(arm_rows, key=lambda r: r["right"]) if arm_rows else shoulder
if arm_rows:   # 어깨 높이는 팔이 처음 나타나는(가장 높은) 띠
    shoulder = max(arm_rows, key=lambda r: r["z"])
# 팔 중심선: 몸통 밖 정점을 어깨점→팔끝 방향으로 8칸에 나눠 칸마다 무게중심·반지름을 잰다(팔꿈치·손목을 중심선 위에 두기 위한 표본)
def arm_axis(sign):
    pts = [v for v in vs if v.x * sign > torso_hw + spacing * 0.5 and v.z > cz + H * 0.05]
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
    # 첫 표본은 팔 뿌리 바깥의 무게중심이라 어깨 관절보다 바깥에 있다. 앞 두 표본을 몸통 폭의 0.9배 지점까지 되짚어 어깨 관절 표본을 앞에 붙인다
    if abs(out[1][0] - out[0][0]) > 1e-4:
        k = (out[0][0] - sign * torso_hw * 0.9) / (out[1][0] - out[0][0])
        out.insert(0, [round(out[0][i] - (out[1][i] - out[0][i]) * k, 3) for i in range(3)] + [out[0][3]])
    return out
axes = {"arm_axis_L": arm_axis(1), "arm_axis_R": arm_axis(-1)}
# 어깨 관절 높이는 중심선 첫 표본(팔 뿌리)에서 잰다. 실루엣 띠로는 팔이 몸통과 붙는 높이밖에 못 잡는다
roots = [ax[0] for ax in axes.values() if ax]
if roots:
    sz = sum(p[2] for p in roots) / len(roots)
    shoulder = min(rows, key=lambda r: abs(r["z"] - sz)); shoulder = dict(shoulder, z=round(sz, 3))
land = {"height": round(H, 3), "ground_z": round(zmin, 3), "top_z": round(zmax, 3),
        "shoulder_z": shoulder["z"], "shoulder_halfwidth": round(shoulder["width"] / 2, 3),
        "crotch_z": crotch["z"] if crotch else round(zmin + H * 0.47, 3),
        "hip_z": round((crotch["z"] if crotch else zmin + H * 0.47) + H * 0.05, 3),
        "knee_z": round(zmin + H * 0.05 + (crotch["z"] - zmin - H * 0.05) * 0.5, 3) if crotch else round(zmin + H * 0.26, 3),
        "ankle_z": round(zmin + H * 0.05, 3), "head_top_z": round(zmax, 3), "neck_z": round(zmax - H * 0.12, 3),
        "torso_halfwidth": torso_hw, "arm_tip_x": tip["right"], "arm_tip_z": tip["z"],
        "vertex_spacing": round(spacing, 4), "symmetry_error": round(sym, 3), "pose_guess": "A" if tip["z"] < shoulder["z"] - H * 0.05 else "T", **axes}
bpy.ops.wm.save_as_mainfile(filepath=A["blend"])
done({"stats": st, "bands": rows, "landmarks": land, "blend": A["blend"]}, A["result"])
