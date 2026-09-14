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
# 표준 BVH 는 Y 가 위(-Z 앞). Blender 가 내보낸 BVH 는 Z 가 위(Y 앞)라 그대로 읽으면 옆으로 눕는다 → bvh_up 옵션
_fwd, _up = ("Y", "Z") if A.get("bvh_up", "y") == "z" else ("-Z", "Y")
bpy.ops.import_anim.bvh(filepath=A["bvh"], axis_forward=_fwd, axis_up=_up, update_scene_fps=True, update_scene_duration=True)
src = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o not in before)
sc = bpy.context.scene
act = src.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
mapping = A["mapping"]   # BVH 본 → 우리 FK 본 (pipeline 이 bench 정규화로 만든다)
mapping = {s: t for s, t in mapping.items() if s in src.pose.bones and t in rig.pose.bones}
Ws, Wt = src.matrix_world, rig.matrix_world
Ws3, Wt3 = Ws.to_3x3(), Wt.to_3x3()
LIMB = ("upper_arm_fk", "forearm_fk", "hand_fk", "thigh_fk", "shin_fk", "foot_fk", "front_thigh_fk", "front_shin_fk", "front_foot_fk")

# 팔다리를 FK 로 돌린다(기본은 IK 라 FK 본을 돌려도 메시가 안 움직인다). 사족은 앞다리(front_thigh_parent)도
for n in ("upper_arm_parent.L", "upper_arm_parent.R", "thigh_parent.L", "thigh_parent.R", "front_thigh_parent.L", "front_thigh_parent.R"):
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
    b = src.data.bones[s]
    kids = list(b.children)
    for c in kids:
        if c.name in mapping: return c.name
    for c in kids:
        if "middle" in c.name.lower(): return c.name
    # 매핑된 자식도 middle 도 없으면: 꼬리와 머리가 겹치는 자식(가져오기가 첫 자식으로 꼬리를 정한 경우)만 방향으로 인정한다.
    # 꼬리가 어떤 자식과도 안 겹치면 End Site 로 정한 꼬리 → 본 축이 진짜 방향(늑대 Head 의 자식은 귀뿐이다)
    for c in kids:
        if (c.head_local - b.tail_local).length < 1e-4: return c.name
    return None

