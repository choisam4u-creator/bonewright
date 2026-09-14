"""정답 자산의 포즈 변형본 만들기(토큰 0): T 포즈 캐릭터의 원본 뼈대로 팔을 내려 A 포즈 파일을 만든다.

왜 필요한가 — A 포즈 자산(cesium_man 7.3%, quaternius_ual 7.4%)이 T 포즈 자산(1.6~3.9%)보다 오차가 크지만
자산이 달라서 '포즈 탓'인지 '자산 탓'인지 가를 수 없다. 같은 자산의 팔만 내린 변형본이면 차이가 순수하게 포즈다.

절차: 원본 뼈대를 살려 가져온다 → 위팔 본을 어깨 기준으로 각도만큼 내린다 → 메시를 구워 그 자세로 굳힌다
→ 뼈대의 쉬는 자세도 그 자세로 굳힌다(armature_apply) → 다시 스킨을 붙여 glb 로 내보낸다.
내보낸 파일에는 스킨과 (내린 자세의) 정답 뼈대가 같이 들어 있어 gt_joints/bench 가 그대로 쓸 수 있다.
"""
import math
import re
import bpy
from mathutils import Matrix, Vector
from _common import args, done, fresh, import_mesh

A = args(); fresh()
obj = import_mesh(A["mesh"], facing=A.get("facing", "auto"), keep_armature=True)
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if arm is None:
    done({"error": "원본 뼈대가 없다"}, A["result"])


def core(name):
    n = name.lower().split(":")[-1]
    n = re.sub(r"[._-]?\d+$", "", n)
    side = None
    for pat, s in ((r"[._-]l$", "L"), (r"[._-]r$", "R"), (r"^l[._-]", "L"), (r"^r[._-]", "R"),
                   (r"left", "L"), (r"right", "R"), (r"[._-]l[._-]", "L"), (r"[._-]r[._-]", "R")):
        if re.search(pat, n):
            side = s; n = re.sub(pat, "", n); break
    return re.sub(r"[^a-z]", "", n), side


# 위팔 본 찾기: upperarm / arm(팔뚝 forearm 이 아닌 것) 규약
upper = {}
for b in arm.data.bones:
    c, s = core(b.name)
    if s and (c.endswith("upperarm") or c in ("arm", "biparm", "arm1", "armjoint1")):
        upper[s] = b.name
if len(upper) < 2:
    done({"error": f"위팔 본을 못 찾았다: {[b.name for b in arm.data.bones][:30]}"}, A["result"])

deg = float(A.get("angle_deg", 45.0))
arm.data.pose_position = "POSE"   # 가져오기가 REST 표시로 둔다 — 그 상태면 포즈 값을 넣어도 무시된다(두 번째 시도에서 확인)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
# 파일에 든 애니메이션 첫 프레임 자세를 지운다 — 안 지우면 내 회전이 그 위에 얹혀 팔이 앞으로도 휜다(세 번째 시도에서 확인)
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
moved = {}
for side, name in upper.items():
    pb = arm.pose.bones[name]
    # glTF 아마추어의 로컬 축은 Y-up 이라 로컬 "Y 축 회전"은 팔을 앞뒤로 휘두른다(첫 시도에서 손 높이가 그대로였다).
    # 그래서 회전을 월드 좌표(Z 위, 팔은 ±X, 앞은 -Y)에서 정의하고 아마추어 공간으로 옮겨 적용한다
    MW = arm.matrix_world
    head_w = MW @ pb.head
    before = (MW @ pb.tail).z
    sign = 1.0 if side == "L" else -1.0   # Y 축 +회전은 +X 를 -Z 로 보낸다 → 왼팔(+X)은 +각도, 오른팔은 -각도가 아래다(네 번째 시도에서 부호 확인)
    R_w = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(deg) * sign, 4, "Y") @ Matrix.Translation(-head_w)
    pb.matrix = MW.inverted() @ R_w @ MW @ pb.matrix
    bpy.context.view_layer.update()
    moved[side] = {"bone": name, "tail_before_z": round(before, 3), "tail_after_z": round((MW @ pb.tail).z, 3)}
bpy.ops.object.mode_set(mode="OBJECT")

# 메시를 그 자세로 굽는다. import_mesh 가 이미 아마추어 모디파이어를 굽고 없앴으므로(정점 그룹은 남아 있다)
# 모디파이어를 다시 붙인 뒤 굽는다 — 안 붙이면 굽기가 헛돌아 뼈대만 내려가고 메시는 T 포즈로 남는다(다섯 번째 시도에서 확인)
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
obj.parent = arm; obj.matrix_parent_inverse = arm.matrix_world.inverted()
am0 = obj.modifiers.new("Armature", "ARMATURE"); am0.object = arm
mw = obj.matrix_world.copy()
bpy.ops.object.convert(target="MESH"); obj.parent = None; obj.matrix_world = mw
# 뼈대의 쉬는 자세를 지금 자세로 굳힌다
bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE"); bpy.ops.pose.armature_apply(selected=False); bpy.ops.object.mode_set(mode="OBJECT")
# 스킨을 다시 붙인다(가중치는 그대로라 정점 그룹 이름으로 연결된다)
obj.parent = arm; obj.matrix_parent_inverse = arm.matrix_world.inverted()
am = obj.modifiers.new("Armature", "ARMATURE"); am.object = arm
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=A["out"], use_selection=True, export_apply=False, export_format="GLB",
                          export_skins=True, export_animations=False, export_yup=True)
done({"out": A["out"], "angle_deg": deg, "moved": moved, "verts": len(obj.data.vertices)}, A["result"])
