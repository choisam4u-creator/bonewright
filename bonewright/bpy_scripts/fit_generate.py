"""2~3단계: 메타리그 추가 → 관절 목표(JSON)대로 주요 본 이동 → Rigify 생성 → 자동 가중치 → 통계."""
import bpy, json, re
from mathutils import Vector, Matrix
from _common import args, done
A = args()
bpy.ops.wm.open_mainfile(filepath=A["blend"])
bpy.ops.preferences.addon_enable(module="rigify")
obj = bpy.data.objects["character"]
T = A["targets"]            # {"bone": {"head":[x,y,z], "tail":[x,y,z]}} 일부만 와도 된다
# 들고 있는 소품·장식 정점(bw_attachment). 스키닝 단계에서 정점 그룹이 통째로 지워지므로 여기서 떠 둔다
_attg = obj.vertex_groups.get("bw_attachment")
ATTACH_VERTS = {v.index for v in obj.data.vertices if _attg and any(g.group == _attg.index for g in v.groups)}
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

GENERIC = preset == "generic"
# 보고용 기본값. 일반 리그 경로에서는 아래 사람·개과 전용 보정이 통째로 건너뛴다
moved = []; clamped = []; fixed = []; bent = []; axis_snapped = []; snapped_inside = []
propagated = []; rejoined = []; resymmetrized = []; removed_face = 0; finger_scale = None
PINNED = set(); pin_applied = {}; rest_pose = {"applied": False}


_ANATOMY = {"spine", "chest", "neck", "head", "shoulder", "upper_arm", "forearm", "hand",
            "thigh", "shin", "foot", "toe", "front_thigh", "front_shin", "front_foot", "tail"}


def build_generic_metarig(joints):
    """원본 뼈대를 **그대로 베낀** 메타리그. 사람·개과 메타리그에 맞출 수 없는 몸(용·유령·문어·블롭)을 위한 길이다.

    원칙은 하나다: **사슬이면 컨트롤을 만든다.** 관절 이름을 알아볼 필요도, 사람 비율을 가정할 필요도 없다.
      · 본마다 `basic.super_copy` 를 붙인다 → 본 하나에 컨트롤 하나, 전부 변형 본이 된다
      · 부모 tail 에 붙어 있는(use_connect) 사슬은 `limbs.simple_tentacle` 로 올린다 → 한 덩어리로 휜다
    Rigify 4.x 부터 본 컬렉션에 UI 줄이 하나라도 없으면 생성이 실패하므로 컬렉션을 하나 만들어 둔다."""
    arm = bpy.data.armatures.new("metarig"); mt = bpy.data.objects.new("metarig", arm)
    bpy.context.collection.objects.link(mt)
    bpy.ops.object.select_all(action="DESELECT"); mt.select_set(True); bpy.context.view_layer.objects.active = mt
    bpy.ops.object.mode_set(mode="EDIT")
    e = arm.edit_bones
    zs = [v["head"][2] for v in joints.values()] + [v["tail"][2] for v in joints.values()]
    H = (max(zs) - min(zs)) or 1.0
    for n, v in joints.items():
        b = e.new(n); b.head = Vector(v["head"]); b.tail = Vector(v["tail"])
        if (b.tail - b.head).length < 1e-4:      # 길이 0 본은 Rigify 가 거부한다
            b.tail = b.head + Vector((0, 0, H * 0.002))
    conn = {}
    for n, v in joints.items():
        pn = v.get("parent")
        if pn and pn in e:
            e[n].parent = e[pn]
            # 부모 tail 에 거의 붙어 있으면 사슬로 잇는다. Rigify 사슬 리그는 붙은 자식만 사슬로 센다
            if (e[n].head - e[pn].tail).length < H * 0.01:
                e[n].use_connect = True
        conn[n] = e[n].use_connect
    bpy.ops.object.mode_set(mode="OBJECT")
    kids = {}
    for n, v in joints.items():
        kids.setdefault(v.get("parent"), []).append(n)
    assign = {n: "basic.super_copy" for n in joints}
    starts = [n for n, v in joints.items() if not v.get("parent") or len(kids.get(v.get("parent"), [])) != 1 or not conn.get(n)]
    for s in starts:
        ch = [s]
        while len(kids.get(ch[-1], [])) == 1 and conn.get(kids[ch[-1]][0]):
            ch.append(kids[ch[-1]][0])
        # 역할 이름이 붙은 사슬(thigh.L, forearm.R …)은 촉수 리그로 묶지 않는다.
        # 촉수 리그는 컨트롤 이름을 새로 지어서, 이름으로 본을 찾는 동작 리타겟이 못 찾는다
        if any(x.split(".")[0] in _ANATOMY for x in ch):
            continue
        if len(ch) >= 2 and all(assign.get(x) == "basic.super_copy" for x in ch):
            assign[ch[0]] = "limbs.simple_tentacle"
            for x in ch[1:]:
                assign.pop(x, None)
    for n, v in joints.items():
        # 원본이 변형에 안 쓰는 본(Root 같은 정리용)은 변형 본으로 만들지 않는다.
        # 이걸 안 하면 몸 밖 원점에 있는 Root 가 '메시 밖 변형 본'으로 잡혀 멀쩡한 리그가 needs_review 가 된다
        if n in mt.data.bones and v.get("deform") is False:
            mt.data.bones[n].use_deform = False
    for n, t in assign.items():
        if n in mt.pose.bones:
            mt.pose.bones[n].rigify_type = t
            if joints.get(n, {}).get("deform") is False:
                try:      # 리그 타입별로 이름이 다르다. 없으면 use_deform 표시만으로 간다
                    mt.pose.bones[n].rigify_parameters.make_deform = False
                except Exception:
                    pass
    col = arm.collections.new("Controls")
    for b in arm.bones:
        col.assign(b)
    col.rigify_ui_row = 1
    return mt, assign


if GENERIC:
    meta, _assign = build_generic_metarig(A["source_joints"])
    moved = sorted(_assign)
