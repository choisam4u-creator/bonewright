# v2: 본을 얇은 기둥 메시로 바꿔 헤드리스 렌더에 보이게 한다(아마추어는 최종 렌더에 안 그려짐). 왼쪽 위팔 본은 고의로 밖으로.
import bpy, os, sys, math, json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="rigify")
bpy.ops.object.armature_human_metarig_add(); meta = bpy.context.active_object
bpy.ops.object.mode_set(mode="EDIT")
if "upper_arm.L" in meta.data.edit_bones:
    meta.data.edit_bones["upper_arm.L"].tail = (1.2, 0.0, 1.9)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=1.2, location=(0, 0, 1.2)); body = bpy.context.active_object; body.name = "body"
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, 0, 1.95)); head = bpy.context.active_object; head.name = "head"
mat = bpy.data.materials.new("bone_red"); mat.diffuse_color = (1, 0.1, 0.1, 1)
n = 0
for b in meta.data.bones:
    if b.name.startswith("face") or "eye" in b.name or "lip" in b.name or "brow" in b.name or "nose" in b.name or "cheek" in b.name or "jaw" in b.name or "ear" in b.name or "chin" in b.name or "tongue" in b.name or "teeth" in b.name or "temple" in b.name or "forehead" in b.name:
        continue
    h, t = meta.matrix_world @ b.head_local, meta.matrix_world @ b.tail_local
    d = t - h; L = d.length
    if L < 0.01: continue
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=L, location=(h + t) / 2)
    c = bpy.context.active_object; c.rotation_mode = "QUATERNION"; c.rotation_quaternion = d.to_track_quat("Z", "Y"); c.data.materials.append(mat); n += 1
bpy.ops.object.camera_add(location=(3.2, -3.6, 1.5), rotation=(math.radians(82), 0, math.radians(41))); cam = bpy.context.active_object
bpy.context.scene.camera = cam
bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = 512; sc.render.resolution_y = 512
sc.display.shading.color_type = "MATERIAL"
sc.render.filepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[-1])), "rig_view2.png")
bpy.ops.render.render(write_still=True)
print("RESULT " + json.dumps({"bone_proxies": n, "bytes": os.path.getsize(sc.render.filepath)}))
