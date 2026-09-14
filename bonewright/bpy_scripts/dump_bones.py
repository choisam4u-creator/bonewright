"""리그의 변형 본 head/tail 좌표를 뽑는다(토큰 0). 테스트·디버깅용."""
import bpy
from _common import args, done
A = args()
bpy.ops.wm.open_mainfile(filepath=A["blend"])
rig = [o for o in bpy.data.objects if o.type == "ARMATURE" and not o.name.startswith("meta")][0]
names = A.get("names")
out = {}
for b in rig.data.bones:
    if names and b.name not in names: continue
    if not names and not b.use_deform: continue
    out[b.name] = {"head": [round(v, 4) for v in (rig.matrix_world @ b.head_local)],
                   "tail": [round(v, 4) for v in (rig.matrix_world @ b.tail_local)]}
done({"bones": out, "count": len(out)}, A["result"])
