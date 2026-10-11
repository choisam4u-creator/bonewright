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

from . import __version__, bench, blender, pipeline
from .blender import find_blender, has_bpy_module
from .config import find_root, load, unknown_keys_line
from .i18n import T
from .ledger import path as ledger_path, summarize

ROOT = find_root()


def plugin_dir() -> Path:
    """Codex 플러그인 폴더. 저장소에서 돌리면 plugin/, pip 으로 설치했으면 패키지에 실린 bonewright/_plugin/."""
    here = Path(__file__).resolve().parent
    for p in (here.parent / "plugin", here / "_plugin"):
        if (p / ".codex-plugin" / "plugin.json").is_file():
            return p
    raise FileNotFoundError(T(f"Codex 플러그인 폴더를 찾지 못했다({here.parent / 'plugin'}, {here / '_plugin'})\n  → 저장소에서 `pip install .` 으로 다시 설치하라",
                              f"Codex plugin folder not found ({here.parent / 'plugin'}, {here / '_plugin'})\n  → reinstall from the repository with `pip install .`"))


def doctor(warn_unknown: bool = True) -> int:
    """준비 상태. 필수는 Blender 앱 또는 bpy 모듈 둘 중 하나뿐이다 — mock·--from-skeleton·--from-shape·--targets 는 codex 없이 된다.
    warn_unknown=False: 모르는 설정 키 경고를 뺀다(`--for-issue` 는 설정 절에 같은 내용을 한 번 싣는다)."""
    # Blender 앱과 bpy 모듈은 둘 중 하나만 있으면 된다 — 줄마다 그렇게 적고, 하나가 있으면 다른 쪽은 [필요 없음].
    # (10/10 5회차 실측: 둘 다 [required] 로 찍혀 둘 다 깔아야 하는 줄 알았다. 마지막 줄에서야 "either one")
    either, opt, unneeded = T("[필수: 둘 중 하나]", "[required: one of]"), T("[선택]", "[optional]"), T("[필요 없음]", "[not needed]")
    cfg = load(ROOT)
    bl = find_blender(cfg["blender"])
    bpy_ok = False if bl else has_bpy_module()
    ok = bool(bl) or bpy_ok
    print(either if bl or not ok else unneeded, "Blender:", bl[0] if bl else
          (T("없음 — bpy 모듈을 대신 쓴다", "not found — the bpy module is used instead") if bpy_ok else
           T(f"없음 (Blender 5.2 LTS 설치 {blender.DOWNLOAD} 또는 BW_BLENDER 에 경로)", f"not found (install Blender 5.2 LTS from {blender.DOWNLOAD}, or set BW_BLENDER to its path)")))
    if bl:
        v = subprocess.run(bl + ["--version"], capture_output=True, text=True).stdout.splitlines()
        print("  ", v[0] if v else "?")
        print(unneeded, T("bpy 모듈: 확인 안 함 — Blender 앱을 쓴다", "bpy module: not checked — the Blender app is used"))
    else:
        print(either, T("bpy 모듈:", "bpy module:"), T("있음", "found") if bpy_ok else T("없음 (pip install bpy==5.2.2, Python 3.13)", "not found (pip install bpy==5.2.2, Python 3.13)"))
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
    if warn_unknown and (warn := unknown_keys_line(ROOT)):
        print(warn)
    print(T("준비됨" if ok else "준비 안 됨: Blender 앱이나 bpy 모듈 중 하나를 설치하라", "ready" if ok else "not ready: install Blender or the bpy module (either one)"))
    return 0 if ok else 1


def scrub(text: str) -> str:
    """이슈에 붙일 글에서 개인 경로를 지운다: 홈 폴더 → `~`, 남은 /Users/<이름>·/home/<이름>·C:\\Users\\<이름> → `~`."""
    home = str(Path.home())
    if len(home) > 1:   # JSON 안(runs/config.json)의 Windows 경로는 역슬래시가 둘씩이다: C:\\Users\\<이름>
        text = text.replace(home, "~").replace(home.replace("\\", "\\\\"), "~")
    return re.sub(r"(/Users/|/home/|[A-Za-z]:\\{1,2}Users\\{1,2})[^/\\\s'\"]+", "~", text)


def latest_run(runs: Path) -> str | None:
    """state.json 이 있는 실행 중 가장 최근 것의 id."""
    cand = [p for p in runs.iterdir() if (p / "state.json").is_file()] if runs.is_dir() else []
    return max(cand, key=lambda p: (p / "state.json").stat().st_mtime).name if cand else None


def config_section(p: Path, limit: int = 4000) -> list[str]:
    """`--for-issue` 에 실을 설정 파일 절: 내용 그대로(깨진 JSON 도 — 그게 원인일 수 있다)와 모르는 키 한 줄.
    설정이 원인인 리깅 이슈는 설정 없이 재현이 안 된다. 경로 치환은 issue_report 의 scrub 이 한다."""
    if not p.is_file():
        return ["", T("(runs/config.json 없음 — 기본 설정)", "(no runs/config.json — default settings)")]
    text = p.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) > limit:
        text = text[:limit] + "\n" + T(f"… ({len(text) - limit}자 줄임)", f"… ({len(text) - limit} characters cut)")
    out = ["", "`runs/config.json`", "", "```json", text, "```"]
    from .config import unknown_keys
    if (bad := unknown_keys(ROOT)):
        out.append(T(f"모르는 키(무시됨): {', '.join(bad)}", f"unknown keys (ignored): {', '.join(bad)}"))
    return out


