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
# 판정 기준면: 원본 메시는 옷·신발·머리가 겹친 여러 껍질이고 목·소매에 구멍이 뚫려 있어 안/밖 판정이 둘 다 틀린다
# (법선 방식은 몸 안의 점을 밖으로, 광선 방식은 구멍으로 새어 밖으로 읽는다 — 둘 다 실측으로 확인).
# 복셀 리메시로 구멍을 메운 "부피 메시"를 한 번 만들어 그것으로만 판정한다.
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.object.duplicate(); vol = bpy.context.active_object; vol.name = "bw_volume"
_vm = vol.modifiers.new("remesh", "REMESH"); _vm.mode = "VOXEL"; _vm.voxel_size = max(0.004, A["landmarks"]["height"] / 150); volume_voxel = round(_vm.voxel_size, 4)
bpy.ops.object.modifier_apply(modifier="remesh")
vinv = vol.matrix_world.inverted()
def is_inside(p, margin=0.0):
    """부피 메시 기준: 가장 가까운 면의 법선 방향으로 margin 보다 더 나가 있으면 밖."""
    ok, loc, nrm, _ = vol.closest_point_on_mesh(vinv @ p)
    if not ok: return True
    d = (p - (vol.matrix_world @ loc)).dot((vol.matrix_world.to_3x3() @ nrm).normalized())
    return d <= margin

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
# 사람 메타리그 전용: 늑대(사족)는 척추가 spine..spine.011 이라 spine.003 이 등 한가운데다.
# 거기에 목·머리 정렬을 걸면 척추 사슬이 끊겨 Rigify 가 "disjoint" 로 실패한다(벤치마크로 확인)
chain = ["spine.003", "spine.004", "spine.005", "spine.006"]
if preset == "humanoid" and all(n in eb for n in chain):
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
PINNED = set(A.get("pinned") or [])   # 사용자가 --pin 으로 직접 고정한 본은 어떤 보정도 건드리지 않는다
for side in ("L", "R"):
    ax = L.get(f"arm_axis_{side}") or []
    if len(ax) < 3: continue
    for up, low in ((f"upper_arm.{side}", f"forearm.{side}"), (f"forearm.{side}", f"hand.{side}")):
        if up in eb and low in eb and low not in PINNED and up not in PINNED:
            d, q, r = nearest_on_axis(eb[low].head, ax)
            if d > r * 0.5:
                eb[low].head = q; eb[up].tail = q; axis_snapped.append(low)
# 다리: 팔과 달리 거의 수직이므로 높이(z)는 그대로 두고 좌우·앞뒤(x, y)만 다리 중심선으로 맞춘다
for side in ("L", "R"):
    lax = L.get(f"leg_axis_{side}") or []
    if len(lax) < 3: continue
    def leg_center(z):
        for i in range(len(lax) - 1):
            a, b = lax[i], lax[i + 1]
            if a[2] <= z <= b[2]:
                t = (z - a[2]) / (b[2] - a[2]) if b[2] > a[2] else 0
                return Vector((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z)), a[3] + (b[3] - a[3]) * t
        near = lax[0] if z < lax[0][2] else lax[-1]
        return Vector((near[0], near[1], z)), near[3]
    for up, low in ((f"thigh.{side}", f"shin.{side}"), (f"shin.{side}", f"foot.{side}")):
        if up in eb and low in eb and low not in PINNED and up not in PINNED:
            q, r = leg_center(eb[low].head.z)
            if r > 0 and (eb[low].head - q).length > r * 0.6:
                eb[low].head = q; eb[up].tail = q; axis_snapped.append(low)
# 보정 2: 목표에 없는 자식 본(손가락·발가락·뒤꿈치)은 가장 가까운 목표 조상 본의 이동(평행이동+회전+길이 비율)을 그대로 따른다.
# 이걸 안 하면 손가락이 메타리그 기본 위치에 남아 메시 밖에 뜬다
propagated = []
for b in list(eb):
    if b.name in before or b.name in PINNED: continue
    anc = b.parent
    while anc is not None and anc.name not in before: anc = anc.parent
    if anc is None or anc.name.startswith("spine"): continue   # 척추 목표의 길이 비율을 상체 전체에 번지게 하지 않는다(팔다리·손발 하위만)
    h0, t0 = before[anc.name]; h1, t1 = anc.head.copy(), anc.tail.copy(); d0, d1 = t0 - h0, t1 - h1
    if d0.length < 1e-6 or d1.length < 1e-6: continue
    M = Matrix.Translation(h1) @ d0.rotation_difference(d1).to_matrix().to_4x4() @ Matrix.Scale(d1.length / d0.length, 4) @ Matrix.Translation(-h0)
    b.transform(M, scale=True, roll=True); propagated.append(b.name)
