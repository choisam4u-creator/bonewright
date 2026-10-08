"""bw: bonewright 명령줄. rig · motion · demo · bench · doctor · status · usage · plugin-path"""
import argparse
import contextlib
import io
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

from . import __version__, bench, pipeline
from .blender import find_blender, has_bpy_module
from .config import find_root, load, unknown_keys_line
from .i18n import T
from .ledger import summarize

ROOT = find_root()


def plugin_dir() -> Path:
    """Codex 플러그인 폴더. 저장소에서 돌리면 plugin/, pip 으로 설치했으면 패키지에 실린 bonewright/_plugin/."""
    here = Path(__file__).resolve().parent
    for p in (here.parent / "plugin", here / "_plugin"):
        if (p / ".codex-plugin" / "plugin.json").is_file():
            return p
    raise FileNotFoundError(T(f"Codex 플러그인 폴더를 찾지 못했다({here.parent / 'plugin'}, {here / '_plugin'})\n  → 저장소에서 `pip install .` 으로 다시 설치하라",
                              f"Codex plugin folder not found ({here.parent / 'plugin'}, {here / '_plugin'})\n  → reinstall from the repository with `pip install .`"))


def doctor() -> int:
    """준비 상태. [필수]는 Blender 앱 또는 bpy 모듈 하나뿐이다 — mock·--from-skeleton·--from-shape·--targets 는 codex 없이 된다."""
    req, opt = T("[필수]", "[required]"), T("[선택]", "[optional]")
    cfg = load(ROOT)
    bl = find_blender(cfg["blender"])
    print(req, "Blender:", bl[0] if bl else T("없음 (Blender.app 설치 또는 BW_BLENDER)", "not found (install Blender or set BW_BLENDER)"))
    if bl:
        v = subprocess.run(bl + ["--version"], capture_output=True, text=True).stdout.splitlines()
        print("  ", v[0] if v else "?")
    ok = bool(bl)
    if not bl:
        ok = has_bpy_module()
        print(req, T("bpy 모듈:", "bpy module:"), T("있음", "found") if ok else T("없음 (pip install bpy==5.2.2, Python 3.13)", "not found (pip install bpy==5.2.2, Python 3.13)"))
    codex = shutil.which("codex")
    print(opt, "codex CLI:", codex or T("없음 — 모델 판정(기본 `bw rig`)에만 필요. 토큰 0 경로(--from-skeleton·--from-shape·--targets·BW_BACKEND=mock)는 없이 된다 → https://developers.openai.com/codex",
                                       "not found — needed only for the model judge (default `bw rig`). The 0-token routes (--from-skeleton, --from-shape, --targets, BW_BACKEND=mock) work without it → https://developers.openai.com/codex"))
    if codex:
        print("  ", subprocess.run(["codex", "--version"], capture_output=True, text=True).stdout.strip())
        login = subprocess.run(["codex", "login", "status"], capture_output=True, text=True)
        print("  ", T("로그인:", "login:"), (login.stdout or login.stderr).strip()[:60])
    gen, text_model = pipeline.kimodo_paths((ROOT / cfg["kimodo"]["root"]).resolve(), cfg["kimodo"])
    print(opt, "kimodo.cpp:", (T("빌드됨", "built") if text_model else T("빌드됨, 텍스트 인코더 없음 — docs/GUIDE.md 의 \"Text → motion: building kimodo.cpp\"", "built, no text encoder — see \"Text → motion: building kimodo.cpp\" in docs/GUIDE.md")) if gen else T("없음 — 텍스트→동작(`bw motion --text`)에만 필요, 빌드는 docs/GUIDE.md 의 \"Text → motion: building kimodo.cpp\"", "not built — needed only for text→motion (`bw motion --text`); to build, see \"Text → motion: building kimodo.cpp\" in docs/GUIDE.md"))
    print(T("작업 폴더(ROOT):", "work folder (ROOT):"), ROOT, T("(BW_HOME 으로 바꿀 수 있음)", "(change with BW_HOME)"))
    if (warn := unknown_keys_line(ROOT)):
        print(warn)
    print(T("준비됨" if ok else "준비 안 됨: Blender 앱이나 bpy 모듈 중 하나를 설치하라", "ready" if ok else "not ready: install Blender or the bpy module (either one)"))
    return 0 if ok else 1


def scrub(text: str) -> str:
    """이슈에 붙일 글에서 개인 경로를 지운다: 홈 폴더 → `~`, 남은 /Users/<이름>·/home/<이름>·C:\\Users\\<이름> → `~`."""
    home = str(Path.home())
    if len(home) > 1:
        text = text.replace(home, "~")
    return re.sub(r"(/Users/|/home/|[A-Za-z]:\\Users\\)[^/\\\s'\"]+", "~", text)


