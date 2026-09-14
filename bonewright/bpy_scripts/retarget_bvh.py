"""BVH 동작을 우리 Rigify 리그에 옮긴다(토큰 0).

원리: 관절마다 BVH 의 '쉬는 자세 대비 월드 회전 델타'를 구해 우리 FK 본의 쉬는 자세에 곱한다.
  Rt = (Rs · Rs0⁻¹) · M · Rt0     (Rs: BVH 현재 월드 회전, Rs0: BVH 쉬는 자세, Rt0: 우리 쉬는 자세)
M 은 팔다리 본에만 넣는 보정: BVH 쉬는 본 방향 → 우리 쉬는 본 방향의 최소 회전. 이게 있으면 두 뼈대의
쉬는 자세가 달라도(BVH 가 A 포즈, 우리가 T 포즈) 매 프레임 우리 본 방향이 BVH 본 방향과 같아진다.
몸통·목·머리·어깨는 본 축 규약이 서로 달라(torso 는 앞을 보고 Hips 는 위를 본다) M 없이 순수 델타만 쓴다.
비틀림(롤)은 옮기지 않는다 — 손바닥 방향은 어긋날 수 있다.
루트 이동은 BVH 엉덩이 이동을 키 비율로 줄여 torso 컨트롤에 옮긴다.

검증 두 가지(프레임마다):
  dir_deg: BVH 관절→자식 관절 방향과 우리 DEF 본 방향 사이 각도. 비율 차이와 무관해서 자세가 옮겨졌는지 본다.
  end_cm : 엉덩이 기준 손·발 위치 차이(키 비율로 줄임). 뼈대 비율이 다르면 0 이 될 수 없다 — 참고용.
"""
import os
import bpy
from mathutils import Matrix, Vector
from _common import args, done

A = args()
bpy.ops.wm.open_mainfile(filepath=A["blend"])
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(b.name.startswith("DEF-") for b in o.data.bones))
before = set(bpy.data.objects)
bpy.ops.import_anim.bvh(filepath=A["bvh"], axis_forward="-Z", axis_up="Y", update_scene_fps=True, update_scene_duration=True)
src = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o not in before)
sc = bpy.context.scene
act = src.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
mapping = A["mapping"]   # BVH 본 → 우리 FK 본 (pipeline 이 bench 정규화로 만든다)
mapping = {s: t for s, t in mapping.items() if s in src.pose.bones and t in rig.pose.bones}
Ws, Wt = src.matrix_world, rig.matrix_world
Ws3, Wt3 = Ws.to_3x3(), Wt.to_3x3()
LIMB = ("upper_arm_fk", "forearm_fk", "hand_fk", "thigh_fk", "shin_fk", "foot_fk")

# 팔다리를 FK 로 돌린다(기본은 IK 라 FK 본을 돌려도 메시가 안 움직인다)
for n in ("upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L", "thigh_parent.R"):
    pb = rig.pose.bones.get(n)
    if pb is not None and "IK_FK" in pb: pb["IK_FK"] = 1.0

def rest_rot(pb, W3):
    return W3 @ pb.bone.matrix_local.to_3x3()
def pose_rot(pb, W3):
    return W3 @ pb.matrix.to_3x3()

# 부모 먼저 처리해야 자식이 갱신된 부모를 읽는다
order = sorted(mapping.items(), key=lambda st: len(rig.pose.bones[st[1]].parent_recursive))
for _, t in order:
    rig.pose.bones[t].rotation_mode = "QUATERNION"

# BVH 관절의 '방향 자식': 매핑된 자식 > 이름에 middle 이 든 자식(손) > 유일한 자식 > 첫 자식.
# 가져오기가 정한 본 축(첫 자식 방향)이 아니라 이 자식 방향을 본 방향으로 쓴다 — 손은 엄지 쪽이 첫 자식이라 23° 틀어진다
def dir_child(s):
    kids = list(src.pose.bones[s].children)
    if not kids: return None
    for c in kids:
        if c.name in mapping: return c.name
    for c in kids:
        if "middle" in c.name.lower(): return c.name
    return kids[0].name

