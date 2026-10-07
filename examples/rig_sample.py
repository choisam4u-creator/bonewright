#!/usr/bin/env python3
"""입력 메시 → 리깅 결과(본 개수·이름 표)를 재현한다. 모델 호출 0회(BW_BACKEND=mock), 토큰 0.

    python3 examples/rig_sample.py                    # 절차적 캡슐 인형(자산 파일 없음)을 만들어 리깅
    python3 examples/rig_sample.py --preset quadruped # 절차적 캡슐 개(네 발)를 만들어 사족 리깅
    python3 examples/rig_sample.py adventurer         # tests/assets 의 CC0 캐릭터(1.9MB)를 리깅
    python3 examples/rig_sample.py path/to/x.glb      # 아무 메시나
    python3 examples/rig_sample.py --table x.glb      # 리깅 없이 GLB 안의 스킨 본 표만(블렌더 불필요)

리깅에는 Blender(앱 또는 `pip install bpy==5.2.2`)가 필요하다. 결과는 examples/out/<이름>/ 에 남고
표는 examples/out/<이름>.md 로 쓴다. 무거운 자산은 저장소에 넣지 않는다 — `scripts/fetch_bench_assets.py` 로 받는다.
"""
import argparse
import json
import os
import re
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "examples" / "out"
SAMPLES = {"adventurer": ROOT / "tests" / "assets" / "quaternius_adventurer.glb"}
PROCEDURAL = {"humanoid": "capsule_doll", "quadruped": "capsule_dog"}   # 메시를 안 주면 절차적으로 만드는 것


def glb_skin_bones(path: Path) -> list[str]:
    """GLB 의 첫 스킨 관절 이름을 순서대로 돌려준다(순수 파이썬, 블렌더 불필요)."""
    data = Path(path).read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError(f"{path}: GLB 가 아니다 — .glb(바이너리 glTF)를 넣는다. .gltf 는 Blender 로 .glb 로 내보낸 뒤 쓴다")
    n, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A:   # 'JSON'
        raise ValueError(f"{path}: 첫 청크가 JSON 이 아니다 — 파일이 깨졌는지 원본에서 다시 받는다")
    gltf = json.loads(data[20:20 + n])
    skins = gltf.get("skins") or []
    if not skins:
        return []
    nodes = gltf.get("nodes", [])
    return [nodes[j].get("name", f"node{j}") for j in skins[0]["joints"]]


def bone_table(names: list[str]) -> str:
    """본 이름 표(마크다운): 개수, 좌/우/가운데 분포, 부위별 묶음."""
    side = Counter("L" if re.search(r"[._](L|l|Left)$|^Left", n) else "R" if re.search(r"[._](R|r|Right)$|^Right", n) else "C"
                   for n in names)
    groups: dict[str, list[str]] = {}
    for n in names:
        key = re.sub(r"^(DEF-|ORG-|MCH-)", "", n)
        key = re.split(r"[.\d]", key)[0] or n
        groups.setdefault(key, []).append(n)
    rows = [f"- 본 {len(names)}개 · 왼쪽 {side['L']} · 오른쪽 {side['R']} · 가운데 {side['C']}", "",
            "| 부위 | 개수 | 이름 |", "|---|---:|---|"]
    rows += [f"| {k} | {len(v)} | {', '.join(f'`{x}`' for x in v)} |" for k, v in groups.items()]
    return "\n".join(rows) + "\n"


def rig_and_table(mesh: Path | None, name: str, preset: str) -> Path:
    from bonewright import blender, pipeline
    if not (blender.find_blender({}) or blender.has_bpy_module()):
        raise SystemExit("Blender 가 없다 — Blender 5.2 LTS 를 설치하거나 `pip install bpy==5.2.2`(파이썬 3.13), "
                         "또는 BW_BLENDER 에 실행 파일 경로를 넣는다. 표만 보려면 --table x.glb")
    os.environ["BW_BACKEND"] = "mock"
    os.environ.setdefault("BW_NO_RENDER", "1")
    OUT.mkdir(parents=True, exist_ok=True)
    if mesh is None:   # 절차적 캡슐 인형(사람) 또는 캡슐 개(사족)
        mesh = OUT / f"{name}.glb"
        blender.run_script("make_test_mesh", {"out": str(mesh), "kind": preset}, {}, OUT / "logs")
    src = glb_skin_bones(mesh) if mesh.suffix.lower() == ".glb" else []
    pipeline.rig(OUT, str(mesh), preset, run_id=name, quiet=True, no_judge=True)
    glb = pipeline.export_rig(OUT, name, quiet=True)
    st = json.loads((OUT / "runs" / name / "rig_stats.json").read_text())["stats"]
    status = json.loads((OUT / "runs" / name / "state.json").read_text())["status"]
    md = [f"# {name}: `{mesh.name}` → 리깅 결과", "",
          f"- 관문: **{status}** · 리그 본 {st['rig_bones']}(변형 {st['deform_bones']}) · 가중치 없는 정점 {st['unweighted_verts']}",
          f"- 입력 파일의 원래 스킨 본: {len(src)}개 (리깅할 때 버리고 새로 만든다)" if src else "- 입력 파일에 스킨 본 없음",
          "", "## 내보낸 GLB 의 변형 본", "", bone_table(glb_skin_bones(glb))]
    out = OUT / f"{name}.md"
    out.write_text("\n".join(md), encoding="utf-8")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mesh", nargs="?", help="'adventurer', .glb/.gltf 경로, 생략하면 절차적 캡슐 인형")
    p.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid")
    p.add_argument("--table", action="store_true", help="리깅하지 않고 GLB 안의 스킨 본 표만 찍는다(블렌더 불필요)")
    a = p.parse_args()
    mesh = SAMPLES.get(a.mesh, Path(a.mesh)) if a.mesh else None
    if mesh is not None and not mesh.exists():
        raise SystemExit(f"파일이 없다: {mesh} — 경로를 확인하거나 'adventurer' 를 쓴다. "
                         "벤치 자산은 `python3 scripts/fetch_bench_assets.py` 로 받는다")
    if a.table:
        if mesh is None:
            raise SystemExit("--table 에는 .glb 경로가 필요하다 (예: --table adventurer)")
        print(bone_table(glb_skin_bones(mesh)), end="")
        return 0
    name = a.mesh if a.mesh in SAMPLES else (mesh.stem if mesh else PROCEDURAL[a.preset])
    out = rig_and_table(mesh, name, a.preset)
    print(out.read_text(encoding="utf-8"), end="")
    print(f"\n표: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
