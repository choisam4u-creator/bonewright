#!/usr/bin/env python3
"""입력 메시 → 리깅 결과(본 개수·이름 표)를 재현한다. 모델 호출 0회(BW_BACKEND=mock), 토큰 0.
Reproduce a rig from a mesh (bone count and name table). Zero model calls, zero tokens. `--help` follows BW_LANG.

    python3 examples/rig_sample.py                    # 절차적 캡슐 인형(자산 파일 없음)을 만들어 리깅
    python3 examples/rig_sample.py --preset quadruped # 절차적 캡슐 개(네 발)를 만들어 사족 리깅
    python3 examples/rig_sample.py adventurer         # tests/assets 의 CC0 캐릭터(1.9MB)를 리깅
    python3 examples/rig_sample.py path/to/x.glb      # 아무 메시나
    python3 examples/rig_sample.py --table adventurer # 저장소의 캐릭터, 리깅 없이 GLB 안의 스킨 본 표만(블렌더 불필요)
    python3 examples/rig_sample.py --motion           # 캡슐 인형을 리깅하고 절차 생성 BVH(손 흔들기 24프레임)를 리타겟

리깅에는 Blender(앱 또는 `pip install bpy==5.2.2`)가 필요하다. 결과는 examples/out/<이름>/ 에 남고
표는 examples/out/<이름>.md 로 쓴다. 결과 문서(표·요약)는 화면 언어와 상관없이 영어다 — sample-output 과 늘 같게. 무거운 자산은 저장소에 넣지 않는다 — `scripts/fetch_bench_assets.py` 로 받는다.
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
from bonewright.i18n import T  # noqa: E402  화면 언어(BW_LANG·로캘)를 따른다

OUT = ROOT / "examples" / "out"
SAMPLES = {"adventurer": ROOT / "tests" / "assets" / "quaternius_adventurer.glb"}
PROCEDURAL = {"humanoid": "capsule_doll", "quadruped": "capsule_dog"}   # 메시를 안 주면 절차적으로 만드는 것


def glb_skin_bones(path: Path) -> list[str]:
    """GLB 의 첫 스킨 관절 이름을 순서대로 돌려준다(순수 파이썬, 블렌더 불필요)."""
    data = Path(path).read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError(T(f"{path}: GLB 가 아니다 — .glb(바이너리 glTF)를 넣는다. .gltf 는 Blender 로 .glb 로 내보낸 뒤 쓴다",
                           f"{path}: not a GLB — give a .glb (binary glTF). Export a .gltf to .glb from Blender first"))
    n, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A:   # 'JSON'
        raise ValueError(T(f"{path}: 첫 청크가 JSON 이 아니다 — 파일이 깨졌는지 원본에서 다시 받는다",
                           f"{path}: the first chunk is not JSON — the file may be broken; download it again"))
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
    rows = [f"- {len(names)} bones · left {side['L']} · right {side['R']} · center {side['C']}", "",
            "| part | count | names |", "|---|---:|---|"]
    rows += [f"| {k} | {len(v)} | {', '.join(f'`{x}`' for x in v)} |" for k, v in groups.items()]
    return "\n".join(rows) + "\n"


# 절차 생성 BVH(라이선스 문제 없음): Mixamo 식 이름, Y 위, 미터, T 자세. (부모, 이름, 오프셋, 끝 오프셋)
WAVE_JOINTS = [
    (None, "Hips", (0, 0, 0), None),
    ("Hips", "Spine", (0, 0.10, 0), None), ("Spine", "Chest", (0, 0.15, 0), None),
    ("Chest", "Neck", (0, 0.20, 0), None), ("Neck", "Head", (0, 0.10, 0), (0, 0.15, 0)),
    ("Chest", "LeftShoulder", (0.05, 0.15, 0), None), ("LeftShoulder", "LeftArm", (0.12, 0, 0), None),
    ("LeftArm", "LeftForeArm", (0.27, 0, 0), None), ("LeftForeArm", "LeftHand", (0.25, 0, 0), (0.08, 0, 0)),
    ("Chest", "RightShoulder", (-0.05, 0.15, 0), None), ("RightShoulder", "RightArm", (-0.12, 0, 0), None),
    ("RightArm", "RightForeArm", (-0.27, 0, 0), None), ("RightForeArm", "RightHand", (-0.25, 0, 0), (-0.08, 0, 0)),
    ("Hips", "LeftUpLeg", (0.09, -0.05, 0), None), ("LeftUpLeg", "LeftLeg", (0, -0.42, 0), None),
    ("LeftLeg", "LeftFoot", (0, -0.42, 0), (0, -0.05, 0.12)),
    ("Hips", "RightUpLeg", (-0.09, -0.05, 0), None), ("RightUpLeg", "RightLeg", (0, -0.42, 0), None),
    ("RightLeg", "RightFoot", (0, -0.42, 0), (0, -0.05, 0.12)),
]


def wave_bvh(path: Path, frames: int = 24) -> Path:
    """왼팔은 내리고 오른팔을 들어 아래팔을 흔드는 짧은 BVH 를 쓴다(순수 파이썬, 매번 같은 파일)."""
    import math
    kids: dict = {}
    for parent, name, off, end in WAVE_JOINTS:
        kids.setdefault(parent, []).append((name, off, end))
    lines = ["HIERARCHY"]

    def emit(name, off, end, depth):
        pad = "\t" * depth
        lines.append(f"{pad}{'ROOT' if depth == 0 else 'JOINT'} {name}")
        lines.append(pad + "{")
        lines.append(f"{pad}\tOFFSET {off[0]:.4f} {off[1]:.4f} {off[2]:.4f}")
        lines.append(f"{pad}\tCHANNELS " + ("6 Xposition Yposition Zposition " if depth == 0 else "3 ") + "Zrotation Xrotation Yrotation")
        for k in kids.get(name, []):
            emit(*k, depth + 1)
        if end:
            lines.extend([f"{pad}\tEnd Site", f"{pad}\t{{", f"{pad}\t\tOFFSET {end[0]:.4f} {end[1]:.4f} {end[2]:.4f}", f"{pad}\t}}"])
        lines.append(pad + "}")

    emit("Hips", (0, 0, 0), None, 0)
    lines += ["MOTION", f"Frames: {frames}", f"Frame Time: {1 / 24:.6f}"]
    order = []
    def walk(name):
        order.append(name)
        for k in kids.get(name, []):
            walk(k[0])
    walk("Hips")
    for f in range(frames):
        w = math.sin(2 * math.pi * f / 12)   # 0.5초에 한 번 흔든다
        rot = {"LeftArm": (-70, 0, 0), "RightArm": (-60, 0, 0), "RightForeArm": (-30 + 25 * w, 0, 0),
               "LeftLeg": (0, 5, 0), "RightLeg": (0, 5, 0)}   # (Z, X, Y) 도
        vals = [0.01 * w, 0.95, 0.0, 0, 0, 0]
        for name in order[1:]:
            vals += rot.get(name, (0, 0, 0))
        lines.append(" ".join(f"{v:.4f}" for v in vals))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def motion_and_report(name: str) -> Path:
    """rig_and_table 로 리깅한 `name` 에 wave_bvh 를 리타겟하고 결과 요약을 examples/out/<name>_motion.md 로 쓴다."""
    from bonewright import pipeline
    bvh = wave_bvh(OUT / "wave.bvh")
    run = f"{name}_motion"
    pipeline.motion(OUT, bvh=str(bvh), run_id=run, quiet=True, rig_run=name)
    rt = json.loads((OUT / "runs" / run / "retarget.json").read_text())
    mapped = rt["mapped"]
    pairs = sorted(mapped.items()) if isinstance(mapped, dict) else [(m, "") for m in sorted(mapped)]
    rep = (OUT / "runs" / run / "report.md").read_text(encoding="utf-8").splitlines()
    keep = [ln for ln in rep if ln.startswith(("- source:", "- armature:", "- retarget →", "- legs:"))]
    keep = [re.sub(r" · roll transfer:.*", "", ln) for ln in keep]   # 숫자 오차는 기계마다 조금씩 달라 뺀다
    keep = [re.sub(r"bvh: .*[/\\]", "bvh: examples/out/", ln) for ln in keep]   # 절대 경로(홈 폴더)를 싣지 않는다
    frames = re.search(r"frames \[(\d+), (\d+)\]", "\n".join(keep))
    nframes = int(frames[2]) - int(frames[1]) + 1 if frames else 0
    md = [f"# {name}: procedural BVH (hand wave) → retarget result", "",
          f"- BVH joints {len(WAVE_JOINTS)} · frames {nframes} · mapped {len(pairs)} · unmapped BVH joints {len(rt['unmapped'])}",
          "", "## Mapped joints", "", "| BVH joint | rig control |", "|---|---|"]
    md += [f"| `{a}` | {f'`{b}`' if b else ''} |" for a, b in pairs]
    md += ["", "## report.md excerpt", "", *keep, ""]
    out = OUT / f"{name}_motion.md"
    out.write_text("\n".join(md), encoding="utf-8")
    return out


def rig_and_table(mesh: Path | None, name: str, preset: str) -> Path:
    from bonewright import blender, pipeline
    if not (blender.find_blender({}) or blender.has_bpy_module()):
        here = Path(__file__).resolve()   # 저장소 폴더 밖에서 돌렸으면 이 파일의 실제 경로로(10/11 12회차)
        me = "examples/rig_sample.py" if Path("examples/rig_sample.py").resolve() == here else (f'"{here}"' if " " in str(here) else str(here))
        raise SystemExit(T("Blender 가 없다 — Blender 5.2 LTS 를 설치하거나 `pip install bpy==5.2.2`(파이썬 3.13), "
                           "또는 BW_BLENDER 에 실행 파일 경로를 넣는다. Blender 없이 본 표만 보려면: "
                           f"python3 {me} --table adventurer",
                           "Blender not found — install Blender 5.2 LTS or `pip install bpy==5.2.2` (Python 3.13), "
                           "or put the executable's path in BW_BLENDER. For the bone table alone, without Blender: "
                           f"python3 {me} --table adventurer"))
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
    md = [f"# {name}: `{mesh.name}` → rig result", "",
          f"- gates: **{status}** · rig bones {st['rig_bones']} (deform {st['deform_bones']}) · unweighted vertices {st['unweighted_verts']}",
          f"- skin bones already in the input file: {len(src)} (dropped and rebuilt when rigging)" if src else "- no skin bones in the input file",
          "", "## Deform bones in the exported GLB", "", bone_table(glb_skin_bones(glb))]
    out = OUT / f"{name}.md"
    out.write_text("\n".join(md), encoding="utf-8")
    return out


def main() -> int:
    p = argparse.ArgumentParser(
        description=T("입력 메시 → 리깅 결과(본 개수·이름 표)를 재현한다. 모델 호출 0회(BW_BACKEND=mock), 토큰 0.",
                      "Reproduce a rig from a mesh (bone count and name table). Zero model calls (BW_BACKEND=mock), zero tokens."),
        epilog=T("리깅에는 Blender(앱 또는 `pip install bpy==5.2.2`)가 필요하다. 결과는 examples/out/ 에 남는다.",
                 "Rigging needs Blender (the app or `pip install bpy==5.2.2`). Results go to examples/out/."))
    p.add_argument("mesh", nargs="?", help=T("'adventurer', .glb/.gltf 경로, 생략하면 절차적 캡슐 인형",
                                             "'adventurer', a .glb/.gltf path, or omit for a procedural capsule doll"))
    p.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid",
                   help=T("메시를 안 주면 만들 절차 인형·리그 종류(기본 humanoid)",
                          "rig type, and the procedural mesh to build when none is given (default humanoid)"))
    p.add_argument("--table", action="store_true", help=T("리깅하지 않고 GLB 안의 스킨 본 표만 찍는다(블렌더 불필요)",
                                                          "print the skin bone table inside a GLB without rigging (no Blender needed)"))
    p.add_argument("--motion", action="store_true",
                   help=T("리깅 뒤 절차 생성 BVH(손 흔들기)를 리타겟해 요약을 쓴다(사람 프리셋)",
                          "after rigging, retarget a procedural BVH (hand wave) and write a summary (humanoid preset)"))
    a = p.parse_args()
    if a.motion and a.preset != "humanoid":   # 리깅(수십 초) 전에 막는다 — 기다린 뒤 거절하지 않게
        raise SystemExit(T("--motion 은 사람 프리셋에서만 돈다(절차 BVH 가 사람 뼈대다)",
                           "--motion works with the humanoid preset only (the procedural BVH is a human skeleton)"))
    if a.motion and a.table:
        raise SystemExit(T("--motion 과 --table 은 같이 쓸 수 없다 — --table 은 리깅하지 않는다",
                           "--motion and --table do not go together — --table does not rig"))
    mesh = SAMPLES.get(a.mesh, Path(a.mesh)) if a.mesh else None
    if mesh is not None and not mesh.exists():
        raise SystemExit(T(f"파일이 없다: {mesh} — 경로를 확인하거나 'adventurer' 를 쓴다. "
                           "벤치 자산은 `python3 scripts/fetch_bench_assets.py` 로 받는다",
                           f"file not found: {mesh} — check the path or use 'adventurer'. "
                           "Benchmark assets come from `python3 scripts/fetch_bench_assets.py`"))
    if a.table:
        if mesh is None:
            raise SystemExit(T("--table 에는 .glb 경로가 필요하다 (예: --table adventurer)",
                               "--table needs a .glb path (e.g. --table adventurer)"))
        print(bone_table(glb_skin_bones(mesh)), end="")
        return 0
    name = a.mesh if a.mesh in SAMPLES else (mesh.stem if mesh else PROCEDURAL[a.preset])
    out = rig_and_table(mesh, name, a.preset)
    print(out.read_text(encoding="utf-8"), end="")
    print("\n" + T("표: ", "table: ") + str(out.relative_to(ROOT)))
    if a.motion:
        mo = motion_and_report(name)
        print("\n" + mo.read_text(encoding="utf-8"), end="")
        print("\n" + T("리타겟 요약: ", "retarget summary: ") + str(mo.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
