"""리타겟 결과를 게임용 GLB 로 내보낸다(토큰 0): 변형 본(DEF-)만 + 메시 + 구운 애니메이션.

Rigify 리그는 컨트롤·MCH·ORG 본이 400개가 넘는다. glTF 로 그대로 내면 엔진에서 쓸모없는 본이 잔뜩 따라간다 →
export_def_bones 로 변형 본만 남기고, 컨스트레인트 결과를 프레임마다 샘플링해 굽는다.
검증: 내보낸 파일을 빈 장면에 다시 읽어 본 수·프레임 수를 세고, 중간 프레임의 손 위치가 원본 리그와 얼마나 다른지 cm 로 잰다.
"""
import bpy
from mathutils import Vector
from _common import args, done, fresh

A = args()
bpy.ops.wm.open_mainfile(filepath=A["blend"])
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(b.name.startswith("DEF-") for b in o.data.bones))
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig)
sc = bpy.context.scene
# 리타겟 액션의 실제 범위로 중간 프레임을 잡는다(장면 범위는 BVH 가져오기가 250 까지 늘려 놓을 수 있다)
act0 = rig.animation_data.action if rig.animation_data else None
f0, f1 = (int(act0.frame_range[0]), int(act0.frame_range[1])) if act0 else (sc.frame_start, sc.frame_end)
fps = sc.render.fps
fm = (f0 + f1) // 2
sc.frame_set(fm); bpy.context.view_layer.update()
# 대조값: 중간 프레임의 손·발 월드 위치
probe = {n: (rig.matrix_world @ rig.pose.bones[n].head).copy() for n in ("DEF-hand.L", "DEF-hand.R", "DEF-foot.L", "DEF-foot.R") if n in rig.pose.bones}
# glTF 내보내기는 기본(ACTIONS)이 '아마추어에 얹을 수 있는 모든 액션'을 굽는다 → 원본 BVH 아마추어의 액션(motion)까지 우리 리그에
# 얹혀 나가고, 다시 읽으면 그게 활성이 되어 리그가 쉬는 자세로 굳는다(e2e1 에서 손 위치 165cm 차이로 발견). 활성 액션만 내보내고
# 다른 아마추어의 액션은 지운다
for o in bpy.data.objects:
    if o.type == "ARMATURE" and o is not rig and o.animation_data and o.animation_data.action:
        act = o.animation_data.action; o.animation_data.action = None; bpy.data.actions.remove(act)
sc.frame_start, sc.frame_end = f0, f1
bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=A["out"], use_selection=True, export_format="GLB", export_apply=False, export_yup=True,
                          export_skins=True, export_def_bones=True, export_animations=True, export_force_sampling=True,
                          export_frame_range=True, export_animation_mode="ACTIVE_ACTIONS", export_anim_single_armature=True,
                          export_optimize_animation_size=False)

# 다시 읽어 확인
fresh()
bpy.context.scene.render.fps = fps   # 가져오기는 장면 fps 로 키를 찍는다 → 원래 fps 로 맞춰야 프레임 번호가 같다
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=A["out"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o not in before)
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in before]
act = arm.animation_data.action if arm.animation_data else None
fr = [int(act.frame_range[0]), int(act.frame_range[1])] if act else None
sc = bpy.context.scene
# glTF 시간은 0 초부터라 프레임 번호가 f0 만큼 앞당겨진다
sc.frame_set(fm - f0 + (fr[0] if fr else 0)); bpy.context.view_layer.update()
diff = {}
for n, p in probe.items():
    pb = arm.pose.bones.get(n)
    if pb is not None:
        diff[n] = round(((arm.matrix_world @ pb.head) - p).length * 100, 2)
done({"out": A["out"], "bones": len(arm.data.bones), "meshes": len(meshes), "verts": sum(len(m.data.vertices) for m in meshes),
      "actions": [a.name for a in bpy.data.actions],
      "frames": fr, "fps": fps, "probe_frame": fm, "reimport_diff_cm": diff,
      "max_diff_cm": max(diff.values()) if diff else None}, A["result"])