def rest_joint_dir(s, c):
    """BVH 관절 s 의 쉬는 방향: 자식 c 가 있으면 관절→자식, 없으면(End Site 만 있는 끝 관절) 가져오기가 정한 본 축(End Site 방향)"""
    if c is None:
        return (Ws3 @ src.data.bones[s].matrix_local.to_3x3() @ Vector((0, 1, 0))).normalized()
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
# 몸통 사슬(가슴·목·머리)은 방향 보정 M 을 쓰지 않는다. 본 축이 리그마다 다른 곳을 가리켜서(kimodo Head 는 턱 58°, Quaternius 늑대 Head 는
# 주둥이 쪽 아래 15°, Rigify 는 정수리 쪽 위 15°; kimodo 목은 앞으로 17° 기움) 맞추면 오히려 머리·목이 숙여진다(둘 다 렌더로 확인).
# 대신 델타의 기준을 바인드 자세가 아니라 '클립에서 가장 전형적인 프레임'(방향이 클립 평균에 가장 가까운 프레임)으로 잡는다:
# 그 프레임에서 우리 본은 우리 쉬는 자세 그대로이고, 클립 안에서 벗어난 만큼만 옮겨진다. 바인드 자세가 애니와 다른 리그(늑대: 바인드는
# 머리를 들고 있는데 걷기는 내린다 → 순수 델타면 머리가 땅을 본다)에서 이게 맞는다. 한계: 클립 내내 숙인 동작(먹기)은 숙임이 사라진다.
AXIAL = ("chest", "neck", "head")
axial_ref = {}   # t → 기준 프레임의 소스 월드 회전(Rs_ref)
def _src_dir_at(s):
    return (Ws3 @ src.pose.bones[s].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
_ax = [(s, t) for s, t in order if t in AXIAL]
if _ax:
    dirs = {t: [] for _, t in _ax}; rots = {t: [] for _, t in _ax}
    for f in range(f0, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        for s, t in _ax:
            dirs[t].append(_src_dir_at(s)); rots[t].append(pose_rot(src.pose.bones[s], Ws3).copy())
    for _, t in _ax:
        mean = sum(dirs[t], Vector()) / len(dirs[t])
        i = min(range(len(dirs[t])), key=lambda i: dirs[t][i].angle(mean) if mean.length > 1e-6 else 0.0)
        axial_ref[t] = (rots[t][i], f0 + i)
def axial_src_child(s):
    """몸통 사슬 관절의 방향 자식: 매핑된 자식 > 유일한 자식 > None(End Site 본 축 또는 부모→관절). 턱·눈·귀 같은 곁가지는 방향이 아니다"""
    b = src.data.bones[s]; kids = list(b.children)
    for c in kids:
        if c.name in mapping: return c.name
    if len(kids) == 1 and (kids[0].head_local - b.tail_local).length < 1e-4: return kids[0].name
    return None
def axial_rest_dir(s):
    """믿을 수 있는 방향만 돌려준다: 매핑된 자식·유일한 자식 → 관절→자식, 자식 없음 → 본 축(End Site). 자식이 여럿(턱·눈·귀)이면 None —
    가져오기가 꼬리를 자식 평균으로 정해 축이 엉뚱하다(kimodo Head 는 턱 쪽 58°). 그때는 보정 없이 순수 델타"""
    c = axial_src_child(s)
    if c: return rest_joint_dir(s, c)
    b = src.data.bones[s]
    if not b.children: return rest_joint_dir(s, None)
    return None
def axial_def_dir(t):
    """컨트롤 t 의 머리에 가장 가까운 DEF 척추·목·머리 본의 쉬는 방향(월드)"""
    h = Wt @ rig.data.bones[t].head_local
    cands = [b for b in rig.data.bones if b.use_deform and b.name.startswith(("DEF-spine", "DEF-neck", "DEF-head"))]
    if not cands: return None
    b = min(cands, key=lambda b: ((Wt @ b.head_local) - h).length)
    return (Wt3 @ (b.tail_local - b.head_local)).normalized()
M = {}
axial_debug = {}
for s, t in order:
    c = dir_child(s)
    if t.startswith(LIMB):
        ds = rest_joint_dir(s, c)
        dt = (rest_rot(rig.pose.bones[t], Wt3) @ Vector((0, 1, 0))).normalized()
        M[t] = canon_frame(ds) @ canon_frame(dt).inverted() if A.get("roll", True) else dt.rotation_difference(ds).to_matrix()
    elif t in AXIAL and t in axial_ref:
        M[t] = Matrix.Identity(3)
        axial_debug[t] = {"src": s, "ref_frame": axial_ref[t][1]}
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

# 다리 IK 모드(legs="ik"): FK 회전만 옮기면 두 뼈대의 다리 비율 차이가 그대로 발 위치 오차가 된다(늑대: 허벅지가 1.4배 길어 비절 40cm).
# 표준 리타겟처럼 몸·팔은 FK, 다리는 발 IK 로 BVH 발목(비절) 위치를 좇게 한다. Rigify 는 발목(비절) 아래가 foot_ik 컨트롤에
# 통째로 붙어 있으므로(사람 limbs.leg 는 발목에, 늑대 limbs.paw 는 발끝에 컨트롤이 있지만 둘 다 강체) "발목을 P 로 옮기고 D 만큼 돌린다"는
# 강체 변환을 foot_ik 의 쉬는 행렬에 그대로 적용하면 된다: foot_ik(f) = T(P)·D·T(-발목_rest)·foot_ik_rest.
# 목표 P: xy 는 엉덩이 기준 상대 위치(키 비율), z 는 바닥 기준(BVH z × 키 비율) — 디딤발이 바닥에 닿도록.
LEGS = A.get("legs", "auto")
IK_LEGS = []   # (parent_prop, foot_ik, s_foot|None, s_shin, DEF 발 본, DEF 고관절 본, 소스 고관절, 다리 길이 비)
if LEGS in ("ik", "auto"):
    inv_map = {t: s for s, t in mapping.items()}
    hips_z_s = (Ws @ src.data.bones[hips_src].matrix_local).translation.z if hips_src else None
    ik_skipped = []
    for side in ("L", "R"):
        for pre in ("", "front_"):
            par, fik, ffk, fsh, dfoot = f"{pre}thigh_parent.{side}", f"{pre}foot_ik.{side}", f"{pre}foot_fk.{side}", f"{pre}shin_fk.{side}", f"DEF-{pre}foot.{side}"
            dhip, s_hip = f"DEF-{pre}thigh.{side}", inv_map.get(f"{pre}thigh_fk.{side}")
            if par in rig.pose.bones and fik in rig.pose.bones and dfoot in rig.pose.bones and dhip in rig.pose.bones and s_hip and (ffk in inv_map or fsh in inv_map):
                # 다리 길이 비: 우리 고관절→발목(비절) 쉬는 거리 / 소스 고관절→발목 쉬는 거리. 발목 목표를 '고관절 기준 상대 위치 × 이 비'로 두면
                # 어느 프레임에서도 닿을 수 있고(같은 굽힘), 엉덩이 높이 비(k)와 다리 비가 어긋난 만큼만 발이 뜨거나 뚫린다
                # 기준점은 발목이 아니라 발끝이다: 발목으로 맞추면 발 길이 비율 차이만큼 발이 뜬다(늑대 비절이 소스보다 낮아 발끝이 22cm 떴다).
                # 소스 발끝 = 발 관절의 자식 관절(사람 ToeBase) 또는 본 꼬리(End Site). 우리 발끝 = 그에 맞춰 DEF-toe 머리(발볼) 또는 꼬리(끝)
                s_end = inv_map.get(ffk) or inv_map[fsh]
                c_end = dir_child(s_end)
                p_end_s = (Ws @ src.data.bones[c_end].matrix_local).translation if c_end else (Ws @ src.data.bones[s_end].tail_local)
                dtoe = dfoot.replace("foot", "toe")
                if dtoe in rig.data.bones:
                    anchor_rest = Wt @ (rig.data.bones[dtoe].head_local if c_end else rig.data.bones[dtoe].tail_local)
                else:
                    anchor_rest = Wt @ rig.data.bones[dfoot].tail_local
                p_hip_s = (Ws @ src.data.bones[s_hip].matrix_local).translation
                # auto: 소스 발끝이 바닥 근처가 아니면(사슬이 손목·발목에서 끝남) IK 목표가 될 발끝이 없다 → 이 다리는 FK
                if LEGS == "auto" and hips_z_s and (p_end_s.z - (Ws @ src.data.bones[s_hip].matrix_local).translation.z * 0 ) > 0.2 * hips_z_s:
                    ik_skipped.append(fik); continue
                l_s = (p_end_s - p_hip_s).length
                l_t = (anchor_rest - (Wt @ rig.data.bones[dhip].head_local)).length
                k_leg = (l_t / l_s) if l_s > 1e-6 else k
                IK_LEGS.append((par, fik, inv_map.get(ffk), inv_map.get(fsh), dfoot, dhip, s_hip, k_leg, s_end, c_end, anchor_rest))
                rig.pose.bones[par]["IK_FK"] = 0.0
                rig.pose.bones[fik].rotation_mode = "QUATERNION"
    # 발 방향 보정 M(foot_fk 에 이미 계산됨)이 없으면(앞발 소스 없음) 정강이 소스의 델타를 그대로 쓴다
    for leg in IK_LEGS:
        ffk = leg[1].replace("_ik.", "_fk.")
        if ffk not in M:
            M[ffk] = Matrix.Identity(3)

# 검증 짝. dir: BVH 관절 s 의 자식 중 매핑된 것(없으면 유일한 자식) ↔ 우리 DEF 본. end: 손발
DEF_OF = {"upper_arm_fk": "DEF-upper_arm", "forearm_fk": "DEF-forearm", "hand_fk": "DEF-hand",
          "thigh_fk": "DEF-thigh", "shin_fk": "DEF-shin", "foot_fk": "DEF-foot",
          "front_thigh_fk": "DEF-front_thigh", "front_shin_fk": "DEF-front_shin", "front_foot_fk": "DEF-front_foot"}
DIR, END = {}, {}
for s, t in mapping.items():
    for fk, deff in DEF_OF.items():
        if t.startswith(fk):
            d = deff + t[len(fk):]
            if d in rig.pose.bones:
                DIR[s] = (dir_child(s), d)
                if fk in ("hand_fk", "foot_fk", "front_foot_fk"):
                    END[s] = d
dir_err = {d: [] for _, d in DIR.values()}
dir_rest = {}
roll_err = {d: [] for _, d in DIR.values() if d.startswith(('DEF-hand', 'DEF-foot'))}
end_err = {d: [] for d in END.values()}
src_foot_z = []
toe_xy, src_toe_xy = {}, {}   # 발 미끄러짐 계산용(프레임별 발끝 xy)
foot_z = []   # 프레임마다 가장 낮은 발끝 z: 음수면 바닥을 뚫고, 늘 양수면 떠 있다

def joint_dir(s, child):
    if child is None:
        return (Ws3 @ src.pose.bones[s].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
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

src_floor = {}
if IK_LEGS:
    for f in range(f0, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        for leg in IK_LEGS:
            fik, s_end, c_end = leg[1], leg[8], leg[9]
            z = (Ws @ src.pose.bones[c_end].matrix).translation.z if c_end else (Ws @ src.pose.bones[s_end].tail).z
            src_floor[fik] = min(src_floor.get(fik, z), z)
    lo = min(src_floor.values()); src_floor = {kk: lo for kk in src_floor}   # 네 발 공통 바닥

for f in range(f0, f1 + 1):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    for s, t in order:
        ps, pt = src.pose.bones[s], rig.pose.bones[t]
        ref = axial_ref[t][0] if t in axial_ref else rest_rot(ps, Ws3)   # 몸통 사슬은 전형 프레임, 나머지는 바인드 자세 기준
        delta = pose_rot(ps, Ws3) @ ref.inverted()
        Rt = Wt3.inverted() @ (delta @ M[t] @ rest_rot(pt, Wt3))
        newM = Rt.to_4x4(); newM.translation = pt.matrix.translation
        if t == "torso" and hips_ref is not None:
            dp = ((Ws @ ps.matrix).translation - hips_ref) * k
            newM.translation = Wt.inverted() @ (torso_rest_w + dp)
        pt.matrix = newM
        bpy.context.view_layer.update()
        pt.keyframe_insert("rotation_quaternion", frame=f)
        if t == "torso": pt.keyframe_insert("location", frame=f)
    for par, fik, s_foot, s_shin, dfoot, dhip, s_hip, k_leg, s_end, c_end, anchor_rest in IK_LEGS:
        ps = src.pose.bones[s_foot] if s_foot is not None else src.pose.bones[s_shin]
        p_s = (Ws @ src.pose.bones[c_end].matrix).translation if c_end else (Ws @ src.pose.bones[s_end].tail)
        # 목표 발끝 = 우리 고관절(지금 프레임, FK 로 이미 움직인 몸통을 따른다) + (소스 발끝 − 소스 고관절) × 다리 길이 비.
        # z 는 바닥 기준: 소스 발끝의 클립 최저점을 바닥으로 보고(본이 발끝을 지나쳐 바닥 아래로 그려진 리그가 있다) 키 비로 줄인다
        hip_t = (Wt @ rig.pose.bones[dhip].matrix).translation
        hip_s = (Ws @ src.pose.bones[s_hip].matrix).translation
        P = hip_t + (p_s - hip_s) * k_leg
        if A.get("ik_ground", True): P.z = (p_s.z - src_floor.get(fik, 0.0)) * k
        ffk = fik.replace("_ik.", "_fk.")
        D = (pose_rot(ps, Ws3) @ rest_rot(ps, Ws3).inverted()) @ M.get(ffk, Matrix.Identity(3))
        pik = rig.pose.bones[fik]
        ik_rest_w = Wt @ pik.bone.matrix_local
        new_w = Matrix.Translation(P) @ D.to_4x4() @ Matrix.Translation(-anchor_rest) @ ik_rest_w
        pik.matrix = Wt.inverted() @ new_w
        bpy.context.view_layer.update()
        pik.keyframe_insert("location", frame=f); pik.keyframe_insert("rotation_quaternion", frame=f)
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
    feet = [d for d in END.values() if "foot" in d]
    def our_toe(d):   # 발 사슬의 가장 낮은 끝: DEF-toe 꼬리(사족 발끝), 없으면 DEF-foot 꼬리
        toe = d.replace("foot", "toe")
        return Wt @ (rig.pose.bones[toe].tail if toe in rig.pose.bones else rig.pose.bones[d].tail)
    def src_toe(s_):   # BVH 발끝: 자식 관절이 있으면 그 관절, 없으면 본 꼬리(End Site)
        c_ = dir_child(s_)
        return ((Ws @ src.pose.bones[c_].matrix).translation if c_ else (Ws @ src.pose.bones[s_].tail)) * k
    for s_, d in END.items():
        if "foot" in d:
            toe_xy.setdefault(d, []).append(our_toe(d).xy.copy())
            src_toe_xy.setdefault(d, []).append(src_toe(s_).xy.copy())
    if feet:
        foot_z.append(min(our_toe(d).z for d in feet))
        src_foot_z.append(min(src_toe(s_).z for s_, d in END.items() if "foot" in d))
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
      "axial": axial_debug, "legs": LEGS, "ik_legs": [x[1] for x in IK_LEGS], "ik_skipped": ik_skipped if LEGS in ("ik", "auto") else [], "leg_scale": {x[1]: round(x[7], 3) for x in IK_LEGS}, "src_floor_z": round(min(src_floor.values()), 4) if src_floor else None, "stretch": stretch, "foot_slide": slide, "renders": frames_out, "out_blend": A["out_blend"]}, A["result"])
