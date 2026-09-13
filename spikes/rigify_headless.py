# 헤드리스 확인: Rigify 활성화 → 휴머노이드·사족 메타리그 → 리그 생성 → 본 수·FBX 내보내기 (토큰 0)
import bpy, sys, json, time, os
out = {"blender": bpy.app.version_string, "steps": []}
t0 = time.time()
try:
    bpy.ops.preferences.addon_enable(module="rigify")
    out["steps"].append("rigify enabled")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="rigify")
    for name, op in [("human", "armature_human_metarig_add"), ("wolf", "armature_wolf_metarig_add")]:
        getattr(bpy.ops.object, op)()
        meta = bpy.context.active_object
        meta.name = f"meta_{name}"
        nb = len(meta.data.bones)
        bpy.context.view_layer.objects.active = meta
        bpy.ops.pose.rigify_generate()
        rig = bpy.context.active_object
        out["steps"].append({"metarig": name, "meta_bones": nb, "rig": rig.name, "rig_bones": len(rig.data.bones),
                             "deform_bones": sum(1 for b in rig.data.bones if b.use_deform)})
    exp = os.path.join(os.path.dirname(os.path.abspath(sys.argv[-1])), "rig_test.fbx")
    bpy.ops.export_scene.fbx(filepath=exp, use_selection=False, add_leaf_bones=False)
    out["fbx_bytes"] = os.path.getsize(exp)
    out["seconds"] = round(time.time() - t0, 1); out["ok"] = True
except Exception as e:
    out["ok"] = False; out["error"] = repr(e)
print("RESULT " + json.dumps(out, ensure_ascii=False))