# 보정 2b: 척추 중간 본(spine.001~.003)은 양 끝(spine tail ↔ spine.004 head) 사이에 원래 길이 비율대로 다시 편다
mid = ["spine.001", "spine.002", "spine.003"]
if preset == "humanoid" and all(n in eb for n in ["spine", "spine.004"] + mid):
    a_, b_ = eb["spine"].tail.copy(), eb["spine.004"].head.copy(); lens = [orig_len[n] for n in mid]; tot = sum(lens) or 1.0; acc = 0.0
    for n, ln in zip(mid, lens):
        eb[n].head = a_ + (b_ - a_) * (acc / tot); acc += ln; eb[n].tail = a_ + (b_ - a_) * (acc / tot)
# 보정 3: 손(과 손가락)이 메시 손끝을 넘으면 손 본 head 를 중심으로 줄인다. 손 방향으로 광선을 쏴 메시를 빠져나가는 거리를 잰다
inv = obj.matrix_world.inverted(); finger_scale = {}
center_y = 0.0   # 가져오기에서 다리 중앙을 y=0 으로 맞춘다
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
# 보정 4: 그래도 메시 밖에 있는 점(head/tail)은 메시 안으로 당긴다.
# 안/밖 판정은 "광선 통과 횟수"로 한다(홀수면 안). 가장 가까운 면의 법선으로 판정하면 게임 메시처럼 옷·신발이 겹친
# 여러 껍질에서는 몸 안의 점도 "밖"으로 잘못 나온다(실측: 정강이 중간점이 5.2cm 밖으로 오판).
def pull_inside(p, inset=0.012):
    """메시 밖의 점만 안으로 당긴다: 가장 가까운 표면에서 inset 만큼 안쪽 → 광선 판정으로 확인, 실패하면 절반씩 줄여 재시도,
    그래도 안 되면 같은 높이의 몸 중심축 쪽으로 조금씩 옮긴다(얇은 껍질·법선 오류 대비)."""
    if is_inside(p): return p, False
    ok, loc, nrm, _ = vol.closest_point_on_mesh(vinv @ p)
    if not ok: return p, False
    loc = vol.matrix_world @ loc; nrm = (vol.matrix_world.to_3x3() @ nrm).normalized()
    for k in range(4):
        q = loc - nrm * (inset / (2 ** k))
        if is_inside(q): return q, True
    axis = Vector((0.0, center_y, p.z))   # 몸 중심축(좌우 0, 앞뒤 중앙)
    for k in range(1, 11):
        q = p + (axis - p) * (k / 10.0)
        if is_inside(q): return q, True
    return loc - nrm * (inset / 8), True
snapped_inside = []
skip_inside = {b.name for h in ("hand.L", "hand.R") if h in eb for b in eb if any(pb.name == h for pb in b.parent_recursive)}
for b in list(eb):
    if b.name in skip_inside or b.name in PINNED: continue   # 손가락: 보정 3 이 손 실루엣 안으로 넣었다. 부피 메시(복셀 1.2cm)는 손가락을 뭉개서 잘못 당긴다
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
# 고정(pin)은 마지막에 다시 적용한다: 중간 보정(사슬 재결합·길이·굽힘)이 건드렸을 수 있다. 사용자가 찍은 값이 최종 결정권을 갖는다
pin_applied = []
for name in sorted(PINNED):
    t = T.get(name)
    if not t or name not in eb: continue
    b = eb[name]
    if "head" in t:
        b.head = Vector(t["head"])
        if name in joined and b.parent: b.parent.tail = b.head.copy()   # 붙어 있던 사슬은 같이 따라간다
    if "tail" in t:
        b.tail = Vector(t["tail"])
        for ch in b.children:
            if ch.name in joined: ch.head = b.tail.copy()
    pin_applied.append(name)

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
def clear_groups():
    for g in list(obj.vertex_groups): obj.vertex_groups.remove(g)
    for md in [m for m in obj.modifiers if m.type == "ARMATURE"]: obj.modifiers.remove(md)
