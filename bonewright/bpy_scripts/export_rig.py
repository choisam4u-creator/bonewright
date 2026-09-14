"""리깅 결과를 게임용 GLB 로 내보낸다(토큰 0): 변형 본(DEF-)만 + 스킨 메시, 애니메이션 없음.

Rigify 리그는 컨트롤·MCH·ORG 본이 400개가 넘어 그대로 내면 엔진에서 쓸모없는 본이 따라간다 → export_def_bones 로 변형 본만.
검증: 내보낸 파일을 빈 장면에 다시 읽어 본 수·정점 수를 세고, 손·발 본 머리 위치를 원본 리그와 cm 로 대조한다.
"""
import bpy
from _common import args, done, fresh

A = args()
bpy.ops.wm.open_mainfile(filepath=A["blend"])
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(b.name.startswith("DEF-") for b in o.data.bones))
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig)
rig.data.pose_position = "REST"; bpy.context.view_layer.update()
PROBE = [n for n in ("DEF-hand.L", "DEF-hand.R", "DEF-foot.L", "DEF-foot.R", "DEF-front_foot.L", "DEF-spine") if n in rig.data.bones]
probe = {n: (rig.matrix_world @ rig.data.bones[n].head_local).copy() for n in PROBE}
nverts = len(mesh.data.vertices)
bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=A["out"], use_selection=True, export_format="GLB", export_apply=False, export_yup=True,
                          export_skins=True, export_def_bones=True, export_animations=False)
fresh()
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=A["out"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o not in before)
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in before]
bpy.context.view_layer.update()
diff = {n: round(((arm.matrix_world @ arm.data.bones[n].head_local) - p).length * 100, 2) for n, p in probe.items() if n in arm.data.bones}
done({"out": A["out"], "bones": len(arm.data.bones), "deform_bones_in_source": sum(1 for b in rig.data.bones if b.use_deform) if False else None,
      "meshes": len(meshes), "verts": sum(len(m.data.vertices) for m in meshes), "verts_in_source": nverts,
      "reimport_diff_cm": diff, "max_diff_cm": max(diff.values()) if diff else None}, A["result"])
