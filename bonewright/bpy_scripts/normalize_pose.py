"""포즈 정규화(토큰 0): 팔을 내린 캐릭터의 메시를 T 자세로 구워 새 파일로 낸다. 분석 **전에** 돌린다.

왜 분석 전인가 — 팔을 내린 메시는 팔과 몸통이 붙어 보여서 관절 찾기가 흔들린다(팔 75° 에서 손 22.6cm, 90° 에서 46.2cm 오차,
90° 는 발목을 못 찾아 게이트에서 거절). 먼저 팔을 수평으로 펴 놓고 재면 T 포즈와 같은 조건이 된다.

절차는 fit_generate 의 rest-pose T 와 같지만, 리그 없이 **거친 메타리그**로만 한다:
메타리그를 키에 맞춰 얹고 → 위팔 본을 분석이 준 팔 중심선 끝(손끝)으로 돌려놓고 → 임시 자동 가중치 →
위팔을 수평으로 되돌리고 → 메시를 굽는다. 목표는 '정확한 리깅'이 아니라 '분석이 잘 되는 자세'다.
"""
import math
import bpy
from mathutils import Matrix, Vector
from _common import args, done, fresh, import_mesh

A = args(); fresh()
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"))
L = A["landmarks"]
bpy.ops.preferences.addon_enable(module="rigify")
bpy.ops.object.armature_human_metarig_add(); meta = bpy.context.active_object
mh = max(b.tail_local.z for b in meta.data.bones) - min(b.head_local.z for b in meta.data.bones)
meta.scale = (L["height"] / mh,) * 3
bpy.context.view_layer.objects.active = meta; bpy.ops.object.transform_apply(scale=True)
meta.location.z = L["ground_z"] - min(b.head_local.z for b in meta.data.bones)
bpy.ops.object.transform_apply(location=True)

# 얼굴·손가락 본은 임시 가중치에 방해만 된다
bpy.ops.object.mode_set(mode="EDIT")
eb = meta.data.edit_bones
DROP = ("face", "eye", "lip", "brow", "nose", "cheek", "jaw", "ear", "chin", "tongue", "teeth", "temple", "forehead", "lid",
        "f_", "thumb", "palm")
for b in list(eb):
    if any(w in b.name for w in DROP):
        eb.remove(b)
# 팔 사슬을 분석이 준 중심선 위에 올린다(어깨 → 팔꿈치 45% → 손목 82% → 끝)
angles = {}
for side in ("L", "R"):
    ax = L.get(f"arm_axis_{side}") or []
    if len(ax) < 4 or f"upper_arm.{side}" not in eb:
        continue
    pts = [Vector(p[:3]) for p in ax]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg) or 1.0
    def at(f):
        d = f * total; acc = 0.0
        for i, ln in enumerate(seg):
            if acc + ln >= d:
                return pts[i].lerp(pts[i + 1], (d - acc) / ln if ln else 0.0)
            acc += ln
        return pts[-1]
    sh, el, wr, tip = at(0.0), at(0.45), at(0.82), at(1.0)
    for n, h, t in ((f"upper_arm.{side}", sh, el), (f"forearm.{side}", el, wr), (f"hand.{side}", wr, tip)):
        if n in eb:
            eb[n].head, eb[n].tail = h, t
    d = tip - sh
    sx = 1.0 if side == "L" else -1.0
    angles[side] = math.degrees(math.atan2(-d.z, d.x * sx))   # 수평이면 0, 내렸으면 +
bpy.ops.object.mode_set(mode="OBJECT")

applied = False
if angles and max(abs(v) for v in angles.values()) > float(A.get("threshold_deg", 20.0)):
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); meta.select_set(True); bpy.context.view_layer.objects.active = meta
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    # 가중치 없는 정점은 가장 가까운 변형 본에 붙인다(임시 가중치라 이 정도면 된다)
    _vg = {g.index: g.name for g in obj.vertex_groups}
    _segs = [(b.name, meta.matrix_world @ b.head_local, meta.matrix_world @ b.tail_local) for b in meta.data.bones
             if b.use_deform and b.name in obj.vertex_groups]
    def _seg_dist(p, a_, b_):
        ab = b_ - a_; t = 0.0 if ab.length_squared < 1e-12 else max(0.0, min(1.0, (p - a_).dot(ab) / ab.length_squared))
        return (p - (a_ + ab * t)).length
    filled = 0
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        if sum(g.weight for g in v.groups if _vg.get(g.group, "") in {n for n, _, _ in _segs}) < 1e-4 and _segs:
            near = min(_segs, key=lambda sg: _seg_dist(p, sg[1], sg[2]))[0]
            obj.vertex_groups[near].add([v.index], 1.0, "REPLACE"); filled += 1
    meta.data.pose_position = "POSE"
    bpy.ops.object.mode_set(mode="POSE")
    MW = meta.matrix_world
    for side, sx in (("L", 1.0), ("R", -1.0)):
        n = f"upper_arm.{side}"
        if n not in meta.pose.bones or side not in angles:
            continue
        pb = meta.pose.bones[n]; head_w = MW @ pb.head
        R = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(-angles[side] * sx), 4, "Y") @ Matrix.Translation(-head_w)
        pb.matrix = MW.inverted() @ R @ MW @ pb.matrix
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    for md in obj.modifiers:
        if md.type == "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    applied = True

bpy.data.objects.remove(meta)
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=A["out"], use_selection=True, export_format="GLB", export_apply=True,
                          export_skins=False, export_animations=False, export_yup=True)
done({"out": A["out"], "applied": applied, "angles_deg": {k: round(v, 2) for k, v in angles.items()},
      "filled_unweighted": filled if applied else 0, "verts": len(obj.data.vertices)}, A["result"])