def rest_joint_dir(s, c):
    ps, pc = src.data.bones[s], src.data.bones[c]
    return (Ws3 @ (pc.matrix_local.translation - ps.matrix_local.translation)).normalized()

# 팔다리 보정 M: 우리 쉬는 본 틀 → BVH 쉬는 본 틀. 방향(y)만 맞추는 최소 회전이면 비틀림(롤)이 안 옮겨져 손바닥 방향이 어긋난다.
# 그래서 두 뼈대에 같은 규칙으로 '기준 틀'을 세운다: y = 본 방향, z = 세계 앞(-Y)을 본 축에 수직으로 투영, x = y × z.
# 본이 앞을 거의 향하면(발) 앞 대신 위(+Z)를 기준으로 쓴다. M = Fs·Ft⁻¹ 이면 방향과 롤 기준이 함께 맞아 BVH 의 비틀림이 그대로 온다.
# (처음엔 방향만 맞추는 rotation_difference 를 ds→dt 로 거꾸로 넣어 오차가 쉬는 차이의 정확히 2배로 나왔다)
def canon_frame(y):
    y = y.normalized()
    ref = Vector((0, -1, 0))
    if abs(ref.dot(y)) > 0.9: ref = Vector((0, 0, 1))
    z = (ref - y * ref.dot(y)).normalized(); x = y.cross(z).normalized()
    F = Matrix.Identity(3); F.col[0] = x; F.col[1] = y; F.col[2] = z
    return F
M = {}
for s, t in order:
    c = dir_child(s)
    if t.startswith(LIMB) and c:
        ds = rest_joint_dir(s, c)
        dt = (rest_rot(rig.pose.bones[t], Wt3) @ Vector((0, 1, 0))).normalized()
        M[t] = canon_frame(ds) @ canon_frame(dt).inverted() if A.get("roll", True) else dt.rotation_difference(ds).to_matrix()
    else:
        M[t] = Matrix.Identity(3)

# 루트: BVH 루트의 쉬는 위치는 원점이라(OFFSET 0) 첫 프레임 자세로 기준을 잡는다. 키 비율 = 우리 엉덩이 높이 / BVH 첫 프레임 엉덩이 높이
hips_src = next((s for s, t in mapping.items() if t == "torso"), None)
torso = rig.pose.bones.get("torso")
sc.frame_set(f0); bpy.context.view_layer.update()
k = 1.0; hips_ref = None
if hips_src and torso is not None:
    hips_ref = (Ws @ src.pose.bones[hips_src].matrix).translation.copy()
    tz = (Wt @ torso.bone.matrix_local).translation.z
    k = (tz / hips_ref.z) if hips_ref.z > 1e-6 else 1.0
torso_rest_w = (Wt @ torso.bone.matrix_local).translation.copy() if torso is not None else None

# 검증 짝. dir: BVH 관절 s 의 자식 중 매핑된 것(없으면 유일한 자식) ↔ 우리 DEF 본. end: 손발
DEF_OF = {"upper_arm_fk": "DEF-upper_arm", "forearm_fk": "DEF-forearm", "hand_fk": "DEF-hand",
          "thigh_fk": "DEF-thigh", "shin_fk": "DEF-shin", "foot_fk": "DEF-foot"}
DIR, END = {}, {}
for s, t in mapping.items():
    for fk, deff in DEF_OF.items():
        if t.startswith(fk):
            d = deff + t[len(fk):]
            if d in rig.pose.bones:
                c = dir_child(s)
                if c:
                    DIR[s] = (c, d)
                if fk in ("hand_fk", "foot_fk"):
                    END[s] = d
dir_err = {d: [] for _, d in DIR.values()}
dir_rest = {}
roll_err = {d: [] for _, d in DIR.values() if d.startswith(('DEF-hand', 'DEF-foot'))}
end_err = {d: [] for d in END.values()}
src_foot_z = []
toe_xy, src_toe_xy = {}, {}   # 발 미끄러짐 계산용(프레임별 발끝 xy)
foot_z = []   # 프레임마다 가장 낮은 발끝 z: 음수면 바닥을 뚫고, 늘 양수면 떠 있다

