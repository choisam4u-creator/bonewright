"""bw: bonewright 명령줄. rig · motion · demo · doctor · status · usage · plugin-path"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, pipeline
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
        print("bpy 모듈:", "있음" if has_bpy_module() else "없음 (pip install bpy==5.2.1, Python 3.13)"); ok &= has_bpy_module()
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
    r.add_argument("--pin", action="append", metavar="본=x,y,z[/x,y,z]",
                   help="관절을 직접 고정한다. 예: --pin spine.004=0,0,1.42 (머리만), --pin hand.L=0.6,0,1.3/0.7,0,1.3 (머리/꼬리). 여러 번 쓸 수 있다")
    r.add_argument("--targets", metavar="targets.json", help="이전 실행의 targets.json 을 그대로 쓴다(모델 호출 0회, 토큰 0)")
    m = sub.add_parser("motion", help="텍스트(kimodo.cpp) 또는 BVH 에서 동작을 만들어 Blender 로 가져온다")
    m.add_argument("--text"); m.add_argument("--bvh"); m.add_argument("--run-id"); m.add_argument("--quiet", action="store_true")
    d = sub.add_parser("demo", help="리그 결과를 IK 로 움직인 데모 영상(mp4/gif) 만들기, 토큰 0")
    d.add_argument("run_id"); d.add_argument("--size", type=int, default=640); d.add_argument("--frames", type=int, default=96); d.add_argument("--quiet", action="store_true")
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
        for rid in ids:
            s = json.loads((runs / rid / "state.json").read_text()); print(f"{rid}: {s['step']} {s['status']} · in {s.get('input_tokens', 0):,}")
        return 0
    def parse_pins(items):
        """--pin 본=x,y,z[/x,y,z] → {"본": {"head": [...], "tail": [...]}}"""
        out = {}
        for it in items or []:
            if "=" not in it:
                raise SystemExit(f"--pin 형식 오류: {it} (예: spine.004=0,0,1.42)")
            name, rest = it.split("=", 1); parts = rest.split("/")
            try:
                v = {"head": [float(x) for x in parts[0].split(",")]}
                if len(parts) > 1: v["tail"] = [float(x) for x in parts[1].split(",")]
            except ValueError:
                raise SystemExit(f"--pin 좌표 오류: {it} (숫자 3개를 쉼표로)")
            if len(v["head"]) != 3 or len(v.get("tail", [0, 0, 0])) != 3:
                raise SystemExit(f"--pin 좌표는 x,y,z 세 개다: {it}")
            out[name.strip()] = v
        return out

    try:
        if a.cmd == "rig":
            out = pipeline.rig(ROOT, a.mesh, a.preset, run_id=a.run_id, lang=a.lang, quiet=a.quiet, budget=a.budget, no_judge=a.no_judge, facing=a.facing, pins=parse_pins(a.pin), targets_file=a.targets)
        elif a.cmd == "demo":
            out = pipeline.demo(ROOT, a.run_id, quiet=a.quiet, size=a.size, frames=a.frames)
        else:
            out = pipeline.motion(ROOT, text=a.text, bvh=a.bvh, run_id=a.run_id, quiet=a.quiet)
    except pipeline.Blocked as e:
        print("BLOCKED:", e, file=sys.stderr); return 2
    except Exception as e:  # Blender 오류 등
        print("BLOCKED:", e, file=sys.stderr); return 2
    print("보고서:", out); return 0


if __name__ == "__main__":
    sys.exit(main())
