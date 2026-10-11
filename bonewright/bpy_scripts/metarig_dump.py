"""메타리그의 본 이름·기본 head/tail(메시 높이로 스케일)을 JSON 으로 — 모델에게 주는 참고표(토큰 절약: 주요 본만)."""
import bpy
from _common import args, done, fresh
A = args(); fresh(); bpy.ops.preferences.addon_enable(module="rigify")
op = {"humanoid": "armature_human_metarig_add", "quadruped": "armature_wolf_metarig_add"}[A.get("preset", "humanoid")]
getattr(bpy.ops.object, op)(); meta = bpy.context.active_object
mh = max(b.tail_local.z for b in meta.data.bones) - min(b.head_local.z for b in meta.data.bones)
s = A["height"] / mh if mh else 1.0
keep = ("spine", "shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot", "toe", "neck", "head")
if A.get("preset") == "quadruped":   # 늑대 메타리그의 앞다리. 이게 빠져 있어서 앞다리는 목표를 한 번도 못 받았다
    # pelvis.L/R(엉덩이 벌어짐 본)도 넣는다 — 골반을 옮기면 같이 따라와야 한다(빠져 있어 말·소에서 몸 밖 뒤쪽으로 남았다)
    keep += ("front_thigh", "front_shin", "front_foot", "front_toe", "pelvis", "breast")
bones = {b.name: {"head": [round(c * s, 3) for c in b.head_local] , "tail": [round(c * s, 3) for c in b.tail_local]}
         for b in meta.data.bones if b.name.split(".")[0] in keep and "face" not in b.name}
for v in bones.values():
    v["head"][2] += A.get("ground_z", 0); v["tail"][2] += A.get("ground_z", 0)
done({"bones": bones, "scale": round(s, 4), "all_bones": len(meta.data.bones),
      "names": sorted(b.name for b in meta.data.bones)}, A["result"])   # bonewright/metarig_names.json 대조용(--pin 이름 검사)