else:

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
    # **실패 기록(2026-09-19): 원본에 없는 손가락 마디 지우기.** 여기에 그 코드가 있었다.
    # 착상: 메타리그는 손가락을 세 마디로 두는데 원본이 두 마디만 주면 남은 마디가 사람 손 기준
    # 기본 자리에 떠 있으면서 살을 가져간다(토끼 `DEF-thumb.03.L` 가중치 1.00). 타깃 없는 끝 마디를
    # 지웠더니 토끼는 늘어남 12.19 → 11.30배로 **조금** 나아졌다.
    # **그런데 다른 자산이 크게 나빠졌다**: godot_player 1.87배/0.0% → 8.46배/3.17%,
    # quat_pp_41j 2.09/0.04% → 11.85/2.13%, rigged_figure 1.61/0.0% → 3.72/6.51%.
    # 손가락에 흩어져 있던 손 살이 손 본 하나로 뭉치면서 손목·손등이 통째로 끌린 것이다.
    # (KayKit 마법사는 변형 본이 35개로 줄어 리깅 게이트까지 실패했다)
    # 남은 마디가 떠 있는 건 사실이지만, 지우는 것보다 **손 살을 나눠 가지는 값**이 더 컸다.
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
    meta_sym = {b.name: (b.head.copy(), b.tail.copy()) for b in eb}              # 손대기 전 메타리그(좌우 대칭 판정용)
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
    SKIP = set(A.get("skip") or [])   # 디버그: 특정 보정을 끈다(이분 탐색용)
    PINNED = set(A.get("pinned") or [])   # 사용자가 --pin 으로 직접 고정한 본은 어떤 보정도 건드리지 않는다
    # 중심선 스냅은 사람 전용이다. arm_axis·leg_axis 는 '팔다리가 몸 중앙에 수직으로 선다'는 사람 가정으로 계산돼
    # 네 발 동물에선 엉뚱한 선이 나온다. 실측: 늑대 비절 목표 [0.325,0.574,0.651] 이 이 스냅 때문에
    # [0.128,-1.105,1.284] 로 끌려가 앞다리 근처에 박혔다(오차 60%)
    AXIS_OK = preset == "humanoid" and "axis" not in SKIP
    for side in (("L", "R") if AXIS_OK else ()):
        ax = L.get(f"arm_axis_{side}") or []
        if len(ax) < 3: continue
        for up, low in ((f"upper_arm.{side}", f"forearm.{side}"), (f"forearm.{side}", f"hand.{side}")):
            if up in eb and low in eb and low not in PINNED and up not in PINNED:
                d, q, r = nearest_on_axis(eb[low].head, ax)
                if d > r * 0.5:
                    eb[low].head = q; eb[up].tail = q; axis_snapped.append(low)
    # 다리: 팔과 달리 거의 수직이므로 높이(z)는 그대로 두고 좌우·앞뒤(x, y)만 다리 중심선으로 맞춘다
    for side in (("L", "R") if AXIS_OK else ()):
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
    helpers = bool(A.get("propagate_helpers"))   # 척추에 달린 살집 보조 본(breast/pelvis)도 따라가게 할지
    for b in (() if "propagate" in SKIP else list(eb)):
        if b.name in before or b.name in PINNED: continue
        anc = b.parent
        while anc is not None and anc.name not in before: anc = anc.parent
        # 척추 목표의 길이 비율을 상체 사슬 전체에 번지게 하지 않는다(팔다리·손발 하위만).
        # 예외: breast/pelvis 는 척추에 매달린 살집 보조 본이라, 사람 비율이 안 통하는 모델(--from-skeleton)에서는
        # 부모 척추를 따라가야 한다. 안 따라가면 사람 기본 자리에 남아 엉뚱한 데를 잡는다(로봇: breast 가 머리 정점 117개를
        # 가져갔다). 반대로 사람형 기본 경로에서는 기본 자리가 이미 맞아, 따라가게 하면 오히려 나빠진다
        # (cesium_man 좌우 일치 0.999 → 0.853) → 그래서 이 예외는 helpers 옵션이 켜졌을 때만이다
        if anc is None or (anc.name.startswith("spine") and not (helpers and b.name.startswith(("breast", "pelvis")))): continue
        h0, t0 = before[anc.name]; h1, t1 = anc.head.copy(), anc.tail.copy(); d0, d1 = t0 - h0, t1 - h1
        if d0.length < 1e-6 or d1.length < 1e-6: continue
        # breast/pelvis 는 회전을 빼고 평행이동+길이 비율만 따른다. 척추 방향이 조금만 틀어져도
        # rotation_difference 가 축 둘레로 아무 방향이나 골라서 좌우가 뒤집힌다(좌우 일치 0.675 로 확인)
        rot = Matrix.Identity(4) if b.name.startswith(("breast", "pelvis")) else d0.rotation_difference(d1).to_matrix().to_4x4()
        M = Matrix.Translation(h1) @ rot @ Matrix.Scale(d1.length / d0.length, 4) @ Matrix.Translation(-h0)
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
    for side in (() if "fingers" in SKIP else ("L", "R")):
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
    # 안쪽으로 당기기 **직전** 상태를 기억한다. 4b 가 되돌릴 대상은 '당기기가 만든 좌우 어긋남' 뿐이다 —
    # 목표(--pin 으로 한쪽만 고정한 경우 등)가 만든 어긋남까지 되돌리면 사용자가 찍은 좌표가 반대쪽으로 번진다
    pre_sym = {b.name: (b.head.copy(), b.tail.copy()) for b in eb}
    snapped_inside = []
    skip_inside = {b.name for h in ("hand.L", "hand.R") if h in eb for b in eb if any(pb.name == h for pb in b.parent_recursive)}

    # 우리가 옮긴 본과 그 자식만 당긴다. 예전엔 메타리그의 모든 본을 당겼는데, 손대지 않은 본까지 표면으로 끌려가
    # 사슬이 끊겼다(사족 프리셋이 Rigify 생성에서 통째로 실패한 원인 — 이분 탐색으로 확인)
    # breast/pelvis 는 목표를 안 줘도 몸 안으로 당긴다 — 메타리그 기본 자리가 몸 밖일 수 있다(말: 둘 다 몸 밖)
    touched = set(T) | set(propagated) | {b.name for b in eb if b.name.startswith(("breast", "pelvis"))}
    for b in (() if "inside" in SKIP else [x for x in eb if x.name in touched]):
        if b.name in skip_inside or b.name in PINNED: continue   # 손가락: 보정 3 이 손 실루엣 안으로 넣었다. 부피 메시(복셀 1.2cm)는 손가락을 뭉개서 잘못 당긴다
        for attr in ("head", "tail"):
            q, moved_pt = pull_inside(getattr(b, attr))
            if moved_pt: setattr(b, attr, q); snapped_inside.append(f"{b.name}.{attr}")
    # 보정 4b: 손대기 전에 좌우가 딱 대칭이던 짝은 보정 뒤에도 대칭으로 되돌린다. pull_inside 는 좌우가 각자
    # '가장 가까운 면'을 골라서, 같은 자리에서 시작한 본도 서로 다른 데로 보낸다(말: pelvis 좌우가 47cm 어긋났다)
    _MIR = Vector((-1, 1, 1))
    resymmetrized = []
    for lb in [b for b in eb if b.name.endswith(".L") and b.name[:-1] + "R" in eb and b.name in pre_sym]:
        rb = eb[lb.name[:-1] + "R"]
        if rb.name not in pre_sym or lb.name in PINNED or rb.name in PINNED:
            continue
        def _same(snap, eps=L["height"] * 0.01):
            """좌우가 '사실상 같은 자리'였는가. 원본 뼈대가 1~3cm 어긋나 있는 자산이 흔해서(알파카 앞발 x 2.7cm)
            정확히 같은 값만 인정하면 되돌리기가 아예 안 걸린다 — 키의 1% 안이면 같은 것으로 본다"""
            (hl, tl), (hr, tr) = snap[lb.name], snap[rb.name]
            return (hl * _MIR - hr).length <= eps and (tl * _MIR - tr).length <= eps
        # 되돌릴 대상은 둘이다: (1) 안쪽으로 당기기가 만든 어긋남, (2) 목표를 안 준 딸린 본(발가락 마디 등)이
        # 부모를 따라가다 좌우로 벌어진 것. 목표를 준 본의 어긋남은 사용자가 시킨 것이라 손대지 않는다
        free = lb.name not in T and rb.name not in T
        # 원본 뼈대가 좌우 대칭인 자산(--from-skeleton)이라면, 우리 결과에 남은 어긋남은 **전부 우리가 만든 것**이다.
        # 보정 도중에 이미 벌어진 뒤라 pre_sym 대조에 안 걸리는 경우가 있어서(Quaternius 데몬 새끼손가락 14cm) 그때도 되돌린다
        src_symmetric = bool(A.get("source_symmetric"))
        if not (_same(pre_sym) or (free and _same(meta_sym)) or src_symmetric):
            continue
        # 되돌리는 기준은 대칭 게이트가 실패로 보는 선(키의 1.67%)보다 조금 아래로 둔다 — 게이트가 잡을 어긋남은 다 고치되,
        # 그보다 작은 차이는 메시 자신의 비대칭이라 억지로 맞추지 않는다
        _tol = L["height"] * 0.0133
        if (lb.head * _MIR - rb.head).length > _tol or (lb.tail * _MIR - rb.tail).length > _tol:
            # 한쪽을 다른 쪽에 **베끼지 않고 가운데로 모은다**. 베끼면 어긋남 전체가 한쪽으로 몰려서,
            # 메시가 조금 비대칭인 자산에서는 되돌린 쪽 본이 메시 밖으로 나간다(Quaternius 블루데몬 팔뚝 3개)
            mh = (lb.head * _MIR + rb.head) / 2; mt = (lb.tail * _MIR + rb.tail) / 2
            lb.head = mh * _MIR; lb.tail = mt * _MIR; rb.head = mh; rb.tail = mt
            resymmetrized.append(rb.name)

    # 안전장치: 길이 0 에 가까운 본은 부모 방향으로 살짝 늘린다(Rigify 는 0 길이 본에서 실패한다)
    fixed = []
    for b in (() if "zerolen" in SKIP else eb):
        if (b.tail - b.head).length < 0.005:
            d = (b.parent.tail - b.parent.head) if b.parent and (b.parent.tail - b.parent.head).length > 0.01 else Vector((0, 0, 1))
            b.tail = b.head + d.normalized() * 0.02; fixed.append(b.name)
    # 안전장치 2: 팔꿈치·무릎이 일직선이면 Rigify 가 폴 방향을 못 정한다 → 팔꿈치는 뒤(+Y), 무릎은 앞(-Y)으로 2cm 굽힌다
    bent = []
    BEND = (("upper_arm.L", "forearm.L", 0.02), ("upper_arm.R", "forearm.R", 0.02), ("thigh.L", "shin.L", -0.02), ("thigh.R", "shin.R", -0.02))
    for up, low, dy in (() if "bend" in SKIP else BEND):
        if up in eb and low in eb:
            a, b = eb[up].tail - eb[up].head, eb[low].tail - eb[low].head
            if a.length > 0 and b.length > 0 and a.cross(b).length < 0.05 * a.length * b.length:   # 약 3도 미만
                joint = eb[low].head + Vector((0, dy, 0))
                eb[low].head = joint; eb[up].tail = joint; bent.append(low)
    # 보정 5: 원래 부모 tail 에 붙어 있던 본은 다시 붙인다(부모부터 순서대로)
    rejoined = []
    for b in (() if "rejoin" in SKIP else sorted(eb, key=lambda b: len(b.parent_recursive))):
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

    # 쉬는 자세 T 정규화(선택, rest_pose="t"): 팔이 내려간 메시(A 포즈)를 T 포즈로 굳힌다.
    # 리깅 자체는 A 포즈도 T 만큼 된다(같은 자산 팔만 내린 실험: mannequiny T 2.96cm vs A 2.5~2.8cm). 이걸 하는 이유는
    # 다음 단계(애니메이션·리타게팅)가 T 포즈 쉬는 자세를 전제로 하기 때문이다.
    # 방법: 메시를 메타리그에 임시 자동 가중치로 붙인다 → 위팔을 어깨 기준으로 돌려 어깨→손끝을 수평으로 → 메시에 굽는다
    # → 메타리그의 쉬는 자세를 그 자세로 굳힌다 → 임시 가중치를 지우고 평소대로 Rigify 생성·스키닝으로 간다
    rest_pose = {"requested": A.get("rest_pose", "keep"), "applied": False, "angles_deg": {}}
    if A.get("rest_pose") == "t" and preset == "humanoid" and all(n in meta.data.bones for n in ("upper_arm.L", "upper_arm.R")):
        import math
        angles = {}
        for side, sx in (("L", 1.0), ("R", -1.0)):
            ua = meta.data.bones[f"upper_arm.{side}"]; hand = meta.data.bones.get(f"hand.{side}")
            a_ = meta.matrix_world @ ua.head_local; b_ = meta.matrix_world @ (hand.tail_local if hand else ua.tail_local)
            d_ = b_ - a_
            angles[side] = round(math.degrees(math.atan2(-d_.z, d_.x * sx)), 2)   # 수평 아래로 몇 도 내려가 있나(+)
        rest_pose["angles_deg"] = angles
        if max(abs(v) for v in angles.values()) > 8.0:   # 이미 거의 수평이면 손대지 않는다
            bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); meta.select_set(True); bpy.context.view_layer.objects.active = meta
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
            # Bone Heat 는 떨어진 조각(손끝 장식·소품)에 가중치를 못 준다 → 그 정점들은 안 따라와 옛 자리에 떠 있었다(렌더로 확인).
            # 가중치 없는 정점은 가장 가까운 변형 본(선분 거리)에 1.0 으로 붙인다. 임시 가중치라 이 정도로 충분하다
            _vg = {g.index: g.name for g in obj.vertex_groups}
            _segs = [(b.name, meta.matrix_world @ b.head_local, meta.matrix_world @ b.tail_local) for b in meta.data.bones if b.use_deform and b.name in obj.vertex_groups]
            def _seg_dist(p, a, b):
                ab = b - a; t = 0.0 if ab.length_squared < 1e-12 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
                return (p - (a + ab * t)).length
            _seg_by = {n: (a_, b_) for n, a_, b_ in _segs}
            filled = reassigned = 0
            for v in obj.data.vertices:
                p = obj.matrix_world @ v.co
                near_name, near_d = min(((sg[0], _seg_dist(p, sg[1], sg[2])) for sg in _segs), key=lambda t: t[1])
                ws = [(g.weight, _vg.get(g.group, "")) for g in v.groups if _vg.get(g.group, "") in _seg_by]
                if not ws or sum(w for w, _ in ws) < 1e-4:
                    obj.vertex_groups[near_name].add([v.index], 1.0, "REPLACE"); filled += 1; continue
                dom = max(ws)[1]; dom_d = _seg_dist(p, *_seg_by[dom])
                # 떨어진 껍질(손끝 장식·소품)은 Bone Heat 가 멀리 있는 몸통 본에 붙인다 → 팔을 돌려도 안 따라와 옛 자리에 떠 있었다(렌더로 확인).
                # 지배 본이 가장 가까운 본보다 3배 넘게 멀면 가까운 본으로 통째로 바꾼다
                if dom_d > near_d * 3.0 + 0.01:
                    for g in list(v.groups):
                        obj.vertex_groups[_vg[g.group]].remove([v.index])
                    obj.vertex_groups[near_name].add([v.index], 1.0, "REPLACE"); reassigned += 1
            rest_pose["filled_unweighted"] = filled; rest_pose["reassigned_far"] = reassigned
            meta.data.pose_position = "POSE"
            bpy.ops.object.mode_set(mode="POSE")
            MW = meta.matrix_world
            for side, sx in (("L", 1.0), ("R", -1.0)):
                pb = meta.pose.bones[f"upper_arm.{side}"]; head_w = MW @ pb.head
                # Y 축 +회전은 +X 를 -Z(아래)로 보낸다 → 왼팔(+X)을 올리려면 -각도, 오른팔은 +각도
                R_w = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(-angles[side] * sx), 4, "Y") @ Matrix.Translation(-head_w)
                pb.matrix = MW.inverted() @ R_w @ MW @ pb.matrix
                bpy.context.view_layer.update()
            bpy.ops.object.mode_set(mode="OBJECT")
            # 메시에 굽기
            bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
            for md in [m for m in obj.modifiers if m.type == "ARMATURE"]:
                bpy.ops.object.modifier_apply(modifier=md.name)
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
            for g in list(obj.vertex_groups): obj.vertex_groups.remove(g)   # 임시 가중치 제거(원본 그룹도 어차피 스키닝 전에 지운다)
            # 메타리그의 쉬는 자세를 지금 자세로 굳힌다
            bpy.ops.object.select_all(action="DESELECT"); meta.select_set(True); bpy.context.view_layer.objects.active = meta
            bpy.ops.object.mode_set(mode="POSE"); bpy.ops.pose.armature_apply(selected=False); bpy.ops.object.mode_set(mode="OBJECT")
            # 안/밖 판정용 부피 메시는 옛 자세로 만든 것이라 다시 만든다
            bpy.data.objects.remove(vol)
            bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate(); vol = bpy.context.active_object; vol.name = "bw_volume"
            _vm = vol.modifiers.new("remesh", "REMESH"); _vm.mode = "VOXEL"; _vm.voxel_size = max(0.004, A["landmarks"]["height"] / 150)
            bpy.ops.object.modifier_apply(modifier="remesh"); vinv = vol.matrix_world.inverted()
            bpy.ops.object.select_all(action="DESELECT"); meta.select_set(True); bpy.context.view_layer.objects.active = meta
            rest_pose["applied"] = True

