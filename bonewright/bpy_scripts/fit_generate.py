"""2~3단계: 메타리그 추가 → 관절 목표(JSON)대로 주요 본 이동 → Rigify 생성 → 자동 가중치 → 통계."""
import bpy, json
from mathutils import Vector, Matrix
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
# 처음에 부모 tail 에 붙어 있던 본(연결 여부와 무관)은 보정이 끝난 뒤에도 붙여 둔다. Rigify 사슬 리그는 head 가 부모 tail 과 어긋나면 "disjoint" 로 실패한다
orig_len = {b.name: (b.tail - b.head).length for b in eb}
joined = {b.name for b in eb if b.parent and (b.head - b.parent.tail).length < 1e-4}
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
before = {n: (eb[n].head.copy(), eb[n].tail.copy()) for n in T if n in eb}   # 자식 본을 같이 옮기기 위해 원래 위치를 기억
for name, t in T.items():
    if name in eb:
        if "head" in t: eb[name].head = clamp(name, t["head"])   # 목표가 메시 상자를 벗어나면 안쪽으로 자른다(모델 답도 동일)
        if "tail" in t: eb[name].tail = clamp(name, t["tail"])
        moved.append(name)
# 보정 1: 팔꿈치·손목을 팔 중심선(analysis.arm_axis) 위로. 표본 반지름의 절반보다 벗어났으면 중심선 위 가장 가까운 점으로 옮긴다
axis_snapped = []
def nearest_on_axis(pt, ax):
    best = None
    for i in range(len(ax) - 1):
        a, b = Vector(ax[i][:3]), Vector(ax[i + 1][:3]); ab = b - a
        k = max(0.0, min(1.0, (pt - a).dot(ab) / ab.length_squared)) if ab.length_squared > 1e-9 else 0.0
        q = a + ab * k; d = (pt - q).length; r = ax[i][3] + (ax[i + 1][3] - ax[i][3]) * k
        if best is None or d < best[0]: best = (d, q, r)
    return best
for side in ("L", "R"):
    ax = L.get(f"arm_axis_{side}") or []
    if len(ax) < 3: continue
    for up, low in ((f"upper_arm.{side}", f"forearm.{side}"), (f"forearm.{side}", f"hand.{side}")):
        if up in eb and low in eb:
            d, q, r = nearest_on_axis(eb[low].head, ax)
            if d > r * 0.5:
                eb[low].head = q; eb[up].tail = q; axis_snapped.append(low)
# 보정 2: 목표에 없는 자식 본(손가락·발가락·뒤꿈치)은 가장 가까운 목표 조상 본의 이동(평행이동+회전+길이 비율)을 그대로 따른다.
# 이걸 안 하면 손가락이 메타리그 기본 위치에 남아 메시 밖에 뜬다
propagated = []
for b in list(eb):
    if b.name in before: continue
    anc = b.parent
    while anc is not None and anc.name not in before: anc = anc.parent
    if anc is None or anc.name.startswith("spine"): continue   # 척추 목표의 길이 비율을 상체 전체에 번지게 하지 않는다(팔다리·손발 하위만)
    h0, t0 = before[anc.name]; h1, t1 = anc.head.copy(), anc.tail.copy(); d0, d1 = t0 - h0, t1 - h1
    if d0.length < 1e-6 or d1.length < 1e-6: continue
    M = Matrix.Translation(h1) @ d0.rotation_difference(d1).to_matrix().to_4x4() @ Matrix.Scale(d1.length / d0.length, 4) @ Matrix.Translation(-h0)
    b.transform(M, scale=True, roll=True); propagated.append(b.name)
# 보정 2b: 척추 중간 본(spine.001~.003)은 양 끝(spine tail ↔ spine.004 head) 사이에 원래 길이 비율대로 다시 편다
mid = ["spine.001", "spine.002", "spine.003"]
if all(n in eb for n in ["spine", "spine.004"] + mid):
    a_, b_ = eb["spine"].tail.copy(), eb["spine.004"].head.copy(); lens = [orig_len[n] for n in mid]; tot = sum(lens) or 1.0; acc = 0.0
    for n, ln in zip(mid, lens):
        eb[n].head = a_ + (b_ - a_) * (acc / tot); acc += ln; eb[n].tail = a_ + (b_ - a_) * (acc / tot)