def joint_dir(s, child):
    return ((Ws @ src.pose.bones[child].matrix).translation - (Ws @ src.pose.bones[s].matrix).translation).normalized()
def def_dir(d):
    pb = rig.pose.bones[d]
    return ((Wt @ pb.tail) - (Wt @ pb.head)).normalized()

# 쉬는 자세의 방향 차이(옮기기 전 상수 오프셋 — M 이 없으면 이만큼이 프레임마다 남는다)
for s, (c, d) in DIR.items():
    ds = rest_joint_dir(s, c)
    b = rig.data.bones[d]
    dt = (Wt3 @ (b.tail_local - b.head_local)).normalized()
    dir_rest[d] = round(__import__("math").degrees(ds.angle(dt)), 1) if ds.length and dt.length else None

for f in range(f0, f1 + 1):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    for s, t in order:
        ps, pt = src.pose.bones[s], rig.pose.bones[t]
        delta = pose_rot(ps, Ws3) @ rest_rot(ps, Ws3).inverted()
        Rt = Wt3.inverted() @ (delta @ M[t] @ rest_rot(pt, Wt3))
        newM = Rt.to_4x4(); newM.translation = pt.matrix.translation
        if t == "torso" and hips_ref is not None:
            dp = ((Ws @ ps.matrix).translation - hips_ref) * k
            newM.translation = Wt.inverted() @ (torso_rest_w + dp)
        pt.matrix = newM
        bpy.context.view_layer.update()
        pt.keyframe_insert("rotation_quaternion", frame=f)
        if t == "torso": pt.keyframe_insert("location", frame=f)
    for s, (c, d) in DIR.items():
        dir_err[d].append(joint_dir(s, c).angle(def_dir(d)))
    # 롤 검증(손·발): 쉬는 자세의 기준 틀 x 축을 델타로 돌린 것과 지금 본의 x 축(같은 규칙의 틀) 차이 — 방향은 이미 같으니 남는 건 비틀림
    for s, (c, d) in DIR.items():
        if not (d.startswith("DEF-hand") or d.startswith("DEF-foot")): continue
        ps = src.pose.bones[s]; delta = pose_rot(ps, Ws3) @ rest_rot(ps, Ws3).inverted()
        want_x = delta @ canon_frame(rest_joint_dir(s, c)).col[0]       # BVH 가 요구하는 x(비틀림 포함)
        Rd = (Wt3 @ rig.pose.bones[d].matrix.to_3x3())
        Rd0 = (Wt3 @ rig.data.bones[d].matrix_local.to_3x3())
        have_x = Rd @ Rd0.inverted() @ canon_frame((Wt3 @ (rig.data.bones[d].tail_local - rig.data.bones[d].head_local))).col[0]
        roll_err[d].append(want_x.angle(have_x) if want_x.length and have_x.length else 0.0)
    feet = [d for d in END.values() if d.startswith("DEF-foot")]
    for s_, d in END.items():
        if d.startswith("DEF-foot"):
            toe_xy.setdefault(d, []).append((Wt @ rig.pose.bones[d].tail).xy.copy())
            src_toe_xy.setdefault(d, []).append(((Ws @ src.pose.bones[dir_child(s_) or s_].matrix).translation * k).xy.copy())
    if feet:
        foot_z.append(min((Wt @ rig.pose.bones[d].tail).z for d in feet))
        sfeet = [s for s, d in END.items() if d.startswith("DEF-foot")]
        src_foot_z.append(min((Ws @ src.pose.bones[dir_child(s) or s].matrix).translation.z * k for s in sfeet))
    if hips_src:
        hs = (Ws @ src.pose.bones[hips_src].matrix).translation
        ht = (Wt @ torso.matrix).translation
        for s, d in END.items():
            rel_s = ((Ws @ src.pose.bones[s].matrix).translation - hs) * k
            rel_t = (Wt @ rig.pose.bones[d].matrix).translation - ht
            end_err[d].append((rel_s - rel_t).length)

