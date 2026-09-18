"""라이선스 경계 검사(토큰 0): `bonewright/` 본체는 MIT 이고 `bonewright/bpy_scripts/` 는 GPL 이다.

경계가 성립하려면 **본체가 bpy 를 import 하지 않아야** 한다. 본체에서 bpy 를 쓰기 시작하면 그 파일은
Blender 파생물이 되어 MIT 로 배포할 수 없다. 사람이 기억해서 지킬 규칙이 아니라 CI 가 지킬 규칙이다.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "bonewright"
GPL = CORE / "bpy_scripts"
BLENDER_MODULES = {"bpy", "bmesh", "mathutils", "bpy_extras", "aud", "gpu", "bl_ui"}

bad = []
for p in sorted(CORE.rglob("*.py")):
    if GPL in p.parents or p == GPL:
        continue
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods = [node.module.split(".")[0]]
        for m in mods:
            if m in BLENDER_MODULES:
                bad.append(f"{p.relative_to(ROOT)}:{node.lineno}: MIT 영역에서 '{m}' 를 import 한다")

need = [GPL / "LICENSE", GPL / "README.md", ROOT / "LICENSE"]
missing = [str(p.relative_to(ROOT)) for p in need if not p.exists()]
if missing:
    bad.append("라이선스 파일 없음: " + ", ".join(missing))

if bad:
    print("라이선스 경계 위반:", file=sys.stderr)
    for b in bad:
        print("  -", b, file=sys.stderr)
    sys.exit(1)
print(f"라이선스 경계 OK — MIT 영역 {sum(1 for p in CORE.rglob('*.py') if GPL not in p.parents)}개 파일이 bpy 를 쓰지 않는다")
