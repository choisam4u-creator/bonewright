"""테스트용 절차적 휴머노이드(캡슐 몸통+머리+팔다리, A포즈, 약 1.8m). 라이선스 걱정 없는 고정 자산."""
import bpy, bmesh, math
from _common import args, done, fresh
A = args(); fresh()

def capsule(name, r, length, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=loc, rotation=rot, vertices=24)
    o = bpy.context.active_object; o.name = name
    for sign in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=16, ring_count=8, location=loc)
        s = bpy.context.active_object
        s.location = o.matrix_world @ __import__("mathutils").Vector((0, 0, sign * length / 2))
        s.select_set(True); o.select_set(True); bpy.context.view_layer.objects.active = o; bpy.ops.object.join()
    return o

parts = [capsule("torso", 0.17, 0.55, (0, 0, 1.25)), capsule("pelvis", 0.16, 0.10, (0, 0, 1.06)),   # 골반을 올려 가랑이가 키의 약 47% 에 오도록
         capsule("head", 0.11, 0.04, (0, 0, 1.68)), capsule("neck", 0.05, 0.08, (0, 0, 1.55))]
from mathutils import Vector
for s, x in (("L", 1), ("R", -1)):
    # 팔: 어깨점(몸통 안)에서 바깥·아래 65도로 뻗는 A 포즈. 캡슐이 서로 겹쳐 한 덩어리가 된다
    sh = Vector((x * 0.15, 0, 1.47)); d = Vector((x * math.sin(math.radians(65)), 0, -math.cos(math.radians(65))))
    rot = (0, math.radians(-x * 65), 0)   # Z축을 Y로 -65도 돌리면 축이 d 와 평행해진다(부호 틀리면 캡슐이 지그재그)
    parts.append(capsule(f"upper_arm.{s}", 0.055, 0.28, sh + d * 0.14, rot))
    parts.append(capsule(f"forearm.{s}", 0.045, 0.26, sh + d * (0.28 + 0.13), rot))
    parts.append(capsule(f"hand.{s}", 0.04, 0.08, sh + d * (0.54 + 0.04), rot))
    parts.append(capsule(f"thigh.{s}", 0.08, 0.42, (x * 0.11, 0, 0.72)))
    parts.append(capsule(f"shin.{s}", 0.06, 0.40, (x * 0.11, 0, 0.30)))
    parts.append(capsule(f"foot.{s}", 0.05, 0.16, (x * 0.11, -0.06, 0.06), (math.radians(90), 0, 0)))
bpy.ops.object.select_all(action="DESELECT")
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
obj = bpy.context.active_object; obj.name = "character"
# 겹친 캡슐을 하나의 닫힌 표면으로(복셀 리메시) — 자동 가중치(Bone Heat)가 풀리는 조건
m = obj.modifiers.new("remesh", "REMESH"); m.mode = "VOXEL"; m.voxel_size = 0.02   # 2cm: 3cm 이면 변형이 뭉툭하게 보인다
bpy.ops.object.modifier_apply(modifier="remesh")
# 바닥을 z=0 에 맞춘다
zmin = min((obj.matrix_world @ v.co).z for v in obj.data.vertices); obj.location.z -= zmin
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.export_scene.gltf(filepath=A["out"], export_format="GLB", use_selection=False)
done({"verts": len(obj.data.vertices), "out": A["out"]}, A["result"])