weight_method = "auto"
unweighted, sums = weigh("ARMATURE_AUTO"); auto_unweighted = unweighted; proxy_unweighted = None
if unweighted > len(obj.data.vertices) * 0.05:
    # Bone Heat 실패(게임 메시는 머리·몸·옷·가방이 따로 겹쳐 있어 자주 실패한다) → 복셀 리메시 대리 메시(한 덩어리 닫힌 표면)에서
    # 자동 가중치를 풀고 원본 정점으로 전송한다(가장 가까운 면 보간). 리깅 도구들이 쓰는 표준 우회법
    clear_groups()
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.duplicate(); proxy = bpy.context.active_object; proxy.name = "bw_proxy"
    rm = proxy.modifiers.new("remesh", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = max(0.005, A["landmarks"]["height"] / 90)
    bpy.ops.object.modifier_apply(modifier="remesh")
    bpy.ops.object.select_all(action="DESELECT"); proxy.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    pvg = {g.index: g.name for g in proxy.vertex_groups}
    proxy_unweighted = sum(1 for v in proxy.data.vertices if sum(g.weight for g in v.groups if pvg.get(g.group, "").startswith("DEF-")) < 1e-4)
    if proxy_unweighted <= len(proxy.data.vertices) * 0.05:
        # data_transfer 는 활성(active) 오브젝트 → 선택된 오브젝트로 옮긴다: 대리 메시가 활성, 원본이 선택
        bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); proxy.select_set(True); bpy.context.view_layer.objects.active = proxy
        bpy.ops.object.data_transfer(use_reverse_transfer=False, data_type="VGROUP_WEIGHTS", vert_mapping="POLYINTERP_NEAREST", layers_select_src="ALL", layers_select_dst="NAME")
        obj.parent = rig; obj.matrix_parent_inverse = rig.matrix_world.inverted()
        am = obj.modifiers.new("Armature", "ARMATURE"); am.object = rig
        weight_method = "auto_proxy"
    bpy.data.objects.remove(proxy)
    vg = {g.index: g.name for g in obj.vertex_groups}; sums = []; unweighted = 0
    for v in obj.data.vertices:
        w = sum(g.weight for g in v.groups if vg.get(g.group, "").startswith("DEF-")); sums.append(w)
        if w < 1e-4: unweighted += 1
    if weight_method != "auto_proxy" or unweighted > len(obj.data.vertices) * 0.05:
        clear_groups(); weight_method = "envelope_fallback"   # 대리 메시도 실패 → 엔벨로프(항상 붙지만 품질 낮음). 보고서에 표시
        unweighted, sums = weigh("ARMATURE_ENVELOPE")
# 정규화: 정점별 변형 가중치 합을 1 로(엔벨로프는 합이 1 이 아니다)
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
vg = {g.index: g.name for g in obj.vertex_groups}; sums = []; unweighted = 0
for v in obj.data.vertices:
    w = sum(g.weight for g in v.groups if vg.get(g.group, "").startswith("DEF-")); sums.append(w)
    if w < 1e-4: unweighted += 1
