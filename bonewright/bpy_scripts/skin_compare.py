"""스키닝 정답 대조(토큰 0): 우리가 만든 가중치를 원작자의 가중치와 비교한다.

관절 위치만 맞아도 스키닝이 엉망이면 쓸 수 없다. 정점 순서는 우리 파이프라인이 메시를 합치고 모디파이어를
구워서 원본과 다르므로, **위치가 가장 가까운 원본 정점**(KD 트리)과 짝지어 비교한다.

두 가지 지표를 낸다.
  1) 이름 지표(pairs): '이 정점을 주로 움직이는 본'의 이름이 원본과 같은가. 규약 정규화가 필요하고,
     원본이 다리를 5토막 내는데 우리가 3토막이면(cesium_man) 맞아도 틀린 것으로 센다 — 한계가 있다.
  2) 위치 지표(influence): 정점에 영향 주는 본들의 '정점에서 가장 가까운 점'을 가중 평균한 자리(영향 중심)를
     원본과 우리 쪽에서 각각 구해 cm 로 잰다. 이름·토막 수와 무관하다. 우리 지배 본이 이름은 달라도 같은 자리면
     오차가 작게 나온다 — 실제 변형이 얼마나 비슷한지에 더 가깝다.
"""
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree
from _common import args, done, fresh, import_mesh

A = args(); fresh()


def seg_closest(p, a, b):
    ab = b - a
    if ab.length_squared < 1e-12:
        return a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return a + ab * t


def influence_point(p, groups, weights, segs):
    """영향 중심: 정점 p 에 붙은 본들의 최근접점을 가중 평균"""
    acc = Vector(); tot = 0.0
    for gname, w in zip(groups, weights):
        sg = segs.get(gname)
        if sg is None or w <= 0:
            continue
        acc += seg_closest(p, sg[0], sg[1]) * w; tot += w
    return (acc / tot) if tot > 1e-8 else None


def bone_segments(arm_obj, names_filter=None):
    """본이 실제로 덮는 구간. 꼬리가 아니라 **자식의 머리**까지로 본다 — 리그마다 뼈를 관절에 붙은 짧은 토막으로 그리는 관습이 있어
    (Quaternius 계열) 꼬리 기준으로 재면 발목 정점의 '영향 중심'이 무릎으로 잡혀 44cm 씩 어긋난다. 자식이 하나일 때만 늘린다
    (척추처럼 자식이 여럿이면 어느 쪽으로 늘릴지 정할 수 없다)."""
    MW = arm_obj.matrix_world
    out = {}
    for b in arm_obj.data.bones:
        if names_filter is not None and not names_filter(b): continue
        kids = [c for c in b.children if names_filter is None or names_filter(c)]
        end = kids[0].head_local if len(kids) == 1 else b.tail_local
        if (end - b.head_local).length < b.length * 0.5:   # 자식이 뒤로 붙는 경우(꼬리·가슴)는 원래 꼬리를 쓴다
            end = b.tail_local
        out[b.name] = (MW @ b.head_local, MW @ end)
    return out


# 1) 원본: 뼈대를 살려서 가져오고 정점마다 (주도 본, 영향 중심) 을 뽑는다
orig = import_mesh(A["mesh"], facing=A.get("facing", "auto"), keep_armature=True,
                   quad=A.get("preset") == "quadruped")
oarm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
osegs = bone_segments(oarm) if oarm else {}
groups = {g.index: g.name for g in orig.vertex_groups}
zs = [(orig.matrix_world @ v.co).z for v in orig.data.vertices]
height = (max(zs) - min(zs)) if zs else 1.0
src = []
for v in orig.data.vertices:
    p = orig.matrix_world @ v.co
    gs = [(groups.get(g.group), g.weight) for g in v.groups if groups.get(g.group) in osegs]
    best = max(gs, key=lambda t: t[1], default=(None, 0.0))
    ip = influence_point(p, [g for g, _ in gs], [w for _, w in gs], osegs)
    src.append((p, best[0], ip))
tree = KDTree(len(src))
for i, (co, _, _) in enumerate(src):
    tree.insert(co, i)
tree.balance()

