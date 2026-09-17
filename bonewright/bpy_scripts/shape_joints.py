"""메시 속 중심선에서 **뼈대를 직접 만든다**(토큰 0).

원본 뼈대가 없고 사람·개과 비율도 아닌 메시(곤충·괴물·양식화)는 관절을 찾을 근거가 없어서 거절해 왔다.
하지만 속 읽기(_medial)는 자세·비례와 무관하게 **팔다리 끝과 거기까지 가는 길**을 찾는다. 그 길을 따라
본을 심으면 곧 뼈대다. 그 뒤는 일반 리그(fit_generate 의 generic 경로)가 그대로 받는다.

**이 뼈대가 무엇이고 무엇이 아닌지 분명히 한다.**
  · 이다: 메시 모양을 따라가는 **조작 장치**. 팔다리마다 사슬이 생기고 컨트롤이 붙는다.
  · 아니다: 해부학적 관절. 마디는 길이를 균등하게 나눈 자리이지 무릎·팔꿈치가 아니다.
    사람이나 개과 체형이면 `--preset` 경로가 훨씬 정확하다 — 그쪽이 안 될 때만 쓰는 길이다.
"""
import bpy

from _common import args, done, fresh, import_mesh, mesh_stats
from _medial import read_shape, resample

A = args(); fresh()
QUAD = A.get("preset") == "quadruped"
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"), quad=QUAD)
st = mesh_stats(obj)
H = st["height"] or 1.0
shape = read_shape(obj, st["min"], st["max"], grid=int(A.get("grid", 56)))
if not shape:
    done({"joints": {}, "bones": 0, "error": "메시 속에서 중심선을 못 찾았다(속이 비었거나 너무 얇다)"}, A["result"])
    raise SystemExit

SEG = max(2, int(A.get("segments", 3)))      # 팔다리 하나를 몇 마디로 나눌지
root = [round(v, 5) for v in shape["root"][:3]]
joints = {}
# 몸통 본: 뿌리에서 위로. 팔다리 사슬이 전부 여기에 매달린다
joints["Body"] = {"head": root, "tail": [root[0], root[1], round(root[2] + H * 0.08, 5)], "parent": None, "deform": True}
limbs = []
for i, tip in enumerate(shape["tips"]):
    pts = resample([q for q in tip["path"]][::-1], SEG + 1)   # 몸통 쪽 → 끝 쪽
    if len(pts) < SEG + 1:
        continue
    parent = "Body"
    made = []
    for j in range(SEG):
        a, b = pts[j], pts[j + 1]
        if (sum((b[k] - a[k]) ** 2 for k in range(3))) ** 0.5 < H * 1e-3:
            continue                                          # 길이 0 에 가까운 마디는 건너뛴다
        n = f"Limb{i + 1}_{j + 1}"
        joints[n] = {"head": [round(v, 5) for v in a], "tail": [round(v, 5) for v in b],
                     "parent": parent, "deform": True}
        parent = n; made.append(n)
    if made:
        limbs.append({"bones": made, "tip": [round(v, 3) for v in tip["p"]], "branch": round(tip["branch"], 4)})

done({"joints": joints, "bones": len(joints), "limbs": len(limbs), "segments": SEG,
      "root": root, "voxel": shape.get("voxel"), "spheres": shape.get("spheres"),
      "bridges": shape.get("bridges"), "limb_info": limbs,
      "height": round(H, 4)}, A["result"])
