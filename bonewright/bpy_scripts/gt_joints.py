"""정답 뼈대 추출(토큰 0): 원본 스켈레톤이 들어 있는 파일을 우리와 '똑같이 정규화한 공간'으로 옮겨
관절(본 head) 좌표를 뽑는다. 벤치마크에서 우리 리깅 결과와 cm 단위로 비교하는 기준이 된다."""
import bpy
from _common import args, done, fresh, import_mesh, IMPORT_INFO
A = args(); fresh()
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"), keep_armature=True,
                  quad=A.get("preset") == "quadruped")
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not arms:
    done({"joints": {}, "bones": 0, "error": "원본 아마추어 없음"}, A["result"]); raise SystemExit
arm = max(arms, key=lambda a: len(a.data.bones))
# 원본에서 **실제로 살을 움직이는 본**만 골라 둔다. glTF 가져오기는 모든 관절에 use_deform 을 켜 두므로
# 그 표시로는 정리용 본(Root)을 못 가른다 — 정점 가중치가 실제로 붙어 있는지로 본다
_gi = {g.index: g.name for g in obj.vertex_groups}
_used = set()
for v in obj.data.vertices:
    for g in v.groups:
        if g.weight > 1e-4:
            n_ = _gi.get(g.group)
            if n_: _used.add(n_)
joints = {}
for b in arm.data.bones:
    h = arm.matrix_world @ b.head_local; t = arm.matrix_world @ b.tail_local
    joints[b.name] = {"head": [round(v, 4) for v in h], "tail": [round(v, 4) for v in t],
                      "parent": b.parent.name if b.parent else None,
                      # 원본이 살을 안 움직이는 본(Root 같은 정리용)은 일반 리그에서도 변형 본으로 만들지 않는다
                      "deform": (b.name in _used) if _used else bool(b.use_deform)}
# **원작자 자신의 '팔→몸통 누수'도 같이 잰다(보정용).** 우리 리그를 재는 것과 똑같은 규칙을 원본
# 가중치에 대고 돌린다. 체형에 따라 사람이 일부러 그렇게 칠하기도 하기 때문이다 — 치비(quat_pp_43j)는
# 팔이 몸에 붙어 있어 **원작자가 39.2%** 를 칠했다. 그런 자산에서 우리 2.9% 를 결함이라 부르면 거짓이다.
# 반대로 KayKit 해골 전사는 원작자가 **0%** 라, 우리 11.7% 는 변명할 수 없는 진짜 결함이다.
_ARMW = ("arm", "hand", "shoulder", "elbow", "wrist", "clavicle")
_armb = {b.name for b in arm.data.bones if any(w in b.name.lower() for w in _ARMW)}
_zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
_H = (max(_zs) - min(_zs)) or 1.0
_z0 = min(_zs)
_ax = [abs((arm.matrix_world @ b.head_local).x) for b in arm.data.bones
       if b.name in _armb and "hand" not in b.name.lower()]
_band = min(0.04 * _H, 0.35 * (sum(_ax) / len(_ax))) if _ax else 0.04 * _H
_cands = []
for v in obj.data.vertices:
    pw = obj.matrix_world @ v.co
    if not (_z0 + 0.45 * _H < pw.z < _z0 + 0.70 * _H):
        continue
    w = {_gi.get(g.group, ""): g.weight for g in v.groups if g.weight > 0}
    t = sum(w.values())
    if not t:
        continue
    _cands.append((abs(pw.x), sum(val for k, val in w.items() if k in _armb) / t))
_cands.sort()
_sel = [c for c in _cands if c[0] < _band]
if len(_sel) < 30:
    _wide = min(0.06 * _H, 0.5 * (sum(_ax) / len(_ax))) if _ax else 0.06 * _H
    _sel = [c for c in _cands if c[0] < max(_band, _wide)][:30]
_leak = sum(1 for _d, sh in _sel if sh > 0.15)
source_leak = {"samples": len(_sel), "leak": _leak, "ratio": round(_leak / len(_sel), 4) if _sel else None}
vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
zs = [v.z for v in vs]
done({"joints": joints, "bones": len(joints), "armature": arm.name,
      "height": round(max(zs) - min(zs), 4), "source_leak": source_leak, "import": dict(IMPORT_INFO)}, A["result"])
