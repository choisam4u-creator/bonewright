"""메타리그의 본 이름·기본 head/tail(메시 높이로 스케일)을 JSON 으로 — 모델에게 주는 참고표(토큰 절약: 주요 본만)."""
import bpy
from _common import args, done, fresh
A = args(); fresh(); bpy.ops.preferences.addon_enable(module="rigify")
op = {"humanoid": "armature_human_metarig_add", "quadruped": "armature_wolf_metarig_add"}[A.get("preset", "humanoid")]
getattr(bpy.ops.object, op)(); meta = bpy.context.active_object
mh = max(b.tail_local.z for b in meta.data.bones) - min(b.head_local.z for b in meta.data.bones)
s = A["height"] / mh if mh else 1.0
keep = ("spine", "shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot", "toe", "neck", "head")
bones = {b.name: {"head": [round(c * s, 3) for c in b.head_local] , "tail": [round(c * s, 3) for c in b.tail_local]}
         for b in meta.data.bones if b.name.split(".")[0] in keep and "face" not in b.name}
for v in bones.values():
    v["head"][2] += A.get("ground_z", 0); v["tail"][2] += A.get("ground_z", 0)
done({"bones": bones, "scale": round(s, 4), "all_bones": len(meta.data.bones)}, A["result"])
