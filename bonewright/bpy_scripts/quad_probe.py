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
gt = {}
for ob in bpy.data.objects:
    if ob.type == "ARMATURE":
        for b in ob.data.bones:
            h = ob.matrix_world @ b.head_local
            gt[b.name] = [round(h.x, 3), round(h.y, 3), round(h.z, 3)]
done({"quad": q, "gt": gt, "height": round(H, 3), "sig": sig}, A["result"])