def latest_run(runs: Path) -> str | None:
    """state.json 이 있는 실행 중 가장 최근 것의 id."""
    cand = [p for p in runs.iterdir() if (p / "state.json").is_file()] if runs.is_dir() else []
    return max(cand, key=lambda p: (p / "state.json").stat().st_mtime).name if cand else None


def issue_report(run_id: str | None, tail: int = 40) -> int:
    """`bw doctor --for-issue [RUN_ID]`: 버그 신고에 붙일 한 덩어리(마크다운). 버전·OS·Python·`bw doctor` 결과와
    실행 하나의 state.json·마지막 로그 꼬리를 모으고 개인 경로를 `~` 로 바꾼다. 이슈 템플릿 3종이 손으로 모으라던 값들."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = doctor()
    lines = ["<details><summary>bw doctor --for-issue</summary>", "", "```",
             f"bonewright {__version__}", f"Python {platform.python_version()} ({sys.executable})",
             f"OS {platform.platform()} {platform.machine()}"]
    lines += [f"{k}={v}" for k, v in sorted(os.environ.items()) if k.startswith("BW_")]
    lines += ["", buf.getvalue().rstrip(), "```"]
    runs = ROOT / "runs"
    rid = run_id or latest_run(runs)
    if run_id and not (runs / run_id).is_dir():
        print("BLOCKED:", scrub(T(f"실행 기록이 없다: {runs / run_id}\n  → `bw status` 로 목록을 보거나 run-id 없이 `bw doctor --for-issue` 를 돌려라",
                                 f"no such run: {runs / run_id}\n  → list runs with `bw status`, or run `bw doctor --for-issue` without a run-id")), file=sys.stderr)
        return 2
    if rid:
        d = runs / rid
        lines += ["", f"run `{rid}`", "", "```json",
                  (d / "state.json").read_text(encoding="utf-8").strip() if (d / "state.json").is_file() else T("(state.json 없음)", "(no state.json)"), "```"]
        logs = sorted((d / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime) if (d / "logs").is_dir() else []
        if logs:
            last = logs[-1].read_text(encoding="utf-8", errors="replace").splitlines()[-tail:]
            lines += ["", T(f"마지막 로그 `logs/{logs[-1].name}` 끝 {len(last)}줄", f"last log `logs/{logs[-1].name}`, final {len(last)} lines"),
                      "", "```", *last, "```"]
    else:
        lines += ["", T("(runs/ 에 실행 기록 없음)", "(no runs under runs/)")]
    lines += ["", "</details>"]
    print(scrub("\n".join(lines)))
    print(T("\n↑ 위 덩어리를 이슈에 그대로 붙여 넣어라. 붙이기 전에 남은 개인 정보가 없는지 한 번 보라",
            "\n↑ paste the block above into the issue as is. Check it once for anything private before posting"), file=sys.stderr)
    return code


def recent_logs(since: float, run_id: str | None = None) -> Path | None:
    """실패한 실행의 로그 폴더. run-id 를 안 줬으면 이번 명령이 시작된 뒤 바뀐 runs/ 아래 폴더 중 가장 최근 것."""
    runs = ROOT / "runs"
    if run_id:
        cand = [runs / run_id]
    else:
        cand = sorted((p for p in runs.iterdir() if p.is_dir() and p.stat().st_mtime >= since),
                      key=lambda p: p.stat().st_mtime, reverse=True) if runs.is_dir() else []
    for d in cand:
        if (d / "logs").is_dir():
            return d / "logs"
    return None


def report_unexpected(e: Exception, since: float, run_id: str | None) -> None:
    """예상 못 한 오류: 한 줄 메시지만으로는 원인을 못 찾으니 로그 위치·트레이스백 얻는 법·이슈 템플릿을 같이 알린다."""
    name = type(e).__name__
    msg = str(e) if name == "BlenderError" else f"{name}: {e}"
    print("BLOCKED:", msg, file=sys.stderr)
    if os.environ.get("BW_DEBUG"):
        traceback.print_exc(file=sys.stderr); return
    logs = recent_logs(since, run_id)
    if logs:
        print(T("  → 로그:", "  → logs:"), logs, file=sys.stderr)
    print(T("  → 원인 추적: 같은 명령 앞에 BW_DEBUG=1 을 붙이면 트레이스백을 보여 준다",
            "  → to see the traceback, run the same command with BW_DEBUG=1 in front"), file=sys.stderr)
    print(T("  → 고쳐지지 않으면 이슈의 'A rig came out wrong' 또는 'Install or `bw doctor` problem' 템플릿에"
            " 이 출력과 `bw doctor --for-issue` 결과를 붙여 달라",
            "  → if it persists, open an issue with the 'A rig came out wrong' or 'Install or `bw doctor` problem'"
            " template and paste this output and what `bw doctor --for-issue` prints"), file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bw", description=f"bonewright {__version__}: Python drives, Codex judges, gates verify.")
    p.add_argument("--version", action="version", version=f"bonewright {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rig", help=T("메시를 Rigify 로 리깅하고 검증한다", "rig a mesh with Rigify and check it"))
    r.add_argument("mesh"); r.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid")
    r.add_argument("--run-id"); r.add_argument("--lang", choices=["ko", "en"], help=T("모델 프롬프트 언어(생략하면 runs/config.json 의 lang, 그것도 없으면 BW_LANG·로캘)", "language of the model prompts (default: lang in runs/config.json, else BW_LANG / locale like the screen text)")); r.add_argument("--budget", type=int)
    r.add_argument("--no-judge", action="store_true", help=T("시각 판정(모델 호출) 생략", "skip the visual judge (model call)")); r.add_argument("--facing", choices=["auto", "neg-y", "pos-y"], default="auto", help=T("캐릭터가 보는 방향. auto=발 방향으로 판단해 -Y 로 맞춤", "which way the character faces. auto=decide from the feet and turn it to -Y")); r.add_argument("--quiet", action="store_true")
    r.add_argument("--force", action="store_true", help=T("거절 게이트를 무시하고 진행(비인간·크기 이상 메시도 리깅 시도)", "ignore the rejection gate and rig anyway (non-human or oddly sized meshes too)"))
    r.add_argument("--from-shape", action="store_true", help=T("메시 속 중심선에서 뼈대를 직접 만들어 리깅한다(토큰 0). 뼈대가 없고 사람·개과 비율도 아닌 메시(곤충·괴물)에 쓴다 — 해부학적 관절이 아니라 모양을 따라가는 조작 장치다", "build the skeleton from the mesh's own centrelines (0 tokens). For meshes with no skeleton and neither human nor dog proportions (insects, monsters) — controls follow the shape, not anatomical joints"))
    r.add_argument("--from-skeleton", action="store_true", help=T("파일에 든 원본 뼈대의 관절을 그대로 써서 Rigify 리그를 만든다(토큰 0). 실루엣으로 관절을 못 찾는 로봇·양식화 캐릭터에 쓴다", "build the Rigify rig on the joints of the skeleton already in the file (0 tokens). For robots and stylised characters whose silhouette hides the joints"))
    r.add_argument("--rest-pose", choices=["keep", "t"], default=None, help=T("쉬는 자세: keep=메시 자세 그대로(기본), t=팔을 수평으로 굳혀 T 포즈로", "rest pose: keep=the mesh's own pose (default), t=bake arms horizontal into a T-pose"))
    r.add_argument("--weights", choices=["auto", "proxy"], default=None, help=T("스키닝: auto=Bone Heat(비면 복셀 대리), proxy=항상 복셀 대리", "skinning: auto=Bone Heat (voxel proxy if it leaves gaps), proxy=always the voxel proxy"))
    r.add_argument("--pin", action="append", metavar=T("본=x,y,z[/x,y,z]", "BONE=x,y,z[/x,y,z]"),
                   help=T("관절을 직접 고정한다. 예: --pin spine.004=0,0,1.42 (머리만), --pin hand.L=0.6,0,1.3/0.7,0,1.3 (머리/꼬리). 여러 번 쓸 수 있다", "pin a joint by hand. e.g. --pin spine.004=0,0,1.42 (head only), --pin hand.L=0.6,0,1.3/0.7,0,1.3 (head/tail). Repeatable"))
    r.add_argument("--targets", metavar="targets.json", help=T("이전 실행의 targets.json 을 그대로 쓴다(모델 호출 0회, 토큰 0)", "reuse a previous run's targets.json (0 model calls, 0 tokens)"))
    m = sub.add_parser("motion", help=T("텍스트(kimodo.cpp) 또는 BVH 에서 동작을 만들어 Blender 로 가져온다", "make motion from text (kimodo.cpp) or a BVH and bring it into Blender"))
    m.add_argument("--text"); m.add_argument("--bvh"); m.add_argument("--run-id"); m.add_argument("--quiet", action="store_true")
    m.add_argument("--rig", help=T("리깅 결과 run-id: 그 리그에 동작을 옮긴다(리타겟, 토큰 0)", "run-id of a rig: retarget the motion onto it (0 tokens)"))
    m.add_argument("--preset", choices=["humanoid", "quadruped"], default=None, help=T("리그의 프리셋. 생략하면 리그 실행 기록(rig_stats.json)에서 읽는다", "the rig's preset. Read from the rig run (rig_stats.json) when omitted"))
    m.add_argument("--bvh-up", choices=["auto", "y", "z"], default="auto", help=T("BVH 의 위 축. auto=머리와 발 위치로 판단(기본). 표준은 y, Blender 가 내보낸 BVH 는 z", "BVH up axis. auto=decide from head and feet (default). Standard BVH is y, Blender-exported BVH is z"))
    m.add_argument("--legs", choices=["auto", "fk", "ik"], default="auto", help=T("다리 전달: auto(소스에 발끝 관절이 있는 다리만 IK) | fk(회전만) | ik(발 IK 로 BVH 발끝을 좇음, 비율 차이 흡수)", "legs: auto (IK only for legs whose source has toe joints) | fk (rotation only) | ik (foot IK follows the BVH feet, absorbs proportion differences)"))
    m.add_argument("--no-roll", action="store_true", help=T("리타겟에서 비틀림(롤)을 옮기지 않는다(방향만, A/B 비교용)", "do not transfer twist (roll), direction only (for A/B comparison)"))
    m.add_argument("--map", dest="bone_map", metavar="bones.json",
                   help=T('BVH 본 → 리그 본 매핑 파일 {"LeftArm": "upper_arm.L"}. 이름이 없는 리그(모양 리그의 Limb3_2 등)는 자동 매핑이 못 붙으니 직접 적는다',
                          'BVH bone → rig bone map {"LeftArm": "upper_arm.L"}. Rigs without standard names (a shape rig\'s Limb3_2 etc.) need one written by hand'))
    m.add_argument("--export", nargs="?", const="auto", help=T("리타겟 결과를 GLB 로 내보낸다(변형 본만·애니 구움). 경로 생략 시 runs/<id>/animated.glb", "export the retargeted result as GLB (deform bones only, animation baked). Default path runs/<id>/animated.glb"))
    ex = sub.add_parser("export", help=T("리그 결과를 변형 본만 든 GLB 로 내보내기(게임 엔진용), 토큰 0", "export a rig as a deform-only GLB for game engines (0 tokens)"))
    ex.add_argument("run_id"); ex.add_argument("--out", help=T("출력 경로(기본 runs/<id>/rigged.glb)", "output path (default runs/<id>/rigged.glb)")); ex.add_argument("--quiet", action="store_true")
    d = sub.add_parser("demo", help=T("리그 결과를 IK 로 움직인 데모 영상(mp4/gif) 만들기, 토큰 0", "render a demo video (mp4/gif) of the rig moving through its IK controls (0 tokens)"))
    d.add_argument("run_id"); d.add_argument("--size", type=int, default=640); d.add_argument("--frames", type=int, default=96); d.add_argument("--quiet", action="store_true")
    bm = sub.add_parser("bench", help=T("원본 뼈대가 든 캐릭터로 관절 오차를 cm 단위로 잰다(토큰 0)", "measure joint error in cm against characters that carry their own skeleton (0 tokens)"))
    bm.add_argument("meshes", nargs="+", help=T("GLB/FBX 파일 또는 폴더", "GLB/FBX files or folders"))
    bm.add_argument("--run-id"); bm.add_argument("--facing", choices=["auto", "neg-y", "pos-y"], default="auto")
    bm.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid")
    bm.add_argument("--rest-pose", choices=["keep", "t"], default=None, help=T("리깅할 때 쉬는 자세를 T 로 굳힌다(포즈 정규화 측정용)", "bake a T rest pose while rigging (to measure pose normalisation)"))
    bm.add_argument("--gt-mesh", help=T("정답 뼈대를 이 파일에서 가져온다(포즈 변형본을 원본 T 포즈와 맞댈 때)", "take the reference skeleton from this file (to compare a posed variant with its original T-pose)"))
    bm.add_argument("--quiet", action="store_true")
    bm.add_argument("--skin", action="store_true", help=T("스키닝 일치도도 잰다(원본 가중치와 대조, 토큰 0)", "also measure skinning agreement with the original weights (0 tokens)"))
    bm.add_argument("--weights", choices=["auto", "proxy"], default=None, help=T("스키닝 방법 강제(A/B 비교용)", "force a skinning method (for A/B comparison)"))
    st = sub.add_parser("status", help=T("실행 기록 목록 또는 한 실행의 단계·상태", "list runs, or one run's step and status")); st.add_argument("run_id", nargs="?")
    u = sub.add_parser("usage", help=T("모델 호출 사용량 장부 요약", "summarise the model-usage ledger")); u.add_argument("--days", type=int, default=7)
    dr = sub.add_parser("doctor", help=T("Blender·bpy·codex·kimodo.cpp 가 준비됐는지 확인", "check that Blender or bpy, codex and kimodo.cpp are reachable"))
    dr.add_argument("--for-issue", nargs="?", const="", metavar="RUN_ID",
                    help=T("버그 신고에 붙일 덩어리를 찍는다: 버전·OS·이 점검 결과·실행 하나(생략하면 가장 최근)의 state.json·마지막 로그 꼬리. 개인 경로는 ~ 로 바꾼다",
                           "print a block to paste into a bug report: versions, OS, this check, and one run's state.json and log tail (the latest run if omitted). Home paths become ~"))
    sub.add_parser("plugin-path", help=T("Codex 플러그인 폴더 경로 출력", "print the Codex plugin folder"))
    return p


def main() -> int:
    a = build_parser().parse_args()
    started = time.time() - 1  # 파일 시각 해상도 여유
    try:
        if a.cmd == "doctor":
            return doctor() if a.for_issue is None else issue_report(a.for_issue or None)
        if a.cmd == "plugin-path":
            try:
                print(plugin_dir()); return 0
            except FileNotFoundError as e:
                print("BLOCKED:", e, file=sys.stderr); return 2
        if a.cmd == "usage":
            print(json.dumps(summarize(ROOT, a.days), ensure_ascii=False, indent=2)); return 0
        if a.cmd == "status":
            runs = ROOT / "runs"
            ids = [a.run_id] if a.run_id else sorted(p.name for p in runs.iterdir() if (p / "state.json").exists()) if runs.is_dir() else []
            if a.run_id and not (runs / a.run_id / "state.json").exists():
                print("BLOCKED:", T(f"실행 기록이 없다: {runs / a.run_id}\n  → `bw status` 로 목록을 보거나 BW_HOME(지금 {ROOT})을 확인하라",
                                   f"no such run: {runs / a.run_id}\n  → list runs with `bw status`, or check BW_HOME (now {ROOT})"), file=sys.stderr); return 2
            for rid in ids:
                s = json.loads((runs / rid / "state.json").read_text()); print(f"{rid}: {s['step']} {s['status']} · in {s.get('input_tokens', 0):,}")
            return 0
        def parse_pins(items: list[str] | None) -> dict[str, dict[str, list[float]]]:
            """--pin 본=x,y,z[/x,y,z] → {"본": {"head": [...], "tail": [...]}}"""
            out: dict[str, dict[str, list[float]]] = {}
            for it in items or []:
                if "=" not in it:
                    raise SystemExit(T(f"--pin 형식 오류: {it} (예: spine.004=0,0,1.42)", f"--pin format error: {it} (e.g. spine.004=0,0,1.42)"))
                name, rest = it.split("=", 1); parts = rest.split("/")
                name = name.strip()
                if not name or len(parts) > 2:
                    raise SystemExit(T(f"--pin 형식 오류: {it} (예: spine.004=0,0,1.42)", f"--pin format error: {it} (e.g. spine.004=0,0,1.42)"))
                try:
                    v = {"head": [float(x) for x in parts[0].split(",")]}
                    if len(parts) > 1: v["tail"] = [float(x) for x in parts[1].split(",")]
                except ValueError:
                    raise SystemExit(T(f"--pin 좌표 오류: {it} (숫자 3개를 쉼표로, 공백 없이. 예: spine.004=0,0,1.42)",
                                       f"--pin coordinate error: {it} (three numbers, comma-separated, no spaces. e.g. spine.004=0,0,1.42)"))
                if (len(v["head"]) != 3 or len(v.get("tail", [0, 0, 0])) != 3
                        or not all(math.isfinite(x) for coords in v.values() for x in coords)):
                    raise SystemExit(T(f"--pin 좌표는 x,y,z 세 개다: {it} (예: hand.L=0.6,0,1.3 또는 머리/꼬리 hand.L=0.6,0,1.3/0.7,0,1.3)",
                                     f"--pin takes x,y,z: {it} (e.g. hand.L=0.6,0,1.3, or head/tail hand.L=0.6,0,1.3/0.7,0,1.3)"))
                out[name] = v
            return out

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
        report_unexpected(e, started, getattr(a, "run_id", None)); return 2
    print(T("보고서:", "report:"), out); return 0


if __name__ == "__main__":
    sys.exit(main())
