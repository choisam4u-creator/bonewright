"""motion: BVH 를 가져와 본·프레임·루트 이동을 확인하고 .blend 로 저장(토큰 0). 리타겟은 v0.2."""
import bpy, os
from _common import args, done, fresh
A = args(); fresh()
bpy.ops.import_anim.bvh(filepath=A["bvh"], axis_forward="-Z", axis_up="Y", update_scene_fps=True, update_scene_duration=True)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]; sc = bpy.context.scene
act = arm.animation_data.action if arm.animation_data else None
frames = None
if act:
    fr = act.frame_range; frames = [int(fr[0]), int(fr[1])]
sc.frame_set(frames[0] if frames else 1); p0 = arm.pose.bones[0].head.copy()
sc.frame_set(frames[1] if frames else 1); p1 = arm.pose.bones[0].head.copy()
bpy.ops.wm.save_as_mainfile(filepath=A["out_blend"])
done({"armature": arm.name, "bones": len(arm.data.bones), "frames": frames, "fps": sc.render.fps, "root_move": round((p1 - p0).length, 3),
      "bone_names": [b.name for b in arm.data.bones]}, A["result"])