# 2) 우리 결과: 리깅된 blend 를 열고 같은 방식으로 뽑는다(변형 본 DEF- 만)
bpy.ops.wm.open_mainfile(filepath=A["blend"])
ours = next((o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups), None)
if ours is None:
    done({"error": "리깅된 메시를 찾지 못했다"}, A["result"])
# blend 에는 메타리그와 생성된 리그가 같이 있다 → DEF- 본을 가진 쪽(메시의 부모)을 고른다. 첫 아마추어를 집으면 메타리그라 영향 중심이 전부 빠진다
rig = ours.parent if (ours.parent and ours.parent.type == "ARMATURE") else None
if rig is None or not any(b.name.startswith("DEF-") for b in rig.data.bones):
    rig = next((o for o in bpy.data.objects if o.type == "ARMATURE" and any(b.name.startswith("DEF-") for b in o.data.bones)), None)
rsegs = bone_segments(rig, lambda b: b.use_deform) if rig else {}
og = {g.index: g.name for g in ours.vertex_groups if g.name.startswith("DEF-")}
pairs, dists, dist_regions, dist_offsets, dist_ours, unweighted, no_ip = [], [], [], [], [], 0, 0
for v in ours.data.vertices:
    cand = [g for g in v.groups if g.group in og]
    if not cand:
        unweighted += 1; continue
    p = ours.matrix_world @ v.co
    _, i, _ = tree.find(p)
    best = max(cand, key=lambda g: g.weight)
    if src[i][1]:
        pairs.append([og[best.group], src[i][1]])
    ip_ours = influence_point(p, [og[g.group] for g in cand], [g.weight for g in cand], rsegs)
    ip_orig = src[i][2]
    if ip_ours is None or ip_orig is None:
        no_ip += 1; continue
    dists.append((ip_ours - ip_orig).length); dist_regions.append(src[i][1])
    dist_offsets.append(ip_ours - ip_orig); dist_ours.append(og[best.group])

# 부위별로 갈라 본다: 어디를 고쳐야 하는지 알려면 평균 하나로는 부족하다. 원본이 그 정점을 주로 맡긴 본 이름으로 나눈다
REGION = (("hand", ("hand", "finger", "thumb", "index", "middle", "ring", "pinky", "palm", "wrist")),
          ("foot", ("foot", "toe", "ankle", "heel", "ball")),
          ("arm", ("arm", "elbow", "shoulder", "clavicle")),
          ("leg", ("leg", "thigh", "shin", "calf", "knee", "hip")),
          ("head", ("head", "neck", "jaw", "eye", "face", "skull")),
          ("torso", ("spine", "chest", "torso", "pelvis", "back", "breast", "body", "root")))
def region_of(name):
    n = (name or "").lower()
    for tag, words in REGION:
        if any(w in n for w in words): return tag
    return "other"
by_region, off_region, name_region = {}, {}, {}
for d_, gname, off, oname in zip(dists, dist_regions, dist_offsets, dist_ours):
    r_ = region_of(gname)
    by_region.setdefault(r_, []).append(d_)
    off_region.setdefault(r_, []).append(off)   # 우리 영향 중심 − 원본 영향 중심(어느 쪽으로 쏠렸나)
    name_region.setdefault(r_, []).append(oname)
def _avg(v):
    return [round(sum(x[i] for x in v) / len(v) * 100, 1) for i in range(3)]
regions = {k: {"verts": len(v), "mean_cm": round(sum(v) / len(v) * 100, 2),
               "mean_pct_height": round(sum(v) / len(v) / height * 100, 2),
               "mean_offset_cm": _avg(off_region[k]),
               "our_bones": sorted({n for n in name_region[k] if n}, key=lambda n: -name_region[k].count(n))[:4]}
           for k, v in sorted(by_region.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))}

dists.sort()
n = len(dists)
influence = None
if n:
    influence = {"verts": n, "mean_cm": round(sum(dists) / n * 100, 2), "median_cm": round(dists[n // 2] * 100, 2),
                 "p90_cm": round(dists[int(n * 0.9)] * 100, 2), "mean_pct_height": round(sum(dists) / n / height * 100, 2),
                 "frac_over_10pct": round(sum(1 for d in dists if d > height * 0.10) / n, 3), "height": round(height, 3)}
done({"pairs": pairs, "unweighted": unweighted, "verts": len(ours.data.vertices),
      "influence": influence, "regions": regions, "no_influence": no_ip}, A["result"])