def issue_report(run_id: str | None, tail: int = 40) -> int:
    """`bw doctor --for-issue [RUN_ID]`: 버그 신고에 붙일 한 덩어리(마크다운). 버전·OS·Python·`bw doctor` 결과와
    실행 하나의 state.json·마지막 로그 꼬리를 모으고 개인 경로를 `~` 로 바꾼다. 이슈 템플릿 3종이 손으로 모으라던 값들."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = doctor(warn_unknown=False)   # 모르는 키는 아래 설정 절에 한 번만
    lines = ["<details><summary>bw doctor --for-issue</summary>", "", "```",
             f"bonewright {__version__}", f"Python {platform.python_version()} ({sys.executable})",
             f"OS {platform.platform()} {platform.machine()}"]
    lines += [f"{k}={v}" for k, v in sorted(os.environ.items()) if k.startswith("BW_")]
    lines += ["", buf.getvalue().rstrip(), "```"]
    lines += config_section(ROOT / "runs" / "config.json")
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
        for extra in ("export_state.json", "demo_state.json"):   # 8회차부터 export·demo 는 리그 state 를 덮지 않고 따로 적는다
            if (d / extra).is_file():
                lines += ["", f"`{extra}`", "", "```json", (d / extra).read_text(encoding="utf-8", errors="replace").strip(), "```"]
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


FIRST_RIG = "bw rig tests/assets/quaternius_adventurer.glb --from-skeleton --no-judge"   # README "First run" 첫 줄 — 저장소 폴더에서 그대로 돈다


def _hint_on_missing(p: argparse.ArgumentParser, arg: str, hint: str) -> None:
    """argparse 의 '…required: <arg>' 한 줄 끝에 다음 할 일을 붙인다(종료 2·사용법 줄은 그대로)."""
    orig = p.error
    def error(message: str):
        orig(message + "\n" + hint if message.rstrip().endswith(": " + arg) else message)
    p.error = error


def _hint_on_bad_command(p: argparse.ArgumentParser, sub) -> None:
    """틀린 하위 명령(`bw resume`·`bw rigs`)에 가장 가까운 명령과 `bw --help` 를 붙인다(종료 2 그대로)."""
    import difflib
    import re
    orig = p.error
    def error(message: str):
        m = re.search(r"argument cmd: invalid choice: '([^']*)'", message)
        if m:
            near = difflib.get_close_matches(m.group(1), list(sub.choices), n=1, cutoff=0.5)
            if m.group(1) == "resume":   # 옛 안내에 있던 명령. 멈춘 리깅은 같은 명령을 다시 돌리거나 targets 로 토큰 0 재실행
                message += "\n" + T("→ `bw resume` 은 없다. 같은 `bw rig` 명령을 다시 돌리거나, 모델 호출 없이 "
                                     "`bw rig <메시> --targets runs/<id>/targets.json`(멈춘 곳은 `bw status <id>`)",
                                     "→ there is no `bw resume`. Run the same `bw rig` command again, or without model calls: "
                                     "`bw rig <mesh> --targets runs/<id>/targets.json` (where it stopped: `bw status <id>`)")
                return orig(message)
            message += "\n" + (T(f"→ 혹시 `bw {near[0]}`? 명령 목록: `bw --help`", f"→ did you mean `bw {near[0]}`? All commands: `bw --help`") if near
                               else T("→ 명령 목록: `bw --help`", "→ all commands: `bw --help`"))
        orig(message)
    p.error = error


def _hint_on_unquoted(p: argparse.ArgumentParser) -> None:
    """공백 든 경로를 따옴표 없이 줬을 때(`bw rig my char.glb`): argparse 는 "unrecognized arguments: char.glb" 만 말한다.
    이어 붙이면 있는 파일이 되는 인자들을 찾아 따옴표 친 명령을 그대로 준다(10/11 10회차 실측, macOS 파일 이름에 흔하다)."""
    orig = p.error
    def error(message: str):
        if "unrecognized arguments:" in message:
            args = sys.argv[1:]
            for i in range(len(args)):
                if args[i].startswith("-") or Path(args[i]).expanduser().exists():
                    continue
                for j in range(len(args), i + 1, -1):
                    joined = " ".join(args[i:j])
                    if Path(joined).expanduser().is_file():
                        cmd = " ".join(["bw", *args[:i], f'"{joined}"', *args[j:]])
                        message += "\n" + T(f"→ 공백 든 경로는 따옴표로 감싼다: {cmd}", f"→ quote a path that has spaces: {cmd}")
                        return orig(message)
        orig(message)
    p.error = error


def _hint_on_conflict(p: argparse.ArgumentParser, hint: str) -> None:
    """argparse 의 '…not allowed with argument …' 끝에 무엇을 고를지 한 줄(종료 2 그대로)."""
    orig = p.error
    def error(message: str):
        orig(message + "\n" + hint if "not allowed with argument" in message else message)
    p.error = error


FACING = ["auto", "neg-y", "pos-y"]


def facing_help() -> str:
    """--facing 값 고르는 법. '-Y 로 맞춤' 만으로는 neg-y·pos-y 중 무엇을 줄지 몰랐다(10/11 9회차 실측)."""
    return T("캐릭터가 보는 방향(기본 auto: 발끝 방향으로 판단, 사족은 머리). Blender 에 가져와 앞 보기(숫자패드 1)에서 "
             "얼굴이 보이면 neg-y, 뒤통수가 보이면 pos-y — auto 로 만든 리그가 등을 앞으로 하고 있을 때 준다",
             "which way the character faces (default auto: judged from the toes, from the head for quadrupeds). Import it into "
             "Blender and look from the front (numpad 1): face visible → neg-y, back of the head visible → pos-y — "
             "use it when the auto rig comes out facing backwards")


def preset_hint() -> str:
    """틀린 --preset(dog·cat·animal…)에 붙일 한 줄. 선택지 나열만으로는 네 발 짐승이 quadruped 인지 몰랐다(10/11 10회차)."""
    return T("사람·인간형은 humanoid, 네 발 짐승(개·고양이·늑대)은 quadruped. 다리가 그 밖인 메시(곤충·괴물)는 "
             "`bw rig <메시> --from-shape`", "humanoid for people and human-like characters, quadruped for four-legged animals "
             "(dog, cat, wolf). Other body plans (insects, monsters): `bw rig <mesh> --from-shape`")


def _hint_on_choice(p: argparse.ArgumentParser, flag: str, hint) -> None:
    """argparse 의 'argument <flag>: invalid choice' 끝에 값 고르는 법 한 줄(종료 2 그대로). hint 는 부를 때 만든다(언어)."""
    orig = p.error
    def error(message: str):
        orig(message + "\n→ " + hint() if f"argument {flag}: invalid choice" in message else message)
    p.error = error


def parse_pin(text: str) -> tuple[str, dict[str, list[float]]]:
    """argparse type for --pin 본=x,y,z[/x,y,z] → ("본", {"head": [...], "tail": [...]}).
    틀리면 다른 입력 오류(`--size 0`)처럼 종료 2 + `→` 그대로 붙여 넣을 예. 예에는 사용자가 쓴 본 이름을 넣는다(10/11 11회차:
    종료 1 에 `→` 없는 한 줄이었다)."""
    name, _, rest = text.partition("=")
    bone = name.strip() or "spine.004"
    example = "→ " + T("예", "e.g.") + f" --pin {bone}=0,0,1.42  " + T("또는 머리/꼬리", "or head/tail") + f" --pin {bone}=0.6,0,1.3/0.7,0,1.3"
    parts = rest.split("/")
    if not name.strip() or "=" not in text or len(parts) > 2:
        raise argparse.ArgumentTypeError(T(f"본=x,y,z 꼴이어야 한다(받은 값 {text!r}) {example}", f"must look like BONE=x,y,z (got {text!r}) {example}"))
    try:
        v = {"head": [float(x) for x in parts[0].split(",")]}
        if len(parts) > 1:
            v["tail"] = [float(x) for x in parts[1].split(",")]
    except ValueError:
        v = {"head": []}
    if len(v["head"]) != 3 or len(v.get("tail", [0, 0, 0])) != 3 or not all(math.isfinite(x) for c in v.values() for x in c):
        raise argparse.ArgumentTypeError(T(f"좌표는 숫자 x,y,z 세 개를 쉼표로, 공백 없이(받은 값 {text!r}) {example}",
                                           f"coordinates are three numbers x,y,z, comma-separated, no spaces (got {text!r}) {example}"))
    return name.strip(), v


def run_id_arg(text: str) -> str:
    """argparse type for run ids: 글자·숫자·`_` 로 시작, 그 뒤 글자·숫자·`._-` 만, `..` 없음.
    10/11 11회차: `--run-id ../escape` 가 runs/ 밖에 폴더를 만들 수 있었고, `bw doctor --for-issue ../..` 는 runs/ 밖을 읽었다."""
    import re
    if text == "":   # `--for-issue` 를 값 없이 쓰면 argparse 가 const "" 도 이 type 에 넣는다
        return text
    if not re.fullmatch(r"\w[\w.-]*", text) or ".." in text:
        raise argparse.ArgumentTypeError(T(f"실행 id 는 글자·숫자·. _ - 만, 폴더 구분자(/ \\)·'..'·공백 없이(받은 값 {text!r}) → 예: hero-v2",
                                           f"a run id takes letters, digits and . _ - only, no path separators (/ \\), '..' or spaces (got {text!r}) → e.g. hero-v2"))
    return text


def positive_int(flag: str, example: int):
    """argparse type: 1 이상 정수만. 0·음수는 리그·렌더까지 간 뒤에야 실패하거나(demo) 빈 결과로 끝나서(usage) 여기서 막는다."""
    def parse(text: str) -> int:
        try:
            v = int(text)
        except ValueError:
            v = 0
        if v < 1:
            raise argparse.ArgumentTypeError(T(f"1 이상 정수여야 한다(받은 값 {text!r}) → 예: {flag} {example}",
                                               f"must be a whole number of 1 or more (got {text!r}) → e.g. {flag} {example}"))
        return v
    return parse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bw", description=f"bonewright {__version__}: Python drives, Codex judges, gates verify.")
    p.add_argument("--version", action="version", version=f"bonewright {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    _hint_on_bad_command(p, sub)
    _hint_on_unquoted(p)
    r = sub.add_parser("rig", help=T("메시를 Rigify 로 리깅하고 검증한다", "rig a mesh with Rigify and check it"))
    r.add_argument("mesh", help=T("리깅할 메시(.glb·.gltf·.fbx·.obj·.blend)", "mesh to rig (.glb, .gltf, .fbx, .obj, .blend)")); r.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid", help=T("리그 종류(기본 humanoid). 네 발 짐승은 quadruped", "rig type (default humanoid); quadruped for four-legged animals"))
    _hint_on_choice(r, "--preset", preset_hint)
    r.add_argument("--run-id", type=run_id_arg, help=T("실행 폴더 이름 runs/<id>(기본 rig-날짜-시각). 같은 id 면 덮어쓴다", "name of the run folder runs/<id> (default rig-<date>-<time>); the same id overwrites")); r.add_argument("--lang", choices=["ko", "en"], help=T("모델 프롬프트 언어(생략하면 runs/config.json 의 lang, 그것도 없으면 BW_LANG·로캘)", "language of the model prompts (default: lang in runs/config.json, else BW_LANG / locale like the screen text)")); r.add_argument("--budget", type=positive_int("--budget", 600_000), metavar="TOKENS",
                   help=T("모델 입력 토큰 상한(기본 600,000 — runs/config.json 의 budget.max_input_tokens). 넘으면 멈춘다",
                          "cap on model input tokens (default 600,000 — budget.max_input_tokens in runs/config.json); the run stops when it is reached"))
    r.add_argument("--no-judge", action="store_true", help=T("시각 판정(모델 호출) 생략", "skip the visual judge (model call)")); r.add_argument("--facing", choices=FACING, default="auto", help=facing_help()); r.add_argument("--quiet", action="store_true", help=T("진행 로그를 끈다(결과·오류만)", "no progress log (results and errors only)"))
    _hint_on_choice(r, "--facing", facing_help)
    r.add_argument("--force", action="store_true", help=T("거절 게이트를 무시하고 진행(비인간·크기 이상 메시도 리깅 시도)", "ignore the rejection gate and rig anyway (non-human or oddly sized meshes too)"))
    _hint_on_conflict(r, T("→ 하나만 준다: --from-skeleton 은 파일에 든 원본 뼈대를 쓰고, --from-shape 은 뼈대가 없을 때 메시 모양에서 만든다",
                           "→ pick one: --from-skeleton uses the skeleton already in the file, --from-shape builds one from the mesh when there is none"))
    source = r.add_mutually_exclusive_group()   # 뼈대를 어디서 얻을지는 하나만(10/10 8회차: 둘 다 받아 어느 쪽이 이기는지 안 보였다)
    source.add_argument("--from-shape", action="store_true", help=T("메시 속 중심선에서 뼈대를 직접 만들어 리깅한다(토큰 0). 뼈대가 없고 사람·개과 비율도 아닌 메시(곤충·괴물)에 쓴다 — 해부학적 관절이 아니라 모양을 따라가는 조작 장치다", "build the skeleton from the mesh's own centrelines (0 tokens). For meshes with no skeleton and neither human nor dog proportions (insects, monsters) — controls follow the shape, not anatomical joints"))
    source.add_argument("--from-skeleton", action="store_true", help=T("파일에 든 원본 뼈대의 관절을 그대로 써서 Rigify 리그를 만든다(토큰 0). 실루엣으로 관절을 못 찾는 로봇·양식화 캐릭터에 쓴다", "build the Rigify rig on the joints of the skeleton already in the file (0 tokens). For robots and stylised characters whose silhouette hides the joints"))
    r.add_argument("--rest-pose", choices=["keep", "t"], default=None, help=T("쉬는 자세: keep=메시 자세 그대로(기본), t=팔을 수평으로 굳혀 T 포즈로", "rest pose: keep=the mesh's own pose (default), t=bake arms horizontal into a T-pose"))
    r.add_argument("--weights", choices=["auto", "proxy"], default=None, help=T("스키닝: auto=Bone Heat(비면 복셀 대리), proxy=항상 복셀 대리", "skinning: auto=Bone Heat (voxel proxy if it leaves gaps), proxy=always the voxel proxy"))
    r.add_argument("--pin", action="append", type=parse_pin, metavar=T("본=x,y,z[/x,y,z]", "BONE=x,y,z[/x,y,z]"),
                   help=T("관절을 직접 고정한다. 예: --pin spine.004=0,0,1.42 (머리만), --pin hand.L=0.6,0,1.3/0.7,0,1.3 (머리/꼬리). 여러 번 쓸 수 있다", "pin a joint by hand. e.g. --pin spine.004=0,0,1.42 (head only), --pin hand.L=0.6,0,1.3/0.7,0,1.3 (head/tail). Repeatable"))
    r.add_argument("--targets", metavar="targets.json", help=T("이전 실행의 targets.json 을 그대로 쓴다(모델 호출 0회, 토큰 0)", "reuse a previous run's targets.json (0 model calls, 0 tokens)"))
    _hint_on_missing(r, "mesh", T(f"→ 처음이면 저장소 폴더에서, 저장소에 든 캐릭터로(모델 호출 없음): {FIRST_RIG}  (README \"첫 실행\")",
                                  f"→ new here? from the repository folder, on the character it ships (no model calls): {FIRST_RIG}  (README \"First run\")"))
    m = sub.add_parser("motion", help=T("텍스트(kimodo.cpp) 또는 BVH 에서 동작을 만들어 Blender 로 가져온다", "make motion from text (kimodo.cpp) or a BVH and bring it into Blender"))
    m.add_argument("--text", help=T("동작을 글로(kimodo.cpp 로 BVH 를 만든다, 예: \"a person walks\")", "describe the motion in words (kimodo.cpp makes the BVH, e.g. \"a person walks\")")); m.add_argument("--bvh", help=T("옮길 BVH 파일", "BVH file to retarget")); m.add_argument("--run-id", type=run_id_arg, help=T("실행 폴더 이름 runs/<id>(기본 motion-날짜-시각)", "name of the run folder runs/<id> (default motion-<date>-<time>)")); m.add_argument("--quiet", action="store_true", help=T("진행 로그를 끈다(결과·오류만)", "no progress log (results and errors only)"))
    m.add_argument("--rig", type=run_id_arg, help=T("리깅 결과 run-id: 그 리그에 동작을 옮긴다(리타겟, 토큰 0)", "run-id of a rig: retarget the motion onto it (0 tokens)"))
    m.add_argument("--preset", choices=["humanoid", "quadruped"], default=None, help=T("리그의 프리셋. 생략하면 리그 실행 기록(rig_stats.json)에서 읽는다", "the rig's preset. Read from the rig run (rig_stats.json) when omitted"))
    _hint_on_choice(m, "--preset", preset_hint)
    m.add_argument("--bvh-up", choices=["auto", "y", "z"], default="auto", help=T("BVH 의 위 축. auto=머리와 발 위치로 판단(기본). 표준은 y, Blender 가 내보낸 BVH 는 z", "BVH up axis. auto=decide from head and feet (default). Standard BVH is y, Blender-exported BVH is z"))
    m.add_argument("--legs", choices=["auto", "fk", "ik"], default="auto", help=T("다리 전달: auto(소스에 발끝 관절이 있는 다리만 IK) | fk(회전만) | ik(발 IK 로 BVH 발끝을 좇음, 비율 차이 흡수)", "legs: auto (IK only for legs whose source has toe joints) | fk (rotation only) | ik (foot IK follows the BVH feet, absorbs proportion differences)"))
    m.add_argument("--no-roll", action="store_true", help=T("리타겟에서 비틀림(롤)을 옮기지 않는다(방향만, A/B 비교용)", "do not transfer twist (roll), direction only (for A/B comparison)"))
    m.add_argument("--map", dest="bone_map", metavar="bones.json",
                   help=T('BVH 본 → 리그 본 매핑 파일 {"LeftArm": "upper_arm.L"}. 이름이 없는 리그(모양 리그의 Limb3_2 등)는 자동 매핑이 못 붙으니 직접 적는다',
                          'BVH bone → rig bone map {"LeftArm": "upper_arm.L"}. Rigs without standard names (a shape rig\'s Limb3_2 etc.) need one written by hand'))
    m.add_argument("--export", nargs="?", const="auto", help=T("리타겟 결과를 GLB 로 내보낸다(변형 본만·애니 구움). 경로 생략 시 runs/<id>/animated.glb", "export the retargeted result as GLB (deform bones only, animation baked). Default path runs/<id>/animated.glb"))
    ex = sub.add_parser("export", help=T("리그 결과를 변형 본만 든 GLB 로 내보내기(게임 엔진용), 토큰 0", "export a rig as a deform-only GLB for game engines (0 tokens)"))
    ex.add_argument("run_id", nargs="?", type=run_id_arg, help=T("내보낼 리그의 실행 id(`bw status` 로 목록, 생략하면 최근 리그를 알려 준다)", "run id of the rig to export (list with `bw status`; omit it to be told the latest rig)")); ex.add_argument("--out", help=T("출력 경로(기본 runs/<id>/rigged.glb)", "output path (default runs/<id>/rigged.glb)")); ex.add_argument("--quiet", action="store_true", help=T("진행 로그를 끈다(결과·오류만)", "no progress log (results and errors only)"))
    d = sub.add_parser("demo", help=T("리그 결과를 IK 로 움직인 데모 영상(mp4/gif) 만들기, 토큰 0", "render a demo video (mp4/gif) of the rig moving through its IK controls (0 tokens)"))
    d.add_argument("run_id", nargs="?", type=run_id_arg, help=T("영상으로 볼 리그의 실행 id(생략하면 최근 리그를 알려 준다)", "run id of the rig to film (omit it to be told the latest rig)")); d.add_argument("--size", type=positive_int("--size", 640), default=640, help=T("영상 한 변 픽셀(기본 640)", "video size in pixels per side (default 640)")); d.add_argument("--frames", type=positive_int("--frames", 96), default=96, help=T("프레임 수(기본 96, 24fps 로 4초)", "number of frames (default 96, 4 s at 24 fps)")); d.add_argument("--quiet", action="store_true", help=T("진행 로그를 끈다(결과·오류만)", "no progress log (results and errors only)"))
    bm = sub.add_parser("bench", help=T("원본 뼈대가 든 캐릭터로 관절 오차를 cm 단위로 잰다(토큰 0)", "measure joint error in cm against characters that carry their own skeleton (0 tokens)"))
    bm.add_argument("meshes", nargs="+", help=T("GLB/FBX 파일 또는 폴더", "GLB/FBX files or folders"))
    _hint_on_missing(bm, "meshes", T("→ 벤치 자산은 저장소에 없다. 받은 뒤 폴더째로(샘플 4개): python3 scripts/fetch_bench_assets.py --only samples && bw bench bench-assets/samples",
                                     "→ benchmark assets are not in the repository. Fetch them, then pass a folder (4 samples): python3 scripts/fetch_bench_assets.py --only samples && bw bench bench-assets/samples"))
    bm.add_argument("--run-id", type=run_id_arg, help=T("결과 폴더 이름 runs/<id>(기본 bench-날짜-시각)", "name of the results folder runs/<id> (default bench-<date>-<time>)")); bm.add_argument("--facing", choices=FACING, default="auto", help=facing_help())
    _hint_on_choice(bm, "--facing", facing_help)
    bm.add_argument("--preset", choices=["humanoid", "quadruped"], default="humanoid", help=T("리그 종류(기본 humanoid)", "rig type (default humanoid)"))
    _hint_on_choice(bm, "--preset", preset_hint)
    bm.add_argument("--rest-pose", choices=["keep", "t"], default=None, help=T("리깅할 때 쉬는 자세를 T 로 굳힌다(포즈 정규화 측정용)", "bake a T rest pose while rigging (to measure pose normalisation)"))
    bm.add_argument("--gt-mesh", help=T("정답 뼈대를 이 파일에서 가져온다(포즈 변형본을 원본 T 포즈와 맞댈 때)", "take the reference skeleton from this file (to compare a posed variant with its original T-pose)"))
    bm.add_argument("--quiet", action="store_true", help=T("진행 로그를 끈다(결과·오류만)", "no progress log (results and errors only)"))
    bm.add_argument("--skin", action="store_true", help=T("스키닝 일치도도 잰다(원본 가중치와 대조, 토큰 0)", "also measure skinning agreement with the original weights (0 tokens)"))
    bm.add_argument("--weights", choices=["auto", "proxy"], default=None, help=T("스키닝 방법 강제(A/B 비교용)", "force a skinning method (for A/B comparison)"))
    st = sub.add_parser("status", help=T("실행 기록 목록 또는 한 실행의 단계·상태", "list runs, or one run's step and status")); st.add_argument("run_id", nargs="?", type=run_id_arg, help=T("한 실행만 자세히(생략하면 목록)", "show one run in detail (omit for the list)"))
    u = sub.add_parser("usage", help=T("모델 호출 사용량 장부 요약", "summarise the model-usage ledger")); u.add_argument("--days", type=positive_int("--days", 30), default=7, help=T("며칠 치를 셀지(기본 7)", "how many days back to count (default 7)"))
    dr = sub.add_parser("doctor", help=T("Blender·bpy·codex·kimodo.cpp 가 준비됐는지 확인", "check that Blender or bpy, codex and kimodo.cpp are reachable"))
    dr.add_argument("--for-issue", nargs="?", const="", type=run_id_arg, metavar="RUN_ID",
                    help=T("버그 신고에 붙일 덩어리를 찍는다: 버전·OS·이 점검 결과·실행 하나(생략하면 가장 최근)의 state.json·마지막 로그 꼬리. 개인 경로는 ~ 로 바꾼다",
                           "print a block to paste into a bug report: versions, OS, this check, and one run's state.json and log tail (the latest run if omitted). Home paths become ~"))
    sub.add_parser("plugin-path", help=T("Codex 플러그인 폴더 경로 출력", "print the Codex plugin folder"))
    return p


def _closed_stdout() -> int:
    """읽는 쪽이 닫힌 stdout 을 devnull 로 돌려, 끝날 때의 flush 가 또 BrokenPipeError 를 내지 않게 한다(파이썬 문서 signal 절 방식)."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError, io.UnsupportedOperation):
        pass
    return 1


