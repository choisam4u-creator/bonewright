# BVH 를 Blender 에 가져와 본 수·프레임 수·루트 이동량을 확인 (토큰 0)
import bpy, sys, json, os
bvh = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_anim.bvh(filepath=bvh, axis_forward="-Z", axis_up="Y", update_scene_fps=True, update_scene_duration=True)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
sc = bpy.context.scene
fr = (sc.frame_start, sc.frame_end)
sc.frame_set(fr[0]); p0 = arm.pose.bones[0].head.copy() if arm.pose.bones else None
sc.frame_set(fr[1]); p1 = arm.pose.bones[0].head.copy() if arm.pose.bones else None
out = {"armature": arm.name, "bones": len(arm.data.bones), "frames": fr, "fps": sc.render.fps,
       "root_move": round((p1 - p0).length, 3) if p0 and p1 else None,
       "bone_names": [b.name for b in arm.data.bones][:8]}
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(bvh)[0] + ".blend")
print("RESULT " + json.dumps(out))