# 가중치 누출 검사(토큰 0): 복셀 대리 메시는 가까운 조각을 붙이므로 팔 본이 몸통으로 샐 수 있다(Maya 는 복셀 위 측지 거리로 막는다).
# (A) 몸통 한가운데(가슴~배) 정점이 팔 본에게 받는 가중치 — 빗장뼈(shoulder)는 원래 가슴 위를 덮으므로 뺀다.
# (B) 지배 본이 정점에서 키의 15% 보다 멀면 의심 — 가방·날개 같은 부속물은 정상적으로 걸리므로 게이트가 아니라 기록만 한다.
_H = A["landmarks"]["height"]; _z0 = A["landmarks"]["ground_z"]
_seg = {b.name: (rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones if b.use_deform}
def _dist(name, p):
    a, b = _seg[name]; ab = b - a
    if ab.length_squared < 1e-12: return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length
_ARM = ("DEF-upper_arm", "DEF-forearm", "DEF-hand")
vgn = {g.index: g.name for g in obj.vertex_groups}
leak_arm, torso_verts, far_dom = 0, 0, 0
for v in obj.data.vertices:
    pw = obj.matrix_world @ v.co
    w = {vgn.get(g.group, ""): g.weight for g in v.groups if vgn.get(g.group, "").startswith("DEF-")}
    if not w: continue
    t = sum(w.values()) or 1.0
    if abs(pw.x) < 0.04 * _H and _z0 + 0.45 * _H < pw.z < _z0 + 0.70 * _H:
        torso_verts += 1
        if sum(val for k, val in w.items() if k.startswith(_ARM)) / t > 0.15: leak_arm += 1
    dom = max(w, key=w.get)
    if w[dom] / t > 0.5 and dom in _seg and _dist(dom, pw) > 0.15 * _H: far_dom += 1
mn = Vector(A["stats"]["min"]); mx = Vector(A["stats"]["max"]); pad = 0.12
outside = [b.name for b in rig.data.bones if b.use_deform and not all(mn[i] - pad <= (rig.matrix_world @ b.head_local)[i] <= mx[i] + pad for i in range(3))]
def _outside(p):
    return not is_inside(p, margin=0.003)
# 손가락 본은 이 검사에서 뺀다: 판정용 부피 메시(복셀 1.2cm)가 손가락을 한 덩어리로 뭉개서 전부 "밖"으로 읽힌다.
# 손가락은 보정 3(손 실루엣 안으로 축소)이 원본 메시 기준으로 이미 처리한다
FINGER = ("DEF-f_", "DEF-thumb", "DEF-palm")
_check = [b for b in rig.data.bones if b.use_deform and not b.name.startswith(FINGER)]
finger_bones_skipped = sum(1 for b in rig.data.bones if b.use_deform and b.name.startswith(FINGER))
# 본을 5등분해 중간점도 검사한다: 끝점만 보면 비스듬한 본이 중간에 메시를 뚫고 나가는 걸 놓친다(실측으로 확인)
def _bone_points(b):
    h, t = rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local
    return [h + (t - h) * (i / 4.0) for i in range(5)]
deform_outside_mesh = sorted({b.name for b in _check for pt in _bone_points(b) if _outside(pt)})
pairs = [(b.name, b.name[:-1] + "R") for b in rig.data.bones if b.use_deform and b.name.endswith(".L") and (b.name[:-1] + "R") in rig.data.bones]
asym = [round(((rig.data.bones[l].head_local * Vector((-1, 1, 1))) - rig.data.bones[r].head_local).length, 4) for l, r in pairs]
stats = {"metarig_bones": len(meta.data.bones), "rig_bones": len(rig.data.bones), "deform_bones": sum(1 for b in rig.data.bones if b.use_deform),
         "weight_method": weight_method, "auto_unweighted": auto_unweighted, "proxy_unweighted": proxy_unweighted, "height": A["landmarks"]["height"], "moved_bones": moved, "removed_face_bones": removed_face, "clamped_targets": sorted(set(clamped)), "fixed_zero_length": fixed, "bent_joints": bent, "axis_snapped": axis_snapped, "propagated_bones": len(propagated), "finger_scale": finger_scale, "snapped_inside": len(snapped_inside), "rejoined": rejoined, "pinned": sorted(PINNED), "pin_applied": pin_applied, "volume_voxel": volume_voxel, "snapped_inside_bones": snapped_inside[:12], "unweighted_verts": unweighted, "weight_sum_min": round(min(sums), 4), "weight_sum_max": round(max(sums), 4),
         "weight_leak_arm_torso": leak_arm, "weight_leak_torso_verts": torso_verts, "weight_far_dominant": far_dom, "bones_outside_bbox": outside[:20], "deform_outside_mesh": len(deform_outside_mesh), "finger_bones_skipped": finger_bones_skipped, "deform_outside_mesh_bones": deform_outside_mesh[:12], "symmetry_pairs": len(pairs), "symmetry_max_error": max(asym) if asym else 0}
bpy.data.objects.remove(vol)   # 판정용 부피 메시는 저장하지 않는다
bpy.ops.wm.save_as_mainfile(filepath=A["out_blend"])
done({"stats": stats, "rig": rig.name, "blend": A["out_blend"]}, A["result"])