bpy.ops.pose.rigify_generate(); rig = bpy.context.active_object
# 스키닝
# 원본 뼈대의 정점 그룹을 먼저 지운다. 가져오기에서 아마추어 모디파이어는 굽지만 그룹 이름은 메시에 남는다.
# 새 아마추어에 없는 이름이라 변형에는 영향이 없지만(가중치 합은 이미 DEF- 만 세고 있다),
# 결과 파일에 죽은 그룹이 섞여 나가고 '이 정점을 주로 움직이는 본'을 물으면 엉뚱한 답이 나온다
# 일반 리그는 원본 뼈대를 **그대로** 베꼈다 → 변형 본 이름이 DEF-<원본 이름> 으로 1:1 이라 원본 가중치를
# 그대로 옮길 수 있다. 다시 계산할 이유가 없다: Bone Heat 는 눈·장식이 따로 떨어진 블롭 메시에서 정점의
# 39%를 비워 놓았는데(orc_blob 464/1203) 원본은 전부 칠해져 있다
source_weights = False; dropped_groups = []
if GENERIC:
    _have = {g.name for g in obj.vertex_groups}
    _want = {n for n, v in A["source_joints"].items() if v.get("deform") is not False}
    _def = {b.name for b in rig.data.bones if b.use_deform}
    if _want and len(_have & _want) >= len(_want) * 0.9:
        _cov = sum(1 for v in obj.data.vertices if any(g.weight > 1e-4 for g in v.groups))
        if _cov >= len(obj.data.vertices) * 0.99:
            for _g in list(obj.vertex_groups):
                if f"DEF-{_g.name}" in _def:
                    _g.name = f"DEF-{_g.name}"
            obj.parent = rig; obj.matrix_parent_inverse = rig.matrix_world.inverted()
            _am = obj.modifiers.new("Armature", "ARMATURE"); _am.object = rig
            source_weights = True
