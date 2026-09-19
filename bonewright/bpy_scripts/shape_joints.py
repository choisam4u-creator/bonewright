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
from _medial import classify, read_shape, resample

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
# 역할을 알아낸 팔다리에는 **리그 이름**을 붙인다. 이름이 있어야 BVH 동작 리타겟이 이름으로 본을 찾을 수 있다.
# 마디 위치는 여전히 균등 분할이라 무릎·팔꿈치가 정확하지는 않다 — 이름은 '어느 사슬인가'만 알려 준다
NAMED = {
    "foot.L": ["thigh.L", "shin.L", "foot.L"], "foot.R": ["thigh.R", "shin.R", "foot.R"],
    "hand.L": ["upper_arm.L", "forearm.L", "hand.L"], "hand.R": ["upper_arm.R", "forearm.R", "hand.R"],
    "head": ["chest", "neck", "head"],
    "hind.L": ["thigh.L", "shin.L", "foot.L"], "hind.R": ["thigh.R", "shin.R", "foot.R"],
    "front.L": ["front_thigh.L", "front_shin.L", "front_foot.L"],
    "front.R": ["front_thigh.R", "front_shin.R", "front_foot.R"],
    "tail": ["tail.001", "tail.002", "tail.003"],
}
roles = classify(shape, H, st["min"][2], quad=QUAD) or {}
role_of = {}
for _r, _t in roles.items():
    role_of[id(_t)] = _r
root = [round(v, 5) for v in shape["root"][:3]]
joints = {}
# 몸통 본: 뿌리에서 위로. 팔다리 사슬이 전부 여기에 매달린다
joints["spine"] = {"head": root, "tail": [root[0], root[1], round(root[2] + H * 0.08, 5)], "parent": None, "deform": True}
limbs = []
# 순서가 중요하다: 머리 사슬을 먼저 만들어야 팔을 **가슴**에 매달 수 있다.
# 팔을 골반(spine)에 바로 매달면 척추가 돌 때 가슴이 통째로 끌려가 메시가 찢어진다(걷기 리타겟 렌더로 확인)
_order = {"head": 0, "hand.L": 1, "hand.R": 1, "front.L": 1, "front.R": 1,
          "foot.L": 2, "foot.R": 2, "hind.L": 2, "hind.R": 2, "tail": 3}
# 역할이 **다 밝혀졌으면** 나머지 끝점은 메시 돌기(어깨 봉우리·옷 주름)이지 팔다리가 아니다 → 버린다.
# 안 버리면 그 사슬이 제자리에 붙들려 있어 몸이 움직일 때 메시를 찢는다(걷기 리타겟에서 변형 65배)
# 끝점을 **버리지 않는다.** 사람 메시에서는 어깨 봉우리·옷 주름이 가짜 팔다리로 잡혀 군더더기가 생기지만,
# 길이로 걸러 보니 전갈 다리 10개 중 2~4개가 같이 잘렸다(중앙값 기준 4개, 최솟값 기준 2개). 군더더기 사슬은
# 자세·내보내기에 해롭지 않고, 진짜 팔다리를 잃는 건 해롭다 — 그래서 남긴다.
_tips = list(enumerate(shape["tips"]))
_tips.sort(key=lambda it: _order.get(role_of.get(id(it[1])), 9))
_ROOT_R = shape["root"][3] if len(shape["root"]) > 3 else 0.0


def _outside_torso(path):
    """경로에서 **몸통 안쪽 구간을 잘라낸다**. 안 자르면 '위팔' 본이 가슴 한가운데서 시작해, 돌 때 몸통을
    통째로 끌고 간다(걷기 리타겟 변형 44배). 머리·꼬리 사슬은 몸통을 포함해야 하므로 자르지 않는다.

    자를 자리는 **굵기가 가장 가파르게 꺾이는 목**이다. "몸통 굵기의 60% 아래" 같은 절대 기준은
    뿌리 구가 배에 놓이는 체형에서 목을 지나쳐 버린다(godot_player 팔→몸통 누수 17/31).
    굵기는 몸통에서 팔다리로 넘어갈 때 한 번 크게 꺾이므로, 그 꺾임 자리가 체형과 무관하게 목이다."""
    if _ROOT_R <= 0 or len(path) < 4:
        return path
    r = [q[3] if len(q) > 3 else 0.0 for q in path]
    n = len(r)
    lim = max(2, int(n * 0.6))          # 목은 앞쪽 절반쯤에 있다 — 끝 쪽의 잔잔한 변화에 속지 않는다
    best, bk = 0.0, None
    for k in range(1, lim):
        drop = r[k - 1] - r[min(n - 1, k + 1)]
        if drop > best:
            best, bk = drop, k
    if bk is None or best < _ROOT_R * 0.15:
        return path                      # 뚜렷한 목이 없으면(블롭·촉수) 손대지 않는다
    return path[max(0, bk - 1):] if n - bk >= 2 else path


for i, tip in _tips:
    _raw = [q for q in tip["path"]][::-1]                     # 몸통 쪽 → 끝 쪽
    _role = role_of.get(id(tip))
    if _role not in ("head", "tail"):
        _raw = _outside_torso(_raw)
    pts = resample(_raw, SEG + 1)
    if len(pts) < SEG + 1:
        continue
    role = role_of.get(id(tip))
    names = NAMED.get(role) if role else None
    # 팔은 가슴에, 나머지는 골반에 매단다(가슴이 아직 없으면 골반)
    parent = "chest" if (role in ("hand.L", "hand.R", "front.L", "front.R") and "chest" in joints) else "spine"
    made = []
    for j in range(SEG):
        a, b = pts[j], pts[j + 1]
        if (sum((b[k] - a[k]) ** 2 for k in range(3))) ** 0.5 < H * 1e-3:
            continue                                          # 길이 0 에 가까운 마디는 건너뛴다
        n = names[j] if (names and j < len(names)) else f"Limb{i + 1}_{j + 1}"
        if n in joints:
            n = f"Limb{i + 1}_{j + 1}"
        joints[n] = {"head": [round(v, 5) for v in a], "tail": [round(v, 5) for v in b],
                     "parent": parent, "deform": True}
        parent = n; made.append(n)
    if made:
        limbs.append({"role": role, "bones": made, "tip": [round(v, 3) for v in tip["p"]], "branch": round(tip["branch"], 4)})

if "chest" in joints:      # 골반 → 가슴이 이어지도록 골반 본 꼬리를 가슴 머리에 맞춘다
    joints["spine"]["tail"] = list(joints["chest"]["head"])
done({"joints": joints, "bones": len(joints), "limbs": len(limbs), "segments": SEG,
      "roles": {k: [round(v, 3) for v in t["p"]] for k, t in roles.items()},
      "named": sorted(n for n in joints if not n.startswith("Limb")),
      "tips_found": len(shape["tips"]), "tips_used": len(_tips),
      "root": root, "voxel": shape.get("voxel"), "spheres": shape.get("spheres"),
      "bridges": shape.get("bridges"), "limb_info": limbs,
      "height": round(H, 4)}, A["result"])