def main() -> int:
    """`bw doctor | head` 처럼 읽는 쪽이 먼저 닫으면 오류가 아니다. 파이프로 나가는 stdout 은 블록 버퍼라 끝날 때
    flush 에서야 터지므로, 여기서 flush 까지 하고 받는다(10/10 CI 에서 드러남)."""
    try:
        try:
            code = _main()
        except SystemExit:          # argparse 의 --version·--help 와 입력 오류도 같은 flush 를 거친다
            sys.stdout.flush(); raise
        sys.stdout.flush()
        return code
    except BrokenPipeError:
        return _closed_stdout()


def home_problem() -> tuple[str, str] | None:
    """BW_HOME 이 파일이거나 없는 폴더면 ("file"|"missing", 문구). 10/11 11회차: 파일이어도 `bw status` 는
    "아직 실행 없음(찾은 곳: <파일>/runs)" 으로 종료 0, `bw doctor` 는 그 경로를 작업 폴더로 그대로 찍었다."""
    env = os.environ.get("BW_HOME")
    if not env:
        return None
    home = Path(env).expanduser()
    if home.is_file():
        return "file", T(f"BW_HOME 이 폴더가 아니라 파일이다: {home}\n  → 작업 폴더(runs/ 가 있거나 생길 곳)로 고치거나 BW_HOME 을 지운다(지금 폴더를 쓴다)",
                         f"BW_HOME is a file, not a folder: {home}\n  → point it at a work folder (where runs/ is or will be), or unset it to use the current folder")
    if not home.exists():
        return "missing", T(f"⚠ BW_HOME 폴더가 없다: {home} — 첫 `bw rig` 가 만든다. 다른 곳에서 돌렸다면 BW_HOME 을 그 폴더로",
                            f"⚠ BW_HOME does not exist: {home} — the first `bw rig` creates it. If you ran bonewright elsewhere, point BW_HOME there")
    return None