# **원작자 가중치를 자리로 옮기는 건 실패했다(2026-09-19).** 여기에 그 코드가 있었다.
# 착상: 이름은 달라도(`mixamorig:Spine` → `DEF-spine.003`) 자리는 원본에서 받아 왔으니 자리로 짝지으면
# 원작자가 칠한 가중치를 그대로 쓸 수 있다. 누수 지표는 실제로 좋아졌다(해골 전사 11/94 → 0).
# **그런데 움직여 보니 더 나빴다.** 같은 자산 CMU 걷기 리타겟: 자동 5.78배/모서리 34 → 원작자 11.25배/70.
# cesium_man 은 3.72 → 20.7배. 원인은 뼈대 규약 차이다 — 관절마다 **길이 0 짜리 표식**만 두는 파일이
# 흔한데(cesium_man), 그러면 '가장 가까운 자리' 짝짓기가 무너져 왼손 살이 몸통 본에 붙는다.
# 게이트(누수·구멍)는 이걸 못 잡는다. 움직여야 드러나기 때문이다. 자세한 기록은 docs/ROADMAP.md.
if source_weights:
    weight_method = "source"
    auto_unweighted = None; proxy_unweighted = None
    _vg = {g.index: g.name for g in obj.vertex_groups}
    sums = [sum(g.weight for g in v.groups if _vg.get(g.group, "").startswith("DEF-")) for v in obj.data.vertices]
    unweighted = sum(1 for s in sums if s < 1e-4)