# 보정 3: 손(과 손가락)이 메시 손끝을 넘으면 손 본 head 를 중심으로 줄인다. 손 방향으로 광선을 쏴 메시를 빠져나가는 거리를 잰다
inv = obj.matrix_world.inverted(); finger_scale = {}
for side in ("L", "R"):
    hn = f"hand.{side}"
    if hn not in eb: continue
    hb = eb[hn]; h = hb.head.copy(); d = (hb.tail - h).normalized()
    hit, loc, _, _ = obj.ray_cast(inv @ h, (inv.to_3x3() @ d).normalized())
    if not hit: continue
    exit_d = ((obj.matrix_world @ loc) - h).length
    sub = [hb] + [b for b in eb if any(p.name == hn for p in b.parent_recursive)]
    far = max(max((b.head - h).dot(d), (b.tail - h).dot(d)) for b in sub)
    if far > exit_d - 0.01 and far > 1e-6:
        sc_ = max(0.2, (exit_d - 0.01) / far); M = Matrix.Translation(h) @ Matrix.Scale(sc_, 4) @ Matrix.Translation(-h)
        for b in sub: b.transform(M, scale=True, roll=True)
        finger_scale[side] = round(sc_, 3)
# 보정 4: 그래도 메시 밖에 있는 점(head/tail)은 가장 가까운 표면에서 1.2cm 안쪽으로 당긴다(뚫린 메시면 법선이 틀릴 수 있어 통계로 남긴다)
def pull_inside(p, inset=0.012):
    ok, loc, nrm, _ = obj.closest_point_on_mesh(inv @ p)
    if not ok: return p, False
    loc = obj.matrix_world @ loc; nrm = (obj.matrix_world.to_3x3() @ nrm).normalized()
    if (p - loc).dot(nrm) <= 0: return p, False
    return loc - nrm * inset, True
snapped_inside = []
for b in list(eb):
    for attr in ("head", "tail"):
        q, moved_pt = pull_inside(getattr(b, attr))
        if moved_pt: setattr(b, attr, q); snapped_inside.append(f"{b.name}.{attr}")
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
# 보정 5: 원래 부모 tail 에 붙어 있던 본은 다시 붙인다(부모부터 순서대로)
rejoined = []
for b in sorted(eb, key=lambda b: len(b.parent_recursive)):
    if b.name in joined and b.parent and (b.head - b.parent.tail).length > 1e-5:
        b.head = b.parent.tail.copy(); rejoined.append(b.name)
# 진단: 부모 tail 과 어긋난 본을 로그에 남긴다(Rigify 사슬 오류 추적용)
for b in eb:
    if b.parent and (b.head - b.parent.tail).length > 1e-5 and (b.name in joined or b.use_connect):
        print("BW chain gap:", b.name, "connect", b.use_connect, "gap", round((b.head - b.parent.tail).length, 4), list(b.head), list(b.parent.tail))
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
def _outside(p):
    ok, loc, nrm, _ = obj.closest_point_on_mesh(inv @ p)
    return ok and ((p - (obj.matrix_world @ loc)).dot((obj.matrix_world.to_3x3() @ nrm)) > 0.003)
deform_outside_mesh = sorted({b.name for b in rig.data.bones if b.use_deform for pt in (b.head_local, b.tail_local) if _outside(rig.matrix_world @ pt)})
pairs = [(b.name, b.name[:-1] + "R") for b in rig.data.bones if b.use_deform and b.name.endswith(".L") and (b.name[:-1] + "R") in rig.data.bones]
asym = [round(((rig.data.bones[l].head_local * Vector((-1, 1, 1))) - rig.data.bones[r].head_local).length, 4) for l, r in pairs]
stats = {"metarig_bones": len(meta.data.bones), "rig_bones": len(rig.data.bones), "deform_bones": sum(1 for b in rig.data.bones if b.use_deform),
         "weight_method": weight_method, "auto_unweighted": auto_unweighted, "moved_bones": moved, "removed_face_bones": removed_face, "clamped_targets": sorted(set(clamped)), "fixed_zero_length": fixed, "bent_joints": bent, "axis_snapped": axis_snapped, "propagated_bones": len(propagated), "finger_scale": finger_scale, "snapped_inside": len(snapped_inside), "rejoined": rejoined, "snapped_inside_bones": snapped_inside[:12], "unweighted_verts": unweighted, "weight_sum_min": round(min(sums), 4), "weight_sum_max": round(max(sums), 4),
         "bones_outside_bbox": outside[:20], "deform_outside_mesh": len(deform_outside_mesh), "deform_outside_mesh_bones": deform_outside_mesh[:12], "symmetry_pairs": len(pairs), "symmetry_max_error": max(asym) if asym else 0}
bpy.ops.wm.save_as_mainfile(filepath=A["out_blend"])
done({"stats": stats, "rig": rig.name, "blend": A["out_blend"]}, A["result"])
