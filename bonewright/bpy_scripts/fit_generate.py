"""2~3단계: 메타리그 추가 → 관절 목표(JSON)대로 주요 본 이동 → Rigify 생성 → 자동 가중치 → 통계."""
import bpy, json
from mathutils import Vector
from _common import args, done
A = args()
bpy.ops.wm.open_mainfile(filepath=A["blend"])
bpy.ops.preferences.addon_enable(module="rigify")
obj = bpy.data.objects["character"]
T = A["targets"]            # {"bone": {"head":[x,y,z], "tail":[x,y,z]}} 일부만 와도 된다
preset = A.get("preset", "humanoid")
op = {"humanoid": "armature_human_metarig_add", "quadruped": "armature_wolf_metarig_add"}[preset]
getattr(bpy.ops.object, op)(); meta = bpy.context.active_object; meta.name = "metarig"
# 전체 크기: 메타리그 높이를 메시 높이에 맞춘다
mh = max(b.tail_local.z for b in meta.data.bones) - min(b.head_local.z for b in meta.data.bones)
scale = A["landmarks"]["height"] / mh if mh else 1.0
meta.scale = (scale, scale, scale); meta.location.z = A["landmarks"]["ground_z"]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT"); eb = meta.data.edit_bones; moved = []; clamped = []
# 얼굴 리그는 기본 제외(v0.1): 메시 머리와 안 맞으면 본이 튀어나온다. rig.face=true 면 유지
FACE = {"face", "eye", "lip", "brow", "nose", "cheek", "jaw", "ear", "chin", "tongue", "teeth", "temple", "forehead", "lid"}
removed_face = 0
if not A.get("face", False):
    # 첫 토큰으로 판별한다("ear" 부분 일치는 forearm 까지 지운다)
    for b in [b for b in eb if b.name.split(".")[0].split("_")[0] in FACE]:
        eb.remove(b); removed_face += 1
# 머리·목 사슬을 메시 높이에 맞춘다: 목 밑 = 어깨 위, 정수리 = 메시 꼭대기. 사슬이 끊기지 않게 앞 본 tail 과 다음 본 head 를 함께 맞춘다
L = A["landmarks"]
chain = ["spine.003", "spine.004", "spine.005", "spine.006"]
if all(n in eb for n in chain):
    z0, z3 = L["shoulder_z"] + 0.03, L["top_z"] - 0.01
    zs = [z0, z0 + (z3 - z0) * 0.3, z0 + (z3 - z0) * 0.45, z3]
    y = eb["spine.004"].head.y
    eb["spine.003"].tail = Vector((0, y, zs[0]))
    for k, name in enumerate(chain[1:]):
        eb[name].head = Vector((0, y, zs[k])); eb[name].tail = Vector((0, y, zs[k + 1]))
lo = Vector(A["stats"]["min"]) + Vector((0.02, 0.02, 0.0)); hi = Vector(A["stats"]["max"]) - Vector((0.02, 0.02, 0.0))
def clamp(name, v):
    c = Vector((min(max(v[i], lo[i]), hi[i]) for i in range(3)))
    if (c - Vector(v)).length > 1e-6: clamped.append(name)
    return c
for name, t in T.items():
    if name in eb:
        if "head" in t: eb[name].head = clamp(name, t["head"])   # 목표가 메시 상자를 벗어나면 안쪽으로 자른다(모델 답도 동일)
        if "tail" in t: eb[name].tail = clamp(name, t["tail"])
        moved.append(name)
# 안전장치: 길이 0 에 가까운 본은 부모 방향으로 살짝 늘린다(Rigify 는 0 길이 본에서 실패한다)
fixed = []
for b in eb:
    if (b.tail - b.head).length < 0.005:
        d = (b.parent.tail - b.parent.head) if b.parent and (b.parent.tail - b.parent.head).length > 0.01 else Vector((0, 0, 1))
        b.tail = b.head + d.normalized() * 0.02; fixed.append(b.name)
