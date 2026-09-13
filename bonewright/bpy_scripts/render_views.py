"""4단계 렌더(토큰 0): 변형 본을 빨간 기둥으로, 메시는 회색으로. 정면·측면·대각 3장. 판정용."""
import bpy, os, math
from mathutils import Vector
from _common import args, done
A = args(); bpy.ops.wm.open_mainfile(filepath=A["blend"])
rig = [o for o in bpy.data.objects if o.type == "ARMATURE" and not o.name.startswith("meta")][0]
obj = bpy.data.objects["character"]
red = bpy.data.materials.new("bw_bone"); red.diffuse_color = (1, 0.1, 0.1, 1)
grey = bpy.data.materials.new("bw_mesh"); grey.diffuse_color = (0.75, 0.75, 0.75, 1)
obj.data.materials.clear(); obj.data.materials.append(grey)
if A.get("pose"):
    # 간단 테스트 포즈: 지정 본 회전(도) — 변형 확인용
    bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode="POSE")
    for name, rot in A["pose"].items():
        pb = rig.pose.bones.get(name)
        if pb: pb.rotation_mode = "XYZ"; pb.rotation_euler = [math.radians(a) for a in rot]
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()
n = 0
for b in rig.pose.bones:
    if not b.bone.use_deform: continue
    h, t = rig.matrix_world @ b.head, rig.matrix_world @ b.tail; d = t - h
    if d.length < 0.01: continue
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=d.length, location=(h + t) / 2, vertices=8)
    c = bpy.context.active_object; c.rotation_mode = "QUATERNION"; c.rotation_quaternion = d.to_track_quat("Z", "Y"); c.data.materials.append(red); n += 1
mn, mx = Vector(A["stats"]["min"]), Vector(A["stats"]["max"]); center = (mn + mx) / 2; H = mx.z - mn.z
bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = A.get("size", 512)
sc.display.shading.color_type = "MATERIAL"; sc.display.shading.light = "STUDIO"
# 엑스레이(반투명): 안쪽 본도 흐리게 보여야 비율을 판정할 수 있다. 실루엣 밖 본은 진한 빨강으로 구분된다
sc.display.shading.show_xray = True; sc.display.shading.xray_alpha = float(A.get("xray_alpha", 0.45))
outs = []
for name, (dx, dy) in {"front": (0, -1), "side": (1, 0), "iso": (0.8, -0.8)}.items():
    dist = H * 1.6
    loc = Vector((center.x + dx * dist, center.y + dy * dist, center.z))
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.active_object
    cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (center - loc).to_track_quat("-Z", "Y")
    cam.data.ortho_scale = H * 1.3; cam.data.type = "ORTHO"; sc.camera = cam
    sc.render.filepath = os.path.join(A["out_dir"], f"view_{name}.png"); bpy.ops.render.render(write_still=True); outs.append(sc.render.filepath)
done({"images": outs, "bone_proxies": n}, A["result"])
