"""진단(토큰 0): 사족 관절 찾기 결과를 원본 뼈대(정답)와 대조한다. 파이프라인에는 쓰지 않는다."""
import bpy
from mathutils import Vector
from _common import args, done, fresh, import_mesh, mesh_stats
from _quad import quad_landmarks

A = args(); fresh()
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"), keep_armature=True)
st = mesh_stats(obj)
vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
el = sorted((obj.data.vertices[e.vertices[0]].co - obj.data.vertices[e.vertices[1]].co).length for e in obj.data.edges[:4000])
spacing = el[len(el) // 2] if el else 0.01
q = quad_landmarks(vs, st, spacing)
# 앞뒤 방향 후보 신호들(어느 근거가 10종 전부 맞히는지 고르기 위한 진단)
zmin = st["min"][2]; H = st["height"]
mean_y = sum(v.y for v in vs) / len(vs)
ymin = min(v.y for v in vs); ymax = max(v.y for v in vs)
def m(sel): return (sum(v.y for v in sel) / len(sel) - mean_y) if sel else None
sig = {
    "top25": m([v for v in vs if v.z > zmin + H * 0.75]),
    "top10": m([v for v in vs if v.z > zmin + H * 0.90]),
    "highest": max(vs, key=lambda v: v.z).y - mean_y,
    "above_belly": m([v for v in vs if v.z > zmin + H * 0.5]),
    # 끝단 덩치: 각 y 끝에서 몸길이의 8% 안에 든 점 수(머리가 꼬리보다 굵다)
    "bulk_lo": len([v for v in vs if v.y < ymin + (ymax - ymin) * 0.08]),
    "bulk_hi": len([v for v in vs if v.y > ymax - (ymax - ymin) * 0.08]),
    # 끝단 높이: 각 끝에서 가장 높은 점(머리는 들려 있고 꼬리는 낮다 — 말린 꼬리면 뒤집힌다)
    "hz_lo": max((v.z for v in vs if v.y < ymin + (ymax - ymin) * 0.08), default=0) - zmin,
    "hz_hi": max((v.z for v in vs if v.y > ymax - (ymax - ymin) * 0.08), default=0) - zmin,
}
# 몸통 단면: 정답 골반 y 에서 등(최고)·배(최저)·무게중심 z 를 재 어느 규칙이 골반 높이를 맞히는지 본다
def slice_at(y, halfw, band):
    """그 y 위치의 등 높이(최고점). 다리는 아래에 있으니 x 를 안 자르고 최고점만 봐도 등이다"""
    sel = [v for v in vs if abs(v.y - y) < band]
    if len(sel) < 6: return None
    zs = [v.z for v in sel]
    return {"zmin": round(min(zs), 3), "zmax": round(max(zs), 3),
            "zmean": round(sum(zs) / len(zs), 3), "n": len(sel)}
gt = {}
for ob in bpy.data.objects:
    if ob.type == "ARMATURE":
        for b in ob.data.bones:
            h = ob.matrix_world @ b.head_local
            gt[b.name] = [round(h.x, 3), round(h.y, 3), round(h.z, 3)]
# 다리 기둥 추적: 발에서 위로 올라가며 직전 중심 주변 점만 모은다. 가장 뒤쪽 표본이 비절/팔꿈치인지 본다
def trace(seed_xy, sx, ztop, spacing):
    cx, cy = seed_xy
    reach = spacing * 4.0
    out = []
    for i in range(24):
        z0 = zmin + ztop * i / 24; z1 = zmin + ztop * (i + 1) / 24
        sel = [v for v in vs if z0 <= v.z < z1 and v.x * sx > 0
               and (v.x - cx) ** 2 + (v.y - cy) ** 2 < reach * reach]
        if len(sel) < 4: break
        c = sum(sel, Vector()) / len(sel)
        rad = sum(((v - c) - Vector((0, 0, v.z - c.z))).length for v in sel) / len(sel)
        out.append([round(c.x, 3), round(c.y, 3), round(c.z, 3), round(rad, 3)])
        cx, cy = c.x, c.y
        reach = max(spacing * 4.0, rad * 2.2)
    return out
traces = {}
for k, f in q.get("feet", {}).items():
    sx = 1.0 if k.endswith("L") else -1.0
    traces[k] = trace((f[0], f[1]), sx, H * 0.55, spacing)
xs = [abs(v.x) for v in vs]; halfw = sorted(xs)[int(len(xs) * 0.6)]   # 다리보다 안쪽 폭(몸통만 보기)
cuts = {}
for label, bone in (("pelvis", "Back"), ("shoulder", "FrontUpperLeg.L"), ("mid", None)):
    y = gt.get(bone, [0, None, 0])[1] if bone else (sum(v.y for v in vs) / len(vs))
    if y is not None:
        cuts[label] = {"y": round(y, 3), **(slice_at(y, halfw, H * 0.04) or {})}
done({"quad": q, "gt": gt, "height": round(H, 3), "sig": sig, "halfw": round(halfw, 3), "cuts": cuts, "traces": traces}, A["result"])
