"""bw: bonewright 명령줄. rig · motion · demo · bench · doctor · status · usage · plugin-path"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, bench, pipeline
from .blender import find_blender, has_bpy_module
from .config import find_root, load
from .ledger import summarize

ROOT = find_root()


def doctor() -> int:
    ok = True
    cfg = load(ROOT)
    bl = find_blender(cfg["blender"])
    print("Blender:", bl[0] if bl else "없음 (Blender.app 설치 또는 BW_BLENDER)")
    if bl:
        v = subprocess.run(bl + ["--version"], capture_output=True, text=True).stdout.splitlines()
        print("  ", v[0] if v else "?")
    else:
        print("bpy 모듈:", "있음" if has_bpy_module() else "없음 (pip install bpy==5.2.2, Python 3.13)"); ok &= has_bpy_module()
    codex = shutil.which("codex")
    print("codex CLI:", codex or "없음 → https://developers.openai.com/codex"); ok &= bool(codex)
    if codex:
        print("  ", subprocess.run(["codex", "--version"], capture_output=True, text=True).stdout.strip())
        login = subprocess.run(["codex", "login", "status"], capture_output=True, text=True)
        print("   로그인:", (login.stdout or login.stderr).strip()[:60])
    k = ROOT / cfg["kimodo"]["root"] / "build-release" / "kmd-generate"
    print("kimodo.cpp:", "빌드됨" if k.exists() else "없음 (선택: 텍스트→동작에만 필요)")
    print("작업 폴더(ROOT):", ROOT, "(BW_HOME 으로 바꿀 수 있음)")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(prog="bw", description=f"bonewright {__version__}: Python drives, Codex judges, gates verify.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rig", help="메시를 Rigify 로 리깅하고 검증한다")
    r.add_argument("mesh"); r.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid")
    r.add_argument("--run-id"); r.add_argument("--lang", choices=["ko", "en"]); r.add_argument("--budget", type=int)
    r.add_argument("--no-judge", action="store_true", help="시각 판정(모델 호출) 생략"); r.add_argument("--facing", choices=["auto", "neg-y", "pos-y"], default="auto", help="캐릭터가 보는 방향. auto=발 방향으로 판단해 -Y 로 맞춤"); r.add_argument("--quiet", action="store_true")
    r.add_argument("--force", action="store_true", help="거절 게이트를 무시하고 진행(비인간·크기 이상 메시도 리깅 시도)")
    r.add_argument("--from-shape", action="store_true", help="메시 속 중심선에서 뼈대를 직접 만들어 리깅한다(토큰 0). 뼈대가 없고 사람·개과 비율도 아닌 메시(곤충·괴물)에 쓴다 — 해부학적 관절이 아니라 모양을 따라가는 조작 장치다")
    r.add_argument("--from-skeleton", action="store_true", help="파일에 든 원본 뼈대의 관절을 그대로 써서 Rigify 리그를 만든다(토큰 0). 실루엣으로 관절을 못 찾는 로봇·양식화 캐릭터에 쓴다")
    r.add_argument("--rest-pose", choices=["keep", "t"], default=None, help="쉬는 자세: keep=메시 자세 그대로(기본), t=팔을 수평으로 굳혀 T 포즈로")
    r.add_argument("--weights", choices=["auto", "proxy"], default=None, help="스키닝: auto=Bone Heat(비면 복셀 대리), proxy=항상 복셀 대리")
    r.add_argument("--pin", action="append", metavar="본=x,y,z[/x,y,z]",
                   help="관절을 직접 고정한다. 예: --pin spine.004=0,0,1.42 (머리만), --pin hand.L=0.6,0,1.3/0.7,0,1.3 (머리/꼬리). 여러 번 쓸 수 있다")
    r.add_argument("--targets", metavar="targets.json", help="이전 실행의 targets.json 을 그대로 쓴다(모델 호출 0회, 토큰 0)")
    m = sub.add_parser("motion", help="텍스트(kimodo.cpp) 또는 BVH 에서 동작을 만들어 Blender 로 가져온다")
    m.add_argument("--text"); m.add_argument("--bvh"); m.add_argument("--run-id"); m.add_argument("--quiet", action="store_true")
    m.add_argument("--rig", help="리깅 결과 run-id: 그 리그에 동작을 옮긴다(리타겟, 토큰 0)")
    m.add_argument("--preset", choices=["humanoid", "quadruped"], default=None, help="리그의 프리셋. 생략하면 리그 실행 기록(rig_stats.json)에서 읽는다")
    m.add_argument("--bvh-up", choices=["auto", "y", "z"], default="auto", help="BVH 의 위 축. auto=머리와 발 위치로 판단(기본). 표준은 y, Blender 가 내보낸 BVH 는 z")
    m.add_argument("--legs", choices=["auto", "fk", "ik"], default="auto", help="다리 전달: auto(소스에 발끝 관절이 있는 다리만 IK) | fk(회전만) | ik(발 IK 로 BVH 발끝을 좇음, 비율 차이 흡수)")
    m.add_argument("--no-roll", action="store_true", help="리타겟에서 비틀림(롤)을 옮기지 않는다(방향만, A/B 비교용)")
    m.add_argument("--map", dest="bone_map", metavar="bones.json",
                   help='BVH 본 → 리그 본 매핑 파일 {"LeftArm": "upper_arm.L"}. 이름이 없는 리그(모양 리그의 Limb3_2 등)는 자동 매핑이 못 붙으니 직접 적는다')
    m.add_argument("--export", nargs="?", const="auto", help="리타겟 결과를 GLB 로 내보낸다(변형 본만·애니 구움). 경로 생략 시 runs/<id>/animated.glb")
    ex = sub.add_parser("export", help="리그 결과를 변형 본만 든 GLB 로 내보내기(게임 엔진용), 토큰 0")
    ex.add_argument("run_id"); ex.add_argument("--out", help="출력 경로(기본 runs/<id>/rigged.glb)"); ex.add_argument("--quiet", action="store_true")
    d = sub.add_parser("demo", help="리그 결과를 IK 로 움직인 데모 영상(mp4/gif) 만들기, 토큰 0")
    d.add_argument("run_id"); d.add_argument("--size", type=int, default=640); d.add_argument("--frames", type=int, default=96); d.add_argument("--quiet", action="store_true")
    bm = sub.add_parser("bench", help="원본 뼈대가 든 캐릭터로 관절 오차를 cm 단위로 잰다(토큰 0)")
    bm.add_argument("meshes", nargs="+", help="GLB/FBX 파일 또는 폴더")
    bm.add_argument("--run-id"); bm.add_argument("--facing", choices=["auto", "neg-y", "pos-y"], default="auto")
    bm.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid")
    bm.add_argument("--rest-pose", choices=["keep", "t"], default=None, help="리깅할 때 쉬는 자세를 T 로 굳힌다(포즈 정규화 측정용)")
    bm.add_argument("--gt-mesh", help="정답 뼈대를 이 파일에서 가져온다(포즈 변형본을 원본 T 포즈와 맞댈 때)")
    bm.add_argument("--quiet", action="store_true")
    bm.add_argument("--skin", action="store_true", help="스키닝 일치도도 잰다(원본 가중치와 대조, 토큰 0)")
    bm.add_argument("--weights", choices=["auto", "proxy"], default=None, help="스키닝 방법 강제(A/B 비교용)")
    st = sub.add_parser("status"); st.add_argument("run_id", nargs="?")
    u = sub.add_parser("usage"); u.add_argument("--days", type=int, default=7)
    for name in ("doctor", "plugin-path"):
        sub.add_parser(name)
    a = p.parse_args()
    if a.cmd == "doctor":
        return doctor()
    if a.cmd == "plugin-path":
        print(Path(__file__).resolve().parents[1] / "plugin"); return 0
    if a.cmd == "usage":
        print(json.dumps(summarize(ROOT, a.days), ensure_ascii=False, indent=2)); return 0
    if a.cmd == "status":
        runs = ROOT / "runs"
        ids = [a.run_id] if a.run_id else sorted(p.name for p in runs.iterdir() if (p / "state.json").exists()) if runs.is_dir() else []
        if a.run_id and not (runs / a.run_id / "state.json").exists():
            print(f"BLOCKED: 실행 기록이 없다: {runs / a.run_id}\n  → `bw status` 로 목록을 보거나 BW_HOME(지금 {ROOT})을 확인하라", file=sys.stderr); return 2
        for rid in ids:
            s = json.loads((runs / rid / "state.json").read_text()); print(f"{rid}: {s['step']} {s['status']} · in {s.get('input_tokens', 0):,}")
        return 0
    def parse_pins(items: list[str] | None) -> dict[str, dict[str, list[float]]]:
        """--pin 본=x,y,z[/x,y,z] → {"본": {"head": [...], "tail": [...]}}"""
        out: dict[str, dict[str, list[float]]] = {}
        for it in items or []:
            if "=" not in it:
                raise SystemExit(f"--pin 형식 오류: {it} (예: spine.004=0,0,1.42)")
            name, rest = it.split("=", 1); parts = rest.split("/")
            name = name.strip()
            if not name or len(parts) > 2:
                raise SystemExit(f"--pin 형식 오류: {it} (예: spine.004=0,0,1.42)")
            try:
                v = {"head": [float(x) for x in parts[0].split(",")]}
                if len(parts) > 1: v["tail"] = [float(x) for x in parts[1].split(",")]
            except ValueError:
                raise SystemExit(f"--pin 좌표 오류: {it} (숫자 3개를 쉼표로, 공백 없이. 예: spine.004=0,0,1.42)")
            if (len(v["head"]) != 3 or len(v.get("tail", [0, 0, 0])) != 3
                    or not all(math.isfinite(x) for coords in v.values() for x in coords)):
                raise SystemExit(f"--pin 좌표는 x,y,z 세 개다: {it} (예: hand.L=0.6,0,1.3 또는 머리/꼬리 hand.L=0.6,0,1.3/0.7,0,1.3)")
            out[name] = v
        return out

    try:
        if a.cmd == "rig":
            out = pipeline.rig(ROOT, a.mesh, a.preset, run_id=a.run_id, lang=a.lang, quiet=a.quiet, budget=a.budget, no_judge=a.no_judge, facing=a.facing, pins=parse_pins(a.pin), targets_file=a.targets, force=a.force, rest_pose=a.rest_pose, weights=a.weights, from_skeleton=a.from_skeleton, from_shape=a.from_shape)
        elif a.cmd == "bench":
            files = []
            for m in a.meshes:
                p_ = Path(m)
                files += sorted(str(f) for f in p_.iterdir() if f.suffix.lower() in (".glb", ".gltf", ".fbx")) if p_.is_dir() else [m]
            out = bench.run(ROOT, files, run_id=a.run_id, quiet=a.quiet, facing=a.facing, preset=a.preset, skin=a.skin, weights=a.weights, rest_pose=a.rest_pose, gt_mesh=a.gt_mesh)
        elif a.cmd == "export":
            out = pipeline.export_rig(ROOT, a.run_id, out=a.out, quiet=a.quiet)
        elif a.cmd == "demo":
            out = pipeline.demo(ROOT, a.run_id, quiet=a.quiet, size=a.size, frames=a.frames)
        else:
            out = pipeline.motion(ROOT, text=a.text, bvh=a.bvh, run_id=a.run_id, quiet=a.quiet, rig_run=a.rig, export=a.export, roll=not a.no_roll, preset=a.preset, bvh_up=a.bvh_up, legs=a.legs, bone_map=a.bone_map)
    except pipeline.Blocked as e:
        print("BLOCKED:", e, file=sys.stderr); return 2
    except Exception as e:  # Blender 오류 등
        print("BLOCKED:", e, file=sys.stderr); return 2
    print("보고서:", out); return 0


if __name__ == "__main__":
    sys.exit(main())