# 변형 검사(토큰 0): 렌더 프레임에서 메시 모서리가 쉬는 자세보다 얼마나 늘어났나. 2배 넘는 모서리는 가중치 구멍(정점이 옛 자리에 남음)이나
# 오배정이다 — mannequiny A 포즈에서 손끝 152개 정점이 무가중치라 224배 막대가 생긴 걸 이걸로 잡았다
mesh = next((o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig), None)
stretch = None
if mesh is not None and A.get("render_frames"):
    rest_co = [v.co.copy() for v in mesh.data.vertices]
    edges = [(e.vertices[0], e.vertices[1]) for e in mesh.data.edges]
    rest_len = [(rest_co[a] - rest_co[b]).length for a, b in edges]
    worst, over2, per_frame = 0.0, 0, {}
    for f in A["render_frames"]:
        sc.frame_set(int(f)); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg).data
        co = [v.co.copy() for v in ev.vertices]
        rat = [(co[a] - co[b]).length / r for (a, b), r in zip(edges, rest_len) if r > 1e-6]
        mx = max(rat) if rat else 0.0; n2 = sum(1 for x in rat if x > 2.0)
        worst = max(worst, mx); over2 = max(over2, n2); per_frame[int(f)] = {"max_ratio": round(mx, 2), "edges_over_2x": n2}
    stretch = {"max_edge_ratio": round(worst, 2), "edges_over_2x": over2, "edges": len(edges), "per_frame": per_frame}

# 원본 BVH 아마추어는 대조용으로 남기되 렌더·뷰포트에서 숨긴다
src.hide_render = True; src.hide_viewport = True
bpy.ops.wm.save_as_mainfile(filepath=A["out_blend"])

# 확인용 렌더: 네 프레임을 정면 옆 45° 에서(워크벤치, 토큰 0)
frames_out = []
if A.get("render_frames"):
    from math import degrees
    H = float(A.get("height", 1.8))
    # BVH 뼈대를 빨간 막대로 우리 옆(+X 로 0.9H)에 세운다. 아마추어 자체는 렌더에 안 나오므로 본마다 기둥을 Copy Transforms 로 붙인다
    import math
    src.hide_render = False; src.hide_viewport = False
    red = bpy.data.materials.new("bw_src_bone"); red.diffuse_color = (0.9, 0.15, 0.1, 1)
    # 본 축이 아니라 관절→자식 관절 선분을 그린다(가져온 본 축은 첫 자식만 향해 엉덩이·가슴에서 헛선이 생긴다):
    # 기둥 밑을 부모 관절에 붙이고(Copy Location) 자식 관절까지 늘인다(Stretch To)
    for b in src.pose.bones:
        for c in b.children:
            bpy.ops.mesh.primitive_cylinder_add(radius=0.012 * H / 1.8, depth=1.0, location=(0, 0.5, 0), rotation=(math.pi / 2, 0, 0), vertices=6)
            cyl = bpy.context.active_object; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); cyl.data.materials.append(red)
            cl = cyl.constraints.new("COPY_LOCATION"); cl.target = src; cl.subtarget = b.name; cl.head_tail = 0.0
            st = cyl.constraints.new("STRETCH_TO"); st.target = src; st.subtarget = c.name; st.head_tail = 0.0; st.rest_length = 1.0; st.volume = "NO_VOLUME"
    src.location.x += 0.9 * H; src.scale = (k, k, k)   # 키 비율을 맞춰 옆에 세운다
    sc.frame_set(f0); bpy.context.view_layer.update()
    center = (Wt @ torso.matrix).translation.copy() if torso is not None else Vector((0, 0, H / 2))
    center.z = H / 2
    bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
    dist = H * 2.0; loc = Vector((center.x + 0.75 * dist, center.y - 0.9 * dist, center.z + 0.25 * dist))
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.active_object
    cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (center - loc).to_track_quat("-Z", "Y")
    cam.data.type = "ORTHO"; cam.data.ortho_scale = H * 2.2; sc.camera = cam
    center.x += 0.45 * H; loc.x += 0.45 * H; cam.location = loc
    sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = int(A.get("size", 512))
    sc.display.shading.color_type = "MATERIAL"; sc.display.shading.light = "STUDIO"
    sc.render.image_settings.file_format = "PNG"
    for f in A["render_frames"]:
        sc.frame_set(int(f)); bpy.context.view_layer.update()
        # 카메라가 루트 이동을 따라가게 한다
        c2 = (Wt @ torso.matrix).translation.copy() if torso is not None else center
        c2.z = H / 2; c2.x += 0.45 * H; cam.location = c2 + (loc - center)
        p = os.path.join(A["out_dir"], f"retarget_f{int(f):04d}.png")
        sc.render.filepath = p; bpy.ops.render.render(write_still=True); frames_out.append(p)

