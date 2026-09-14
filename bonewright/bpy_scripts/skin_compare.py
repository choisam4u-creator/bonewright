"""스키닝 정답 대조(토큰 0): 우리가 만든 가중치를 원작자의 가중치와 비교한다.

관절 위치만 맞아도 스키닝이 엉망이면 쓸 수 없다. 그래서 '어느 본이 이 정점을 주로 움직이는가'를
원본과 맞대본다. 정점 순서는 우리 파이프라인이 메시를 합치고 모디파이어를 구워서 원본과 다르므로,
**위치가 가장 가까운 원본 정점**(KD 트리)과 짝지어 비교한다.

내놓는 값
  · agree      : 주도 본이 같은 정점의 비율(이름 규약을 정규화해서 비교)
  · agree_side : 좌우만 맞은 비율(부위가 달라도 좌우는 맞는 경우 — 팔↔몸통 새는지 보는 용도)
  · mapped     : 원본 본 이름을 우리 이름으로 옮길 수 있었던 정점 비율(낮으면 비교 자체가 무의미하다)
"""
import bpy
from mathutils.kdtree import KDTree
from _common import args, done, fresh, import_mesh

A = args(); fresh()

# 1) 원본: 뼈대를 살려서 가져오고 정점마다 주도 본을 뽑는다
orig = import_mesh(A["mesh"], facing=A.get("facing", "auto"), keep_armature=True,
                   quad=A.get("preset") == "quadruped")
groups = {g.index: g.name for g in orig.vertex_groups}
src = []
for v in orig.data.vertices:
    best = max(v.groups, key=lambda g: g.weight, default=None)
    src.append((orig.matrix_world @ v.co, groups.get(best.group) if best else None,
                best.weight if best else 0.0))
tree = KDTree(len(src))
for i, (co, _, _) in enumerate(src):
    tree.insert(co, i)
tree.balance()

# 2) 우리 결과: 리깅된 blend 를 열고 같은 방식으로 뽑는다
bpy.ops.wm.open_mainfile(filepath=A["blend"])
ours = next((o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups), None)
if ours is None:
    done({"error": "리깅된 메시를 찾지 못했다"}, A["result"])
# 우리 쪽은 변형 본(DEF-) 만 본다. 원본 그룹이 남아 있는 예전 결과 파일과도 맞대볼 수 있게 한다
og = {g.index: g.name for g in ours.vertex_groups if g.name.startswith("DEF-")}
rows = []
for v in ours.data.vertices:
    cand = [g for g in v.groups if g.group in og]
    best = max(cand, key=lambda g: g.weight, default=None)
    if best is None:
        rows.append((None, None, None)); continue
    co = ours.matrix_world @ v.co
    _, i, dist = tree.find(co)
    rows.append((og.get(best.group), src[i][1], dist))

done({"pairs": [[a, b, round(d, 4)] for a, b, d in rows if a and b],
      "unweighted": sum(1 for a, _, _ in rows if a is None),
      "verts": len(rows)}, A["result"])
