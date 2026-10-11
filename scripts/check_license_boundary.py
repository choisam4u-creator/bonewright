"""라이선스 경계 검사(토큰 0): `bonewright/` 본체는 MIT 이고 `bonewright/bpy_scripts/` 는 GPL 이다.

경계가 성립하려면 **본체가 bpy 를 import 하지 않아야** 한다. 본체에서 bpy 를 쓰기 시작하면 그 파일은
Blender 파생물이 되어 MIT 로 배포할 수 없다. 사람이 기억해서 지킬 규칙이 아니라 CI 가 지킬 규칙이다.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bonewright.i18n import T  # noqa: E402  화면 언어(BW_LANG·로캘)를 따른다

BLENDER_MODULES = {"bpy", "bmesh", "mathutils", "bpy_extras", "aud", "gpu", "bl_ui"}


def problems(root: Path) -> tuple[list[str], int]:
    """(위반 줄 목록, 검사한 MIT 파일 수). 위반 줄마다 고칠 방법(→)을 붙인다."""
    core, gpl = root / "bonewright", root / "bonewright" / "bpy_scripts"
    bad, checked = [], 0
    # 저장소 전체(examples·scripts·tests·spikes 포함): LICENSE 는 bpy_scripts/ 말고 전부 MIT 라 적는다.
    # 10/11 까지는 bonewright/ 만 봐서 spikes/ 의 bpy 스크립트 3개를 못 잡았다(샘님 결정으로 삭제)
    skip = {".git", ".venv", "venv", "build", "dist", "node_modules", "vendor", "__pycache__"}
    for p in sorted(root.rglob("*.py")):
        if gpl in p.parents or skip & set(p.relative_to(root).parts):
            continue
        checked += 1
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module.split(".")[0]]
            for m in mods:
                if m in BLENDER_MODULES:
                    where = f"{p.relative_to(root).as_posix()}:{node.lineno}"
                    bad.append(T(f"{where}: MIT 영역에서 '{m}' 를 import 한다\n"
                                 f"      → Blender 를 쓰는 코드는 bonewright/bpy_scripts/(GPL)로 옮기고 blender.run_script 로 부른다",
                                 f"{where}: MIT-licensed code imports '{m}'\n"
                                 f"      → move Blender code into bonewright/bpy_scripts/ (GPL) and call it with blender.run_script"))
    need = [gpl / "LICENSE", gpl / "README.md", root / "LICENSE"]
    missing = [p.relative_to(root).as_posix() for p in need if not p.exists()]
    if missing:
        bad.append(T("라이선스 파일 없음: ", "licence files missing: ") + ", ".join(missing)
                   + T("\n      → git 에서 되살린다(배포본에 MIT·GPL 고지가 둘 다 실려야 한다)",
                       "\n      → restore them from git (the package must ship both the MIT and the GPL notice)"))
    return bad, checked


def main() -> int:
    bad, checked = problems(ROOT)
    if bad:
        print(T("라이선스 경계 위반:", "licence boundary violated:"), file=sys.stderr)
        for b in bad:
            print("  -", b, file=sys.stderr)
        return 1
    print(T(f"라이선스 경계 OK — MIT 영역(bpy_scripts/ 밖 저장소 전체) {checked}개 파일이 bpy 를 쓰지 않는다",
            f"licence boundary OK — {checked} files outside bpy_scripts/ (MIT) do not use bpy"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