# 안전장치 2: 팔꿈치·무릎이 일직선이면 Rigify 가 폴 방향을 못 정한다 → 팔꿈치는 뒤(+Y), 무릎은 앞(-Y)으로 2cm 굽힌다
bent = []
for up, low, dy in (("upper_arm.L", "forearm.L", 0.02), ("upper_arm.R", "forearm.R", 0.02), ("thigh.L", "shin.L", -0.02), ("thigh.R", "shin.R", -0.02)):
    if up in eb and low in eb:
        a, b = eb[up].tail - eb[up].head, eb[low].tail - eb[low].head
        if a.length > 0 and b.length > 0 and a.cross(b).length < 0.05 * a.length * b.length:   # 약 3도 미만
            joint = eb[low].head + Vector((0, dy, 0))
            eb[low].head = joint; eb[up].tail = joint; bent.append(low)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.pose.rigify_generate(); rig = bpy.context.active_object
# 스키닝
def weigh(kind):
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type=kind)
    vg = {g.index: g.name for g in obj.vertex_groups}
    unweighted, sums = 0, []
    for v in obj.data.vertices:
        s = sum(g.weight for g in v.groups if vg.get(g.group, "").startswith("DEF-"))
        sums.append(s)
        if s < 1e-4: unweighted += 1
    return unweighted, sums
weight_method = "auto"
unweighted, sums = weigh("ARMATURE_AUTO"); auto_unweighted = unweighted
if unweighted > len(obj.data.vertices) * 0.05:
    # Bone Heat 실패(겹친 조각·비매니폴드 메시) → 엔벨로프로 대체. 품질은 낮지만 항상 붙는다. 보고서에 표시.
    for g in list(obj.vertex_groups): obj.vertex_groups.remove(g)
    weight_method = "envelope_fallback"
    unweighted, sums = weigh("ARMATURE_ENVELOPE")
# 정규화: 정점별 변형 가중치 합을 1 로(엔벨로프는 합이 1 이 아니다)
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
vg = {g.index: g.name for g in obj.vertex_groups}; sums = []; unweighted = 0
for v in obj.data.vertices:
    w = sum(g.weight for g in v.groups if vg.get(g.group, "").startswith("DEF-")); sums.append(w)
    if w < 1e-4: unweighted += 1
mn = Vector(A["stats"]["min"]); mx = Vector(A["stats"]["max"]); pad = 0.12
outside = [b.name for b in rig.data.bones if b.use_deform and not all(mn[i] - pad <= (rig.matrix_world @ b.head_local)[i] <= mx[i] + pad for i in range(3))]
pairs = [(b.name, b.name[:-1] + "R") for b in rig.data.bones if b.use_deform and b.name.endswith(".L") and (b.name[:-1] + "R") in rig.data.bones]
asym = [round(((rig.data.bones[l].head_local * Vector((-1, 1, 1))) - rig.data.bones[r].head_local).length, 4) for l, r in pairs]
stats = {"metarig_bones": len(meta.data.bones), "rig_bones": len(rig.data.bones), "deform_bones": sum(1 for b in rig.data.bones if b.use_deform),
         "weight_method": weight_method, "auto_unweighted": auto_unweighted, "moved_bones": moved, "removed_face_bones": removed_face, "clamped_targets": sorted(set(clamped)), "fixed_zero_length": fixed, "bent_joints": bent, "unweighted_verts": unweighted, "weight_sum_min": round(min(sums), 4), "weight_sum_max": round(max(sums), 4),
         "bones_outside_bbox": outside[:20], "symmetry_pairs": len(pairs), "symmetry_max_error": max(asym) if asym else 0}
bpy.ops.wm.save_as_mainfile(filepath=A["out_blend"])
done({"stats": stats, "rig": rig.name, "blend": A["out_blend"]}, A["result"])