# 발 미끄러짐(토큰 0): BVH 발끝이 거의 안 움직이는 프레임(디딤발, 한 프레임 이동 < 키의 0.5%)에서 우리 발끝이 수평으로 움직인 거리.
# FK 만 옮기면 비율 차이만큼 디딤발이 밀린다 — 이 값이 크면 IK 발 고정이 필요하다
slide = None
if toe_xy:
    H_ = float(A.get("height", 1.8)); thr = H_ * 0.005
    ours, theirs, n_st = 0.0, 0.0, 0
    for d in toe_xy:
        a, b = toe_xy[d], src_toe_xy[d]
        for i in range(1, len(a)):
            if (b[i] - b[i - 1]).length < thr:
                ours += (a[i] - a[i - 1]).length; theirs += (b[i] - b[i - 1]).length; n_st += 1
    slide = {"stance_frames": n_st, "our_slide_cm": round(ours * 100, 2), "bvh_slide_cm": round(theirs * 100, 2),
             "per_stance_frame_mm": round(ours / n_st * 1000, 2) if n_st else None}

from math import degrees
roll_summary = {d: {"mean_deg": round(degrees(sum(v) / len(v)), 1), "max_deg": round(degrees(max(v)), 1)} for d, v in roll_err.items() if v}
dir_summary = {d: {"mean_deg": round(degrees(sum(v) / len(v)), 1), "max_deg": round(degrees(max(v)), 1), "rest_deg": dir_rest.get(d)}
               for d, v in dir_err.items() if v}
end_summary = {d: {"mean_cm": round(sum(v) / len(v) * 100, 2), "max_cm": round(max(v) * 100, 2)} for d, v in end_err.items() if v}
alld = [x for v in dir_err.values() for x in v]; alle = [x for v in end_err.values() for x in v]
done({"mapped": mapping, "unmapped": [b.name for b in src.data.bones if b.name not in mapping],
      "frames": [f0, f1], "scale": round(k, 4), "dir_deg": dir_summary, "roll_deg": roll_summary, "roll": bool(A.get("roll", True)), "end_cm": end_summary,
      "mean_dir_deg": round(degrees(sum(alld) / len(alld)), 2) if alld else None,
      "mean_end_cm": round(sum(alle) / len(alle) * 100, 2) if alle else None,
      "foot_contact": {"min_toe_z_cm": round(min(foot_z) * 100, 2), "max_min_toe_z_cm": round(max(foot_z) * 100, 2),
                       "bvh_min_toe_z_cm": round(min(src_foot_z) * 100, 2), "bvh_max_min_toe_z_cm": round(max(src_foot_z) * 100, 2),
                       "mean_diff_cm": round(sum(a - b for a, b in zip(foot_z, src_foot_z)) / len(foot_z) * 100, 2),
                       "frames_below_floor": sum(1 for z in foot_z if z < -0.01), "frames": len(foot_z)} if foot_z else None,
      "stretch": stretch, "foot_slide": slide, "renders": frames_out, "out_blend": A["out_blend"]}, A["result"])
