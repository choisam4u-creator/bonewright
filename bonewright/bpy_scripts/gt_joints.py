"""정답 뼈대 추출(토큰 0): 원본 스켈레톤이 들어 있는 파일을 우리와 '똑같이 정규화한 공간'으로 옮겨
관절(본 head) 좌표를 뽑는다. 벤치마크에서 우리 리깅 결과와 cm 단위로 비교하는 기준이 된다."""
import bpy
from _common import args, done, fresh, import_mesh, IMPORT_INFO
A = args(); fresh()
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"), keep_armature=True,
                  quad=A.get("preset") == "quadruped")
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not arms:
    done({"joints": {}, "bones": 0, "error": "원본 아마추어 없음"}, A["result"]); raise SystemExit
arm = max(arms, key=lambda a: len(a.data.bones))
joints = {}
for b in arm.data.bones:
    h = arm.matrix_world @ b.head_local; t = arm.matrix_world @ b.tail_local
    joints[b.name] = {"head": [round(v, 4) for v in h], "tail": [round(v, 4) for v in t],
                      "parent": b.parent.name if b.parent else None}
vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
zs = [v.z for v in vs]
done({"joints": joints, "bones": len(joints), "armature": arm.name,
      "height": round(max(zs) - min(zs), 4), "import": dict(IMPORT_INFO)}, A["result"])
