"""데모 영상(토큰 0): 생성된 리그의 IK 컨트롤을 움직여(두 손 앞으로 → 왼발 뒤로 들기·몸통 비틀기 → 제자리) 메시 변형을 보여주고, 마지막 1초는 턴테이블."""
import bpy, os, math, glob
from mathutils import Vector
from _common import args, done
A = args(); bpy.ops.wm.open_mainfile(filepath=A["blend"])
rig = [o for o in bpy.data.objects if o.type == "ARMATURE" and not o.name.startswith("meta")][0]
obj = bpy.data.objects["character"]
for o in bpy.data.objects:
    if o.name.startswith("metarig"): o.hide_render = True; o.hide_viewport = True
red = bpy.data.materials.new("bw_bone"); red.diffuse_color = (1, 0.1, 0.1, 1)
grey = bpy.data.materials.new("bw_mesh"); grey.diffuse_color = (0.75, 0.75, 0.75, 1)
obj.data.materials.clear(); obj.data.materials.append(grey)
# 본 기둥: 변형 본을 Copy Transforms 로 따라다닌다(포즈가 바뀌어도 같이 움직인다)
n = 0
for b in rig.pose.bones:
    ln = b.bone.length
    if not b.bone.use_deform or ln < 0.01: continue
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=ln, location=(0, ln / 2, 0), rotation=(math.pi / 2, 0, 0), vertices=8)
    c = bpy.context.active_object; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); c.data.materials.append(red)
    con = c.constraints.new("COPY_TRANSFORMS"); con.target = rig; con.subtarget = b.name; n += 1
H = A["height"]; k = H / 1.8
frames = int(A.get("frames", 96)); q = frames // 4
sc = bpy.context.scene; sc.frame_start = 1; sc.frame_end = frames; sc.render.fps = 24
bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True); bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode="POSE")
pb = rig.pose.bones
def key_loc(name, delta, frame):   # IK 컨트롤을 쉬는 자세에서 delta(월드 기준 m)만큼 옮기고 키를 찍는다
    b = pb.get(name)
    if not b: return
    m = b.bone.matrix_local.copy(); m.translation = m.translation + Vector(delta)
    b.matrix = m; bpy.context.view_layer.update(); b.keyframe_insert("location", frame=frame)
def key_rot(name, deg, frame):
    b = pb.get(name)
    if not b: return
    b.rotation_mode = "XYZ"; b.rotation_euler = [math.radians(a) for a in deg]; b.keyframe_insert("rotation_euler", frame=frame)
hands = {s: pb[f"hand_ik.{s}"].bone.matrix_local.translation.copy() for s in ("L", "R") if f"hand_ik.{s}" in pb}
foot = pb["foot_ik.L"].bone.matrix_local.translation.copy() if "foot_ik.L" in pb else None
QUAD = "front_foot_ik.L" in pb   # 사족: 손 IK 대신 앞발 IK 가 있다
def pose(frame, hands_fwd, knee_up, twist):
    for s, x in (("L", 1), ("R", -1)):
        if s in hands:
            tgt = Vector((x * 0.13 * k, -0.30 * k, hands[s].z + 0.05 * k)) if hands_fwd else hands[s]
            key_loc(f"hand_ik.{s}", tgt - hands[s], frame)
    if foot is not None:
        key_loc("foot_ik.L", (Vector((foot.x + 0.04 * k, 0.22 * k, 0.42 * k)) - foot) if knee_up else (0, 0, 0), frame)   # 발을 뒤로 들어 무릎 굽힘을 보인다
    key_rot("torso", (0, 0, 15) if twist else (0, 0, 0), frame); key_rot("head", (0, 0, -20) if twist else (0, 0, 0), frame)

def pose_quad(frame, phase):
    """사족 데모: 대각선 두 발씩 드는 속보(트롯). 사람용 손 IK 가 없어 그냥 서 있던 것을 고친 것이다.
    드는 높이·앞뒤 폭은 다리 길이(발 IK 컨트롤의 쉬는 높이가 아니라 몸 높이 k)에 비례시킨다"""
    lift, fwd = 0.16 * k, 0.10 * k
    pairs = {0: (), 1: ("front_foot_ik.L", "foot_ik.R"), 2: (), 3: ("front_foot_ik.R", "foot_ik.L")}[phase]
    for n in ("front_foot_ik.L", "front_foot_ik.R", "foot_ik.L", "foot_ik.R"):
        if n not in pb: continue
        up = n in pairs
        key_loc(n, (0, -fwd if up else 0, lift if up else 0), frame)
    key_rot("torso", (0, 0, 6 if phase == 1 else (-6 if phase == 3 else 0)), frame)
    key_rot("head", (0, 0, -12 if phase == 1 else (12 if phase == 3 else 0)), frame)

if QUAD:
    for i in range(4):
        pose_quad(1 + i * q if i else 1, i)
else:
    pose(1, False, False, False); pose(q, True, False, False); pose(2 * q, True, True, True); pose(3 * q, False, False, False)
bpy.ops.object.mode_set(mode="OBJECT")
# 턴테이블(마지막 1/4): 새 키의 보간을 선형으로(Blender 5 의 슬롯 액션은 action.fcurves 가 없어 환경설정으로 정한다)
pref = bpy.context.preferences.edit; old_interp = pref.keyframe_new_interpolation_type; pref.keyframe_new_interpolation_type = "LINEAR"
rig.rotation_mode = "XYZ"; rig.rotation_euler = (0, 0, 0); rig.keyframe_insert("rotation_euler", frame=3 * q)
rig.rotation_euler = (0, 0, math.tau); rig.keyframe_insert("rotation_euler", frame=frames)
pref.keyframe_new_interpolation_type = old_interp
mn, mx = Vector(A["stats"]["min"]), Vector(A["stats"]["max"]); center = (mn + mx) / 2
bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
dist = H * 1.6; loc = Vector((center.x + 0.75 * dist, center.y - 0.9 * dist, center.z + 0.25 * dist))
bpy.ops.object.camera_add(location=loc); cam = bpy.context.active_object
cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (center - loc).to_track_quat("-Z", "Y")
cam.data.type = "ORTHO"; cam.data.ortho_scale = H * 1.35; sc.camera = cam
sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = int(A.get("size", 640))
sc.display.shading.color_type = "MATERIAL"; sc.display.shading.light = "STUDIO"
# macOS 배포판 Blender 5.2 에는 FFMPEG 출력이 없다 → PNG 연속 이미지로 내고 파이프라인이 ffmpeg 로 합친다
fdir = os.path.join(A["out_dir"], "demo_frames"); os.makedirs(fdir, exist_ok=True)
for f in glob.glob(os.path.join(fdir, "f_*.png")): os.remove(f)
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = os.path.join(fdir, "f_")
bpy.ops.render.render(animation=True)
done({"frames_dir": fdir, "frames": frames, "fps": sc.render.fps, "bone_proxies": n, "controls": {"hands": sorted(hands), "foot": foot is not None}}, A["result"])