else:

    dropped_groups = [g.name for g in obj.vertex_groups]
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)


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
    # weight_method="proxy" 로 강제할 수 있다(A/B 비교용). 기본은 Bone Heat 가 5% 넘게 비었을 때만 대리 메시로 간다
    if A.get("weight_method") == "proxy" or unweighted > len(obj.data.vertices) * 0.05:
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
# 구멍 메우기: Bone Heat·대리 메시 뒤에도 가중치가 전혀 없는 정점(떨어진 손끝 조각 등)이 남는다. 그 정점은 리그가 걸어가도
# 옛 자리에 남아 메시에서 긴 막대처럼 늘어난다(BVH 리타겟 렌더로 확인: mannequiny A 포즈 152개). 가장 가까운 변형 본(선분 거리)에 1.0 으로 붙인다
_fill_segs = [(b.name, rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones if b.use_deform and b.name in obj.vertex_groups]
def _fill_seg_dist(p, a, b):
    ab = b - a; t = 0.0 if ab.length_squared < 1e-12 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length
vg = {g.index: g.name for g in obj.vertex_groups}; filled_unweighted = 0; rigid_bound = 0
_bare = [v.index for v in obj.data.vertices
         if sum(g.weight for g in v.groups if vg.get(g.group, "").startswith("DEF-")) < 1e-4]
# 떨어진 조각(로봇 팔·발 같은 강체 부품)이 통째로 비면, 그건 '구멍'이 아니라 **그 부품을 통째로 한 본에 붙이면 되는 것**이다.
# 조각 전체를 중심에서 가장 가까운 본 하나에 붙인다(원작자가 본에 통째로 부모로 묶어 둔 것과 같은 결과).
# 일부만 빈 조각은 진짜 구멍이라 예전처럼 정점별로 메우고 구멍으로 센다
if _bare and _fill_segs:
    parent = list(range(len(obj.data.vertices)))
    def _root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for e in obj.data.edges:
        a, b = _root(e.vertices[0]), _root(e.vertices[1])
        if a != b: parent[a] = b
    island = {}
    for i in range(len(obj.data.vertices)):
        island.setdefault(_root(i), []).append(i)
    bare_set = set(_bare)
    for members in island.values():
        if len(members) < 4:
            continue
        # 들고 있는 소품(칼·삼지창)은 **강체**다 — 일부만 비어도 조각 전체를 한 본에 붙이는 게 맞다.
        # 정점별로 메우면 같은 무기가 여러 본에 흩어져 붙고, 메운 정점이 '구멍'으로 세어져 게이트가 실패한다(오크 121/3836)
        held = len(members) >= 4 and sum(1 for i in members if i in ATTACH_VERTS) >= len(members) * 0.9
        if not (bare_set.issuperset(members) or (held and any(i in bare_set for i in members))):
            continue   # 일부만 빈 보통 조각은 아래에서 정점별로
        c = sum((obj.matrix_world @ obj.data.vertices[i].co for i in members), Vector()) / len(members)
        near = min(_fill_segs, key=lambda sg: _fill_seg_dist(c, sg[1], sg[2]))[0]
        obj.vertex_groups[near].add(members, 1.0, "REPLACE")
        rigid_bound += len(members); bare_set.difference_update(members)
    _bare = sorted(bare_set)
# 남은 빈 정점은 **이웃한 살에서 가져온다**. 가장 가까운 본에 1.0 으로 붙이면 그 정점 하나만 다른 본을
# 따라 움직여 껍질에 금이 간다(오크의 무기 12정점). 메시 모서리를 타고 **같은 조각에서 가장 가까운
# 가중치 있는 정점**을 찾아 그 가중치를 통째로 복사하면 주변 살과 함께 움직인다 — 추측이 아니라 보간이다.
# 조각 전체가 비어 이웃이 아예 없을 때만 예전처럼 가장 가까운 본으로 메우고, 그건 구멍으로 센다.
filled_from_neighbor = 0
if _bare:
    _adj = {}
    for e in obj.data.edges:
        a, b = e.vertices[0], e.vertices[1]
        _adj.setdefault(a, []).append(b); _adj.setdefault(b, []).append(a)
    _bare_set = set(_bare)
    _seed = [i for i in _adj if i not in _bare_set]          # 가중치가 있는 정점에서 바깥으로 퍼진다
    _src = {i: i for i in _seed}
    _q = list(_seed); _h = 0
    while _h < len(_q):
        cur = _q[_h]; _h += 1
        for nb in _adj.get(cur, ()):
            if nb in _src:
                continue
            _src[nb] = _src[cur]; _q.append(nb)
    _byv = {}
    for i in _bare:
        j = _src.get(i)
        if j is None:
            continue
        for g in obj.data.vertices[j].groups:
            n = vg.get(g.group, "")
            if n.startswith("DEF-") and g.weight > 1e-4:
                _byv.setdefault(n, []).append((i, g.weight))
    for n, items in _byv.items():
        for i, w in items:
            obj.vertex_groups[n].add([i], w, "REPLACE")
    filled_from_neighbor = len({i for items in _byv.values() for i, _w in items})
    _bare = [i for i in _bare if i not in _src]
for i in _bare:
    if _fill_segs:
        p = obj.matrix_world @ obj.data.vertices[i].co
        near = min(_fill_segs, key=lambda sg: _fill_seg_dist(p, sg[1], sg[2]))[0]
        obj.vertex_groups[near].add([i], 1.0, "REPLACE"); filled_unweighted += 1
# 먼 본이 남긴 가중치 떨어내기: 자동 가중치는 어깨가 몸에 붙은 체형에서 팔 본에 **가슴 한가운데** 정점까지 준다
# (치비 44/115, 로봇 15/217 — 움직이면 가슴이 팔을 따라 밀린다). 그 정점에서 가장 가까운 변형 본보다
# FAR_RATIO 배 넘게 먼 본은 그 정점을 움직일 이유가 없다. 관절 근처의 자연스러운 섞임(팔꿈치·어깨)은
# 두 본 거리가 비슷해서 그대로 남는다
FAR_RATIO = 2.5
_seg_by_name = {n: (a, b) for n, a, b in _fill_segs}
vg = {g.index: g.name for g in obj.vertex_groups}
far_trimmed_verts = far_trimmed_weights = 0
for v in obj.data.vertices:
    gs = [(g, vg.get(g.group, "")) for g in v.groups if vg.get(g.group, "").startswith("DEF-") and g.weight > 0]
    if len(gs) < 2:
        continue
    pw = obj.matrix_world @ v.co
    d = {n: _fill_seg_dist(pw, *_seg_by_name[n]) for _, n in gs if n in _seg_by_name}
    if len(d) < 2:
        continue
    lim = min(d.values()) * FAR_RATIO
    drop = [n for n, dist in d.items() if dist > lim]
    if not drop:
        continue
    keep = sum(g.weight for g, n in gs if n not in drop)
    if keep <= 1e-6:
        continue   # 전부 멀면 손대지 않는다(떨어진 조각 등)
    for n in drop:
        obj.vertex_groups[n].remove([v.index]); far_trimmed_weights += 1
    far_trimmed_verts += 1
# 남의 살덩이에서 온 가중치 떼어내기(`rig.cross_trim`) — **메시 속을 따라 잰 거리**로 판정한다.
# 자동 가중치는 직선 거리로 판단하므로 속 빈 해골에서 팔 본이 텅 빈 가슴을 가로질러 갈비뼈를 가져간다.
# 처음엔 광선을 한 번 쏴 "껍질을 뚫고 나가면 남"으로 봤는데, 조각조각 떨어진 메시(mannequiny)에서는
# 이웃 조각으로 가는 길이 전부 껍질을 뚫어 관절 섞임이 통째로 날아갔다(늘어남 4.71 → 7.88배).
# 복셀로 채우면 조각 사이 실틈은 복셀 한 칸에 묻히고 해골의 빈 가슴은 그대로 남는다 — 해상도가
# "무시할 틈"과 "진짜 빈 속"을 갈라 준다. 자세한 근거는 _voxgeo.py 머리말.
cross_trimmed_verts = cross_trimmed_weights = 0
cross_detour = None
if A.get("cross_trim", True):
    from _voxgeo import VoxGeo
    _vg_geo = VoxGeo(obj, grid=int(A.get("voxgeo_grid", 40)))
    if _vg_geo.ok:
        _winv = obj.matrix_world.inverted()
        _sd = {}
        for n, a, b in _fill_segs:
            _sd[n] = (_winv @ a, _winv @ b)
            _vg_geo.field(n, _sd[n][0], _sd[n][1])
        DETOUR = 1.6          # 살 속으로 1.6 배 넘게 돌아가야 닿는 본은 그 정점을 움직일 이유가 없다
        for v in obj.data.vertices:
            gs = [(g, vg.get(g.group, "")) for g in v.groups if vg.get(g.group, "").startswith("DEF-") and g.weight > 0]
            if len(gs) < 2:
                continue
            dom = max(gs, key=lambda q: q[0].weight)[1]
            drop = []
            for g, n in gs:
                if n == dom or n not in _sd:
                    continue
                r = _vg_geo.detour(v.co, n)
                if r is not None and r > DETOUR:
                    drop.append(n)
            if not drop or sum(g.weight for g, n in gs if n not in drop) <= 1e-6:
                continue
            for n in drop:
                obj.vertex_groups[n].remove([v.index]); cross_trimmed_weights += 1
            cross_trimmed_verts += 1
        cross_detour = DETOUR
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.object.vertex_group_normalize_all(lock_active=False)

# 정점당 영향 본 수 제한: glTF·엔진 표준이 4개다. 넘으면 내보낼 때 잘려 나가면서 가중치 합이 1 이 안 되고, 블렌더 안에서 본
# 모습과 엔진에서 본 모습이 달라진다. 가장 큰 4개만 남기고 다시 1 로 맞춘다(아주 작은 가중치 0.005 미만도 버린다)
MAX_INFLUENCES, MIN_W = 4, 0.005
vg = {g.index: g.name for g in obj.vertex_groups}
trimmed_verts = trimmed_weights = 0; max_inf_before = 0
for v in obj.data.vertices:
    gs = [(g.weight, g.group) for g in v.groups if vg.get(g.group, "").startswith("DEF-")]
    max_inf_before = max(max_inf_before, len(gs))
    keep = sorted(gs, reverse=True)[:MAX_INFLUENCES]
    keep = [(w, gi) for w, gi in keep if w >= MIN_W] or keep[:1]
    drop = [gi for _, gi in gs if gi not in {gi2 for _, gi2 in keep}]
    if drop:
        trimmed_verts += 1; trimmed_weights += len(drop)
        for gi in drop: obj.vertex_groups[vg[gi]].remove([v.index])
    tot = sum(w for w, _ in keep)
    if tot > 1e-8 and abs(tot - 1.0) > 1e-4:
        for w, gi in keep: obj.vertex_groups[vg[gi]].add([v.index], w / tot, "REPLACE")

vg = {g.index: g.name for g in obj.vertex_groups}; sums = []; unweighted = 0
max_influences = 0
for v in obj.data.vertices:
    ws = [g.weight for g in v.groups if vg.get(g.group, "").startswith("DEF-")]
    w = sum(ws); sums.append(w); max_influences = max(max_influences, len(ws))
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
# '몸통 한가운데' 띠의 폭. 키 비례(4%)만 쓰면 치비처럼 어깨가 몸 가까이 붙은 캐릭터에서 띠가 어깨까지 덮어
# 팔 본이 정상적으로 잡은 정점을 '샜다'고 센다(quat_pp_43j 108/271). 어깨 위치로도 제한한다
_ax = [abs((rig.matrix_world @ rig.data.bones[n].head_local).x) for n in ("DEF-upper_arm.L", "DEF-upper_arm.R") if n in rig.data.bones]
_band = min(0.04 * _H, 0.35 * (sum(_ax) / len(_ax))) if _ax else 0.04 * _H
vgn = {g.index: g.name for g in obj.vertex_groups}
leak_arm, torso_verts, far_dom = 0, 0, 0
_cands = []        # (중심선에서 떨어진 거리, 팔 몫) — 가슴 높이 정점을 전부 모아 둔다
for v in obj.data.vertices:
    pw = obj.matrix_world @ v.co
    w = {vgn.get(g.group, ""): g.weight for g in v.groups if vgn.get(g.group, "").startswith("DEF-")}
    if not w: continue
    t = sum(w.values()) or 1.0
    if _z0 + 0.45 * _H < pw.z < _z0 + 0.70 * _H:
        _cands.append((abs(pw.x), sum(val for k, val in w.items() if k.startswith(_ARM)) / t))
    dom = max(w, key=w.get)
    if w[dom] / t > 0.5 and dom in _seg and _dist(dom, pw) > 0.15 * _H: far_dom += 1
# 표본 고르기: 기본은 좁은 띠(_band) 안쪽이다. 저폴리 캐릭터는 그 띠에 정점이 스무 개도 안 들어와
# 게이트가 "표본 부족"으로 검사를 **건너뛰어** 버린다 — 결함이 있어도 통과한다(godot_player 17/31 이
# 팔 본이 밖으로 나가자 21개로 줄며 검사 자체가 꺼졌다). 그래서 모자라면 중심선에 가까운 순서로
# 30개까지 채우되, 어깨까지 번지지 않게 넉넉한 상한(_band 의 2.5배) 안에서만 채운다
_cands.sort()
_sel = [c for c in _cands if c[0] < _band]
if len(_sel) < 30:
    # 넓히되 **어깨까지 가지 않게** 상한을 둔다. 팔 본 x 의 절반을 넘으면 팔이 정상적으로 잡은
    # 정점을 '샜다'고 세기 시작한다(이 파일이 이미 겪은 실수다 — quat_pp_43j 108/271)
    _wide = min(0.06 * _H, 0.5 * (sum(_ax) / len(_ax))) if _ax else 0.06 * _H
    _sel = [c for c in _cands if c[0] < max(_band, _wide)][:30]
torso_verts = len(_sel)
leak_arm = sum(1 for _d, share in _sel if share > 0.15)
mn = Vector(A["stats"]["min"]); mx = Vector(A["stats"]["max"]); pad = 0.12
outside = [b.name for b in rig.data.bones if b.use_deform and not all(mn[i] - pad <= (rig.matrix_world @ b.head_local)[i] <= mx[i] + pad for i in range(3))]
def _outside(p):
    # 여유값은 판정용 부피 메시의 해상도(복셀 한 칸)만큼 준다 — 말처럼 다리가 얇으면 복셀이 다리를 제대로 못 담아
    # 제자리에 있는 본도 '밖'으로 읽힌다(말 앞정강이 11개). 복셀 한 칸보다 덜 나간 것은 측정 한계 안이라 통과시킨다
    return not is_inside(p, margin=max(0.003, volume_voxel))
# 손가락 본은 이 검사에서 뺀다: 판정용 부피 메시(복셀 1.2cm)가 손가락을 한 덩어리로 뭉개서 전부 "밖"으로 읽힌다.
# 손가락은 보정 3(손 실루엣 안으로 축소)이 원본 메시 기준으로 이미 처리한다
# 손가락·발가락 마디: 판정용 부피 메시(복셀)가 뭉개서 전부 '밖'으로 읽힌다. 사족 늑대 메타리그는 뒷발가락을 r_(rear) 로 부른다
FINGER = ("DEF-f_", "DEF-thumb", "DEF-palm", "DEF-r_")
# 가중치가 하나도 없는 본은 살을 움직일 수 없다 → 밖에 있어도 결함이 아니다. 원본 뼈대에서 받은 리그는
# 메타리그가 척추를 잘게 쪼개 원본에 없던 마디를 만들기도 하는데(KayKit 미니언 DEF-spine.003/004),
# 그 마디에 정점이 하나도 안 붙었다면 리그 품질과 무관하다
_wgn = {g.index: g.name for g in obj.vertex_groups}
_wgt_used = set()
for _v in obj.data.vertices:
    for _g in _v.groups:
        if _g.weight > 1e-4:
            _wgt_used.add(_wgn.get(_g.group, ""))
_check = [b for b in rig.data.bones if b.use_deform and not b.name.startswith(FINGER) and b.name in _wgt_used]
finger_bones_skipped = sum(1 for b in rig.data.bones if b.use_deform and b.name.startswith(FINGER))
# 본을 5등분해 중간점도 검사한다: 끝점만 보면 비스듬한 본이 중간에 메시를 뚫고 나가는 걸 놓친다(실측으로 확인)
def _bone_points(b):
    h, t = rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local
    return [h + (t - h) * (i / 4.0) for i in range(5)]
# 조각으로 나뉜 모델(로봇 등)은 본이 '몸 밖'이 아니라 '조각 사이 빈틈'을 지난다. 관절 양끝이 메시 안이면
# 스키닝에 문제가 없으므로 실패가 아니라 경고로 따로 센다 — 실제로 못 붙는 본은 끝이 허공에 뜬 본이다.
# 판정 단위는 DEF 본 하나가 아니라 '메타리그 본 하나'다: Rigify 는 팔다리를 B-본 두 마디로 쪼개므로
# (DEF-forearm.L + DEF-forearm.L.001) 쪼갠 이음매가 마침 빈틈에 떨어지면 멀쩡한 관절도 밖으로 읽힌다.
# 쪼갠 마디는 이름이 '...[.LR].숫자' 라서 골라낼 수 있다(척추의 DEF-spine.001 은 좌우 표시가 없어 안 걸린다)
_SPLIT = re.compile(r"^(.*\.[LR])\.\d+$")
_group = {}
for b in _check:
    m = _SPLIT.match(b.name)
    _group.setdefault(m.group(1) if m and m.group(1) in rig.data.bones else b.name, []).append(b)
deform_outside_mesh, deform_gap_mesh = [], []
for base, members in _group.items():
    members.sort(key=lambda b: b.name)
    pts = [pt for b in members for pt in _bone_points(b)]
    if not any(_outside(pt) for pt in pts):
        continue
    names = [b.name for b in members]
    (deform_gap_mesh if not (_outside(pts[0]) or _outside(pts[-1])) else deform_outside_mesh).extend(names)
deform_outside_mesh.sort(); deform_gap_mesh.sort()
pairs = [(b.name, b.name[:-1] + "R") for b in rig.data.bones if b.use_deform and b.name.endswith(".L") and (b.name[:-1] + "R") in rig.data.bones]
asym = [round(((rig.data.bones[l].head_local * Vector((-1, 1, 1))) - rig.data.bones[r].head_local).length, 4) for l, r in pairs]
worst_sym = pairs[asym.index(max(asym))][0] if asym else None   # 어느 본이 제일 어긋났는지 남긴다(진단용)
stats = {"generic_source_bones": (sum(1 for v in A["source_joints"].values() if v.get("deform") is not False) if GENERIC else None), "metarig_bones": len(meta.data.bones), "rig_bones": len(rig.data.bones), "deform_bones": sum(1 for b in rig.data.bones if b.use_deform),
         "weight_method": weight_method, "auto_unweighted": auto_unweighted, "proxy_unweighted": proxy_unweighted, "height": A["landmarks"]["height"], "moved_bones": moved, "removed_face_bones": removed_face, "clamped_targets": sorted(set(clamped)), "fixed_zero_length": fixed, "bent_joints": bent, "axis_snapped": axis_snapped, "propagated_bones": len(propagated), "finger_scale": finger_scale, "snapped_inside": len(snapped_inside), "rejoined": rejoined, "pinned": sorted(PINNED), "pin_applied": pin_applied, "volume_voxel": volume_voxel, "snapped_inside_bones": snapped_inside[:12], "resymmetrized": resymmetrized[:12], "unweighted_verts": unweighted, "filled_unweighted": filled_unweighted, "filled_from_neighbor": filled_from_neighbor, "rigid_islands_bound": rigid_bound,
         "max_influences": max_influences, "max_influences_before": max_inf_before, "trimmed_verts": trimmed_verts, "trimmed_weights": trimmed_weights, "far_trimmed_verts": far_trimmed_verts, "far_trimmed_weights": far_trimmed_weights, "cross_trimmed_verts": cross_trimmed_verts, "cross_trimmed_weights": cross_trimmed_weights, "cross_detour": cross_detour, "weight_sum_min": round(min(sums), 4), "weight_sum_max": round(max(sums), 4),
         "weight_leak_arm_torso": leak_arm, "weight_leak_torso_verts": torso_verts, "weight_far_dominant": far_dom, "bones_outside_bbox": outside[:20], "deform_outside_mesh": len(deform_outside_mesh), "dropped_source_groups": len(dropped_groups), "rest_pose": rest_pose, "finger_bones_skipped": finger_bones_skipped, "deform_outside_mesh_bones": deform_outside_mesh[:12], "deform_gap_mesh": len(deform_gap_mesh), "deform_gap_mesh_bones": deform_gap_mesh[:12], "symmetry_pairs": len(pairs), "symmetry_max_error": max(asym) if asym else 0, "symmetry_worst": worst_sym}
bpy.data.objects.remove(vol)   # 판정용 부피 메시는 저장하지 않는다
bpy.ops.wm.save_as_mainfile(filepath=A["out_blend"])
done({"stats": stats, "rig": rig.name, "blend": A["out_blend"]}, A["result"])
