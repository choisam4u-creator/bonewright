"""1단계 분석(토큰 0): 메시 크기·대칭·높이띠별 폭에서 관절 후보(어깨·골반·무릎·손)를 추정한다."""
import bpy
from _common import args, done, fresh, import_mesh, mesh_stats, topology
A = args(); fresh()
obj = import_mesh(A["mesh"]); st = mesh_stats(obj); st.update(topology(obj))
vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
zmin, zmax = st["min"][2], st["max"][2]; H = st["height"]
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
crotch = next((r for r in rows if r["gap"] > 0.02), None)
sym = sum(abs(r["left"] + r["right"]) for r in rows) / max(1, len(rows))
# 몸통 반폭: 가랑이 위~어깨 아래 구간에서 가장 좁은 띠. 팔 끝: 어깨 높이 아래 구간에서 가장 바깥 점
cz = crotch["z"] if crotch else zmin + H * 0.47
torso = [r for r in rows if cz + H * 0.08 < r["z"] < shoulder["z"] - H * 0.02 and r["width"] > 0]
torso_hw = round(min(r["width"] for r in torso) / 2, 3) if torso else round(st["width"] / 6, 3)
arm_rows = [r for r in rows if zmin + H * 0.45 < r["z"] <= shoulder["z"] + H * 0.05 and r["width"] > 0]
tip = max(arm_rows, key=lambda r: r["right"]) if arm_rows else shoulder
land = {"height": round(H, 3), "ground_z": round(zmin, 3), "top_z": round(zmax, 3),
        "shoulder_z": shoulder["z"], "shoulder_halfwidth": round(shoulder["width"] / 2, 3),
        "crotch_z": crotch["z"] if crotch else round(zmin + H * 0.47, 3),
        "hip_z": round((crotch["z"] if crotch else zmin + H * 0.47) + H * 0.05, 3),
        "knee_z": round(zmin + (crotch["z"] - zmin) * 0.52, 3) if crotch else round(zmin + H * 0.26, 3),
        "ankle_z": round(zmin + H * 0.05, 3), "head_top_z": round(zmax, 3), "neck_z": round(zmax - H * 0.12, 3),
        "torso_halfwidth": torso_hw, "arm_tip_x": tip["right"], "arm_tip_z": tip["z"],
        "symmetry_error": round(sym, 3), "pose_guess": "A" if tip["z"] < shoulder["z"] - H * 0.05 else "T"}
bpy.ops.wm.save_as_mainfile(filepath=A["blend"])
done({"stats": st, "bands": rows, "landmarks": land, "blend": A["blend"]}, A["result"])