def _main() -> int:
    parser = build_parser()
    if len(sys.argv) <= 1:   # 인자 없는 `bw`: argparse 는 "required: cmd" 한 줄로 끝난다. 설치 직후 가장 먼저 치는 것이라 명령 목록과 첫 걸음을
        parser.print_help(sys.stderr)
        print(T("\n처음이면: `bw doctor` 로 Blender·codex 준비를 확인한 뒤 README 의 \"첫 실행\"(영어판 \"First run\") 첫 명령을 돌려라(모델 호출 없음)",
                "\nnew here? run `bw doctor` to check Blender and codex, then the first command under \"First run\" in the README (no model calls)"),
              file=sys.stderr)
        return 2
    a = parser.parse_args()
    if a.cmd != "plugin-path" and (msg := home_problem()):
        if msg[0] == "file":   # 무엇을 하든 그 아래에 runs/ 를 만들 수 없다
            print("BLOCKED:", msg[1], file=sys.stderr); return 2
        if a.cmd in ("status", "doctor"):   # rig 등은 처음 돌 때 만든다. 목록·점검만 "없다" 를 알린다
            print(msg[1], file=sys.stderr)
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
            report = summarize(ROOT, a.days)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if not report["total"]["calls"]:   # 0 만 든 JSON 은 '기록 안 됨' 인지 '안 썼음' 인지 모른다 → stderr 한 줄(stdout JSON 은 그대로)
                book = ledger_path(ROOT)
                where = book if book.exists() else T(f"{book} — 아직 없음, BW_HOME(지금 {ROOT})이 맞는지 확인", f"{book} — not created yet; check BW_HOME (now {ROOT})")
                print(T(f"최근 {a.days}일 모델 호출 없음(장부: {where}). 토큰 0 경로(--from-skeleton·--from-shape·--targets·BW_BACKEND=mock)만 썼다면 정상 → 더 길게: `bw usage --days 30`",
                        f"no model calls in the last {a.days} days (ledger: {where}). Normal if you only used the 0-token routes (--from-skeleton, --from-shape, --targets, BW_BACKEND=mock) → look further back: `bw usage --days 30`"), file=sys.stderr)
            return 0
        if a.cmd == "status":
            runs = ROOT / "runs"
            ids = [a.run_id] if a.run_id else sorted(p.name for p in runs.iterdir() if (p / "state.json").exists()) if runs.is_dir() else []
            if a.run_id and not (runs / a.run_id / "state.json").exists():
                print("BLOCKED:", T(f"실행 기록이 없다: {runs / a.run_id}\n  → `bw status` 로 목록을 보거나 BW_HOME(지금 {ROOT})을 확인하라",
                                   f"no such run: {runs / a.run_id}\n  → list runs with `bw status`, or check BW_HOME (now {ROOT})"), file=sys.stderr); return 2
            if not ids:   # 빈 출력은 설치가 깨졌는지 BW_HOME 이 다른지 구분이 안 된다
                print(T(f"아직 실행이 없다(찾은 곳: {runs})\n  → 저장소 폴더에서 저장소의 캐릭터로 시작(모델 호출 없음): `{FIRST_RIG}`, 내 메시는 `bw rig <메시>`. "
                        "다른 폴더에서 돌렸다면 BW_HOME 을 그 폴더로",
                        f"no runs yet (looked in {runs})\n  → start from the repository folder on the character it ships (no model calls): `{FIRST_RIG}`; "
                        "your own mesh: `bw rig <mesh>`. If you ran bonewright from another folder, set BW_HOME to it"),
                      file=sys.stderr)
            for rid in ids:   # 읽히지 않는 실행 하나(동기화 충돌 사본·옛 버전)가 목록 전체를 막지 않게 그 줄만 알린다
                try:
                    s = json.loads((runs / rid / "state.json").read_text(encoding="utf-8"))
                    line = f"{rid}: {s['step']} {s['status']} · "   # 먼저 키를 읽는다: 목록·키 없는 state 는 아래 except 로
                    tokens = f"{s.get('input_tokens', 0):,}"
                    line += T(f"입력 토큰 {tokens}", f"input tokens {tokens}")
                    if s["status"] in ("failed", "budget_stop", "usage_limit"):   # 왜 멈췄는지 볼 곳(로그 꼬리·state)
                        line += T(f"  → 이유: `bw doctor --for-issue {rid}`", f"  → why: `bw doctor --for-issue {rid}`")
                except (ValueError, KeyError, TypeError, OSError) as e:
                    line = T(f"{rid}: state.json 을 읽지 못함({type(e).__name__}: {e}) — 이 실행만 건너뜀. 필요 없으면 {runs / rid} 를 지워도 된다",
                             f"{rid}: state.json unreadable ({type(e).__name__}: {e}) — skipped this run only. If you don't need it, {runs / rid} can be deleted")
                print(line)
            return 0
        if a.cmd in ("export", "demo") and not a.run_id:   # argparse 의 "required: run_id" 는 어떤 id 를 넣을지 말해 주지 않는다
            runs = ROOT / "runs"
            rigged = [p for p in runs.iterdir() if (p / "02_rigged.blend").is_file()] if runs.is_dir() else []
            if rigged:
                rid = max(rigged, key=lambda p: (p / "02_rigged.blend").stat().st_mtime).name
                print("BLOCKED:", T(f"run-id 가 필요하다 — 가장 최근 리그: `bw {a.cmd} {rid}`\n  → 다른 실행은 `bw status` 로 목록을 본다",
                                   f"needs a run-id — latest rig: `bw {a.cmd} {rid}`\n  → list other runs with `bw status`"), file=sys.stderr)
            else:
                print("BLOCKED:", T(f"run-id 가 필요한데 리깅을 마친 실행이 없다(찾은 곳: {runs})\n  → 먼저 `{FIRST_RIG}`(또는 내 메시로 `bw rig <메시>`), 끝에 나오는 `next:` 줄에 id 가 있다. "
                                   "다른 폴더에서 돌렸다면 BW_HOME 을 그 폴더로",
                                   f"needs a run-id, and no finished rig was found (looked in {runs})\n  → run `{FIRST_RIG}` (or `bw rig <mesh>` on yours) first; its `next:` line carries the id. "
                                   "If you ran bonewright from another folder, set BW_HOME to it"), file=sys.stderr)
            return 2
        if a.cmd == "rig":
            out = pipeline.rig(ROOT, a.mesh, a.preset, run_id=a.run_id, lang=a.lang, quiet=a.quiet, budget=a.budget, no_judge=a.no_judge, facing=a.facing, pins=dict(a.pin or []), targets_file=a.targets, force=a.force, rest_pose=a.rest_pose, weights=a.weights, from_skeleton=a.from_skeleton, from_shape=a.from_shape)
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
    except (pipeline.Blocked, blender.BlenderMissing) as e:   # 설치·설정으로 고치는 것: 이슈 안내 없이
        print("BLOCKED:", e, file=sys.stderr); return 2
    except BrokenPipeError:
        raise                # main() 이 조용히 끝낸다 — '예상 못 한 오류' 가 아니다
    except Exception as e:  # Blender 오류 등
        report_unexpected(e, started, getattr(a, "run_id", None)); return 2
    print(T("보고서:", "report:"), out)
    if a.cmd == "rig":   # README 다음 줄이 `bw demo <run-id>` 라 id 를 경로에서 오려 내지 않게(stdout 은 보고서 경로 한 줄 그대로)
        rid = Path(out).parent.name; bv = pipeline.sample_bvh()   # 저장소의 손 흔들기 BVH — 그대로 붙여 넣어 돈다
        print(T(f"다음: `bw demo {rid}`(움직이는 영상) · `bw export {rid}`(게임용 GLB) · `bw motion --bvh {bv} --rig {rid}`",
                f"next: `bw demo {rid}` (video of it moving) · `bw export {rid}` (game-ready GLB) · `bw motion --bvh {bv} --rig {rid}`"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
