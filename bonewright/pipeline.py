"""파이프라인: rig(분석 → 맞춤 판단 → 생성·스키닝 → 게이트 → 렌더 → 시각 판정 → 보고서), motion(kimodo → BVH → 가져오기)."""
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

from . import __version__, schemas
from .blender import BlenderError, require as need_blender, run_script
from .codex import CodexError, UsageLimit, run_step
from .config import load, unknown_keys_line
from .from_skeleton import targets_from_skeleton
from .gates import judge_gates, preflight, rig_gates
from .i18n import T
from .ledger import append as ledger_append
from .manifest import atomic_write
from .mock import mock_backend

PROMPTS = Path(__file__).parent / "prompts"


class Blocked(RuntimeError):
    """사용자가 고쳐서 다시 돌릴 수 있는 중단. 메시지에는 '무엇을 바꾸면 되는지'를 한 줄 넣는다."""


MESH_EXTS = (".glb", ".gltf", ".fbx", ".obj", ".blend")   # bpy_scripts/_common.py import_mesh 가 읽는 형식


def need_file(path: str | Path, what: str, fix: str, exts: tuple[str, ...] = (), many: str = "") -> Path:
    """입력 파일을 Blender·모델을 부르기 **전에** 확인한다. 없거나 형식이 틀리면 고칠 방법을 담아 Blocked.
    what·fix·many 는 호출하는 쪽에서 T(한국어, 영어)로 넘긴다. many: 폴더를 줬을 때 여러 파일을 한 번에 다루는 명령."""
    p = Path(path).expanduser()
    if p.is_dir():   # "파일이 없다" 는 거짓말이다 — 폴더는 있다(10/10 8회차 `bw rig .`)
        inside = sorted(f for f in p.iterdir() if f.is_file() and (not exts or f.suffix.lower() in exts))
        first = T(f" 예: {inside[0]}", f" e.g. {inside[0]}") if inside else ""
        also = f"\n  → {many}" if many else ""
        raise Blocked(T(f"{what} 자리에 폴더를 줬다: {p}\n  → 파일 하나를 준다.{first}{also}",
                        f"{what}: this is a folder, not a file: {p}\n  → pass one file.{first}{also}"))
    if not p.is_file():
        raise Blocked(T(f"{what} 파일이 없다: {p}\n  → {fix}", f"{what} file not found: {p}\n  → {fix}"))
    if exts and p.suffix.lower() not in exts:
        raise Blocked(T(f"{what} 형식을 읽을 수 없다: {p.suffix or '(확장자 없음)'} ({p.name})\n  → {' · '.join(exts)} 중 하나로 내보내서 다시 지정하라",
                        f"cannot read {what} format: {p.suffix or '(no extension)'} ({p.name})\n  → export it as one of {' · '.join(exts)} and pass that"))
    return p


def need_mesh_bytes(p: Path) -> None:
    """Blender 를 띄우기 전에 빈 파일·GLB 머리가 틀린 파일을 막는다. 10/10 8회차: 0바이트 .glb 가 Blender 를 띄운 뒤에야
    실패했고, Blender 가 없는 곳에선 'Blender not found' 가 진짜 원인을 가렸다."""
    size = p.stat().st_size
    if size == 0:
        raise Blocked(T(f"메시 파일이 비었다(0바이트): {p}\n  → 내보내기·내려받기가 끝까지 됐는지 보고 원본에서 다시 내보내라",
                        f"the mesh file is empty (0 bytes): {p}\n  → check that the export or download finished, and export it again"))
    if p.suffix.lower() == ".glb":
        with open(p, "rb") as f:
            head = f.read(4)
        if head != b"glTF":
            raise Blocked(T(f"GLB 가 아니다(머리가 'glTF' 가 아님, {size:,}바이트): {p}\n  → 이름만 .glb 인 다른 파일일 수 있다. "
                            "Blender 등에서 glTF Binary(.glb)로 다시 내보내라",
                            f"not a GLB (the file does not start with 'glTF', {size:,} bytes): {p}\n  → it may be another format "
                            "renamed to .glb. Export it again as glTF Binary (.glb), e.g. from Blender"))


def need_bvh_bytes(p: Path) -> None:
    """이름만 .bvh 인 파일(내려받기 실패한 HTML·빈 파일)을 실행 폴더·Blender 전에 막는다. BVH 는 'HIERARCHY' 로 시작한다.
    10/11 10회차: 확장자만 보고 Blender 가져오기까지 갔고, Blender 가 없는 곳에선 'Blender not found' 가 원인을 가렸다."""
    size = p.stat().st_size
    if size == 0:
        raise Blocked(T(f"BVH 파일이 비었다(0바이트): {p}\n  → 내려받기·내보내기가 끝까지 됐는지 보고 다시 받아라. 저장소의 샘플: `--bvh {sample_bvh()}`",
                        f"the BVH file is empty (0 bytes): {p}\n  → check that the download or export finished, and get it again. The repository's sample: `--bvh {sample_bvh()}`"))
    with open(p, "rb") as f:
        head = f.read(256).decode("latin-1").lstrip("\ufeff\xef\xbb\xbf \t\r\n")
    if not head.upper().startswith("HIERARCHY"):
        first = head.splitlines()[0][:40] if head.strip() else ""
        raise Blocked(T(f"BVH 가 아니다(첫 줄이 'HIERARCHY' 가 아님: {first!r}, {size:,}바이트): {p}\n  → 이름만 .bvh 인 다른 파일(웹 페이지 등)일 수 있다. "
                        f"원본에서 BVH 로 다시 내보내거나 받아라. 저장소의 샘플: `--bvh {sample_bvh()}`",
                        f"not a BVH (the first line is not 'HIERARCHY': {first!r}, {size:,} bytes): {p}\n  → it may be another file (a web page, say) "
                        f"saved as .bvh. Export or download it again as BVH. The repository's sample: `--bvh {sample_bvh()}`"))


def metarig_names(preset: str) -> list[str]:
    """Rigify 메타리그의 본 이름 전부(Blender 없이). 목록은 bonewright/metarig_names.json — Blender 시험이 실제 메타리그와 대조한다."""
    return json.loads((Path(__file__).parent / "metarig_names.json").read_text(encoding="utf-8")).get(preset, [])


def need_pin_names(pins: dict, preset: str) -> None:
    """--pin 의 본 이름을 Blender 전에 메타리그와 대조한다. 10/10 8회차 실측: 없는 이름은 Blender 까지 가서 말없이 무시됐다."""
    import difflib
    names = metarig_names(preset)
    bad = [n for n in pins if n not in names]
    if not names or not bad:
        return
    lines = []
    for n in bad:   # 대소문자만 다른 이름(hand.l → hand.L)을 맨 앞에
        near = [m for m in names if m.lower() == n.lower()]
        near += [m for m in difflib.get_close_matches(n, names, n=3, cutoff=0.5) if m not in near]
        lines.append(f"  - {n}" + (T(f" → 가까운 이름: {', '.join(near[:3])}", f" → closest: {', '.join(near[:3])}") if near else ""))
    listed = "\n".join(lines)
    ex = "spine.004" if preset == "quadruped" else "hand.L"
    raise Blocked(T(f"--pin 의 본 이름이 {preset} 메타리그에 없다:\n{listed}\n  → 메타리그 이름을 쓴다(대소문자·.L/.R 까지 같게). 예: --pin {ex}=0.6,0,1.3",
                    f"--pin bone not in the {preset} metarig:\n{listed}\n  → use a metarig bone name (case and .L/.R must match). e.g. --pin {ex}=0.6,0,1.3"))


def sample_bvh() -> str:
    """안내에 넣을 샘플 BVH 경로(examples/wave.bvh — rig_sample.wave_bvh 가 만든 손 흔들기 24프레임, 저장소에 실려 있다).
    저장소 폴더에서 치면 상대 경로, 다른 곳이면 저장소의 절대 경로, 패키지만 설치돼 없으면 자리표시."""
    if Path("examples/wave.bvh").is_file():
        return "examples/wave.bvh"
    p = Path(__file__).resolve().parents[1] / "examples" / "wave.bvh"
    return str(p) if p.is_file() else T("<파일.bvh>", "<file.bvh>")


def need_rig(root: Path, run_id: str, use: str = "") -> Path:
    """리깅 결과(.blend)가 있는 실행인지 확인한다. 없으면 실행 목록을 보는 법과 리깅 명령을 알려 준다.
    use: 고친 명령의 꼴(예: "bw export {}") — 다른 리그가 있으면 id 오타일 수 있어 가까운 리그를 그 꼴로 준다(10/11 9회차)."""
    blend = root / "runs" / run_id / "02_rigged.blend"
    if not blend.exists():
        state = root / "runs" / run_id / "state.json"
        runs = root / "runs"
        rigged = [p for p in runs.iterdir() if (p / "02_rigged.blend").is_file()] if runs.is_dir() else []
        if not state.exists() and rigged:
            import difflib
            near = difflib.get_close_matches(run_id, [p.name for p in rigged], n=3, cutoff=0.5) \
                or [max(rigged, key=lambda p: (p / "02_rigged.blend").stat().st_mtime).name]
            shown = " · ".join(f"`{use.format(n)}`" if use else n for n in near)
            raise Blocked(T(f"그런 리그가 없다: {run_id}\n  → 가까운 리그: {shown} (전체 목록 `bw status`)",
                            f"no rig named {run_id}\n  → closest rig: {shown} (all runs: `bw status`)"))
        why = (T(f"이 실행은 리깅을 마치지 못했다(`bw status {run_id}`)", f"this run did not finish rigging (`bw status {run_id}`)") if state.exists()
               else T("그런 실행 id 가 없다(`bw status` 로 목록 확인)", "there is no run with that id (list them with `bw status`)"))
        raise Blocked(T(f"리깅 결과가 없다: {blend}\n  → {why}. 먼저 `bw rig <메시> --run-id {run_id}` 로 리깅하라",
                        f"no rig result: {blend}\n  → {why}. Rig first with `bw rig <mesh> --run-id {run_id}`"))
    return blend


def _prompt(name: str, lang: str) -> str:
    return (PROMPTS / lang / f"{name}.md").read_text(encoding="utf-8")


def versions_line(blender_result: dict) -> str:
    """report.md 둘째 줄: 리그 결과는 버전마다 달라, 버전 없는 이슈는 재현이 안 된다(rig-problem 템플릿이 report.md 를 붙이라 한다)."""
    return (f"- versions: bonewright {__version__} · Blender {blender_result.get('blender') or '?'} · "
            f"Python {platform.python_version()} · {platform.system()} {platform.machine()}")


def _shown(path: str | Path, base: Path) -> str:
    """report.md 에 적을 경로: 실행 폴더 안이면 그 기준 상대 경로, 밖이면 홈 폴더를 `~` 로.
    이슈 템플릿이 report.md 를 그대로 붙이라고 하므로 사용자 이름이 든 절대 경로를 남기지 않는다."""
    p = Path(path)
    try:
        return p.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        s = str(p)
        for home in dict.fromkeys((str(Path.home()), str(Path.home().resolve()))):   # 홈이 심볼릭 링크면 resolve 된 메시 경로는 실제 쪽에 있다
            if home not in ("", "/") and (s == home or s.startswith(home + os.sep)):
                return "~" + s[len(home):]
        return s


def _arg(path: str | Path, base: Path) -> str:
    """명령에 넣을 경로: `_shown` 과 같고(홈은 `~`), 공백이 있으면 따옴표로 감싼다 — 안내 명령을 그대로 붙여 넣어 돌게."""
    s = _shown(path, base)
    return f'"{s}"' if any(c.isspace() for c in s) else s


def _log(quiet: bool, msg: str) -> None:
    if not quiet:
        print(f"[bw {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


class Run:
    def __init__(self, root: Path, run_id: str, cfg: dict, quiet: bool = False, state_file: str = "state.json") -> None:
        # state_file: export·demo 는 이미 끝난 리그 실행 폴더를 빌려 쓴다 — 그 실패가 리그의 state.json 을 덮어
        # `bw status` 가 리그까지 실패한 것처럼 보이지 않게 따로 적는다(10/10 8회차)
        self.root, self.run_id, self.cfg, self.quiet, self.state_file = root, run_id, cfg, quiet, state_file
        self.dir = root / "runs" / run_id
        self.logs = self.dir / "logs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.usage: list[dict] = []

    def state(self, step: str, status: str, **extra) -> None:
        atomic_write(self.dir / self.state_file, json.dumps({"step": step, "status": status, "at": time.time(), "pid": os.getpid(),
                                                          "input_tokens": self.tokens()["input"], **extra}, ensure_ascii=False, indent=2))

    def tokens(self) -> dict:
        i = sum(u.get("usage", {}).get("input_tokens", 0) for u in self.usage)
        o = sum(u.get("usage", {}).get("output_tokens", 0) for u in self.usage)
        b = self.cfg["budget"]
        return {"input": i, "output": o, "usd_upper": round(i / 1e6 * b["price_input_per_m"] + o / 1e6 * b["price_output_per_m"], 2)}

    def call(self, name: str, role: str, inputs: dict, schema: dict, images: list[str] | None = None) -> dict:
        limit = self.cfg["budget"]["max_input_tokens"]
        if limit and self.tokens()["input"] >= limit:
            self.state(name, "budget_stop")
            raise Blocked(T(f"예산 상한 도달: 입력 {self.tokens()['input']:,} ≥ {limit:,}\n  → `--budget` 으로 상한을 올리거나 `--targets`·`--from-skeleton` 으로 모델 호출 없이 돌려라",
                            f"budget limit reached: input {self.tokens()['input']:,} ≥ {limit:,}\n  → raise it with `--budget`, or run without model calls via `--targets` / `--from-skeleton`"))
        _log(self.quiet, T(f"  → {name} (파일 {len(inputs)}개, 이미지 {len(images or [])}장)", f"  → {name} ({len(inputs)} files, {len(images or [])} images)"))
        try:
            result, usage = run_step(name, _prompt(name, self.cfg["lang"]), schema, inputs, self.cfg["models"][role], self.cfg["codex"], self.logs,
                                     mock=mock_backend, images=images, heartbeat=lambda m: _log(self.quiet, f"    … {name} {m}"))
        except UsageLimit as e:
            self.state(name, "usage_limit", resets_at=e.resets_at)
            raise Blocked(f"{e}\n  → " + T("리셋 뒤 같은 명령을 다시 실행하라(`bw usage` 로 사용량 확인). "
                                           f"맞춤 판단까지 끝난 실행이면 `--targets runs/{self.run_id}/targets.json` 으로 모델 호출 없이 이어 갈 수 있다",
                                           "run the same command again after the reset (see usage with `bw usage`). "
                                           f"If the fit step already finished, `--targets runs/{self.run_id}/targets.json` continues with no model calls"))
        except CodexError as e:
            self.state(name, "failed")
            raise Blocked(f"{name}: {e}")
        self.usage.append(usage)
        u = usage.get("usage", {})
        ledger_append(self.root, {"run_id": self.run_id, "step": name, "backend": usage.get("backend"), "model": usage.get("model"),
                                  "in": u.get("input_tokens", 0), "cached": u.get("cached_input_tokens", 0), "out": u.get("output_tokens", 0),
                                  "seconds": usage.get("seconds", 0)})
        _log(self.quiet, f"  ← {name} {usage.get('seconds')}s · in {u.get('input_tokens', 0):,} / out {u.get('output_tokens', 0):,}")
        return result

    def blender(self, name: str, params: dict) -> dict:
        _log(self.quiet, f"  ⚙ blender {name}")
        t = time.time()
        try:
            r = run_script(name, params, self.cfg["blender"], self.logs)
        except BlenderError:
            self.state(name, "failed")   # 'running' 으로 남으면 `bw status` 가 영원히 도는 중이라 한다
            raise
        _log(self.quiet, f"  ⚙ {name} {time.time() - t:.1f}s")
        return r


def load_bone_map(path: str | Path) -> dict:
    """`--map` 파일을 읽고 모양을 본다. motion() 이 Blender 를 띄우기 **전에** 부른다(10/10 8회차: 없는 파일이 BVH 가져오기 뒤에야 걸렸다)."""
    try:
        user = json.loads(need_file(path, "--map", T('{"LeftArm": "upper_arm.L"} 형태의 JSON 파일 경로를 지정하라', 'pass a JSON file shaped like {"LeftArm": "upper_arm.L"}')).read_text(encoding="utf-8"))
    except ValueError as e:
        raise Blocked(T(f"--map 파일이 JSON 이 아니다: {path} ({e})\n  → 예: {{\"LeftArm\": \"upper_arm.L\"}}",
                        f"--map file is not JSON: {path} ({e})\n  → e.g. {{\"LeftArm\": \"upper_arm.L\"}}"))
    if not isinstance(user, dict) or not all(isinstance(v, str) for v in user.values()):
        raise Blocked(T(f'--map 파일은 {{"BVH 본": "리그 본"}} 형태여야 한다: {path}\n  → 예: {{"LeftArm": "upper_arm.L", "LeftForeArm": "forearm.L"}}',
                        f'--map file must look like {{"BVH bone": "rig bone"}}: {path}\n  → e.g. {{"LeftArm": "upper_arm.L", "LeftForeArm": "forearm.L"}}'))
    return user


def apply_bone_map(mapping: dict, bone_map: "dict | str | Path", bvh_bones: list) -> tuple[dict, int, list]:
    """사용자 매핑 파일을 자동 매핑 위에 덮어쓴다. {"BVH 본": "리그 본"} 형태.

    이름으로 짝짓는 자동 매핑은 **이름이 없는 리그에서 아무것도 못 붙인다** — 메시 모양에서 만든 사슬
    리그는 본이 `Limb3_2` 라 BVH 의 `LeftArm` 과 맞을 리가 없다. 실측으로 벤치 66종 중 34종이 그래서
    동작을 아예 못 받았다. 자리로 **자동** 짝짓는 건 크게 실패한 적이 있어(docs/ROADMAP.md 의
    '원작자 가중치' 기록), 사람이 직접 적는 길부터 연다.

    BVH 에 없는 이름은 조용히 넘기지 않고 세어서 돌려준다 — 오타를 말해 주지 않으면 사용자는
    "왜 안 붙지"만 반복한다. 돌려주는 값은 (덮어쓴 매핑, 적용된 개수, 무시된 이름들)."""
    user = bone_map if isinstance(bone_map, dict) else load_bone_map(bone_map)
    known = {k: v for k, v in user.items() if k in bvh_bones}
    return {**mapping, **known}, len(known), [k for k in user if k not in bvh_bones]


def fill_missing_targets(targets: dict, inputs: dict) -> tuple[dict, list]:
    """모델이 **빼고 답한 본**을 랜드마크에서 계산한 자리로 메운다. (메운 결과, 메운 이름들)을 돌려준다.

    모델이 자신 없는 본을 빼는 건 옳은 행동이다 — 실제 실행에서 "다리 중심선이 z=0.098 까지만 와서
    발목(z=0.049)을 확인할 수 없으므로 shin·foot 을 제외했다" 고 답했다. 문제는 그러면 그 본이
    **메타리그 기본값 그대로** 남아 몸에서 한참 벗어난다는 것이다.
    mannequiny 실측 — 모델만: 관절 평균 5.96cm(발 24.71cm) · 메우면: 평균 3.21cm(발 6.67cm).
    메우는 값은 `BW_BACKEND=mock` 이 쓰는 것과 **같은 함수**다(랜드마크에서 기계적으로 계산, 토큰 0).
    메우기는 보조 장치라, 실패하면 조용히 모델 답 그대로 간다."""
    try:
        from .mock import mock_backend
        base = {t["name"]: {"head": t["head"], "tail": t["tail"]}
                for t in mock_backend("fit", "", inputs).get("targets", [])}
    except Exception:
        return targets, []
    filled = sorted(n for n in base if n not in targets)
    return {**{n: base[n] for n in filled}, **targets}, filled


def rig(root: Path, mesh: str, preset: str = "humanoid", run_id: str | None = None, lang: str | None = None, quiet: bool = False,
        budget: int | None = None, no_judge: bool = False, facing: str = "auto", pins: dict | None = None, targets_file: str | None = None,
        force: bool = False, rest_pose: str | None = None, weights: str | None = None, from_skeleton: bool = False, from_shape: bool = False) -> Path:
    cfg = load(root, lang)
    if (warn := unknown_keys_line(root)):   # 경로·형식으로 막히기 전에(설정 오타가 원인일 수 있다)
        _log(quiet, warn)
    if budget is not None:   # 0 을 말없이 무시하지 않는다(cli 는 1 이상만 넘긴다)
        cfg["budget"]["max_input_tokens"] = budget
    run_id = run_id or time.strftime("rig-%Y%m%d-%H%M%S")
    mesh = str(need_file(mesh, T("메시", "mesh"), T("경로를 확인하라(따옴표로 감싼 공백 경로 포함)", "check the path (quote paths with spaces)"), MESH_EXTS,
                         many=T(f"폴더 안 메시 여럿을 한 번에 재려면 `bw bench {mesh}`", f"to measure every mesh in the folder at once: `bw bench {mesh}`")).resolve())
    need_mesh_bytes(Path(mesh))
    targets_loaded = None
    if targets_file:   # 형식 오류도 Blender·실행 폴더를 건드리기 전에 막는다(같은 run-id 의 기존 결과를 지키려고)
        tf = need_file(targets_file, "--targets", T("이전 실행의 runs/<id>/targets.json 또는 거절 때 남긴 targets_draft.json 을 지정하라",
                                                "pass runs/<id>/targets.json from an earlier run, or the targets_draft.json left by a rejection"))
        try:
            targets_loaded = json.loads(tf.read_text(encoding="utf-8"))
        except UnicodeDecodeError:   # 텍스트가 아니다 — 쉼표·괄호 안내는 틀린 말이 된다(10/10 8회차: 메시를 --targets 에 줌)
            raise Blocked(T(f"--targets 파일이 글자 파일이 아니다(바이너리): {targets_file}\n  → 메시를 준 것 아닌가? "
                            "--targets 에는 이전 실행의 JSON 을 준다: `--targets runs/<id>/targets.json`",
                            f"--targets is not a text file (binary): {targets_file}\n  → did you pass the mesh? "
                            "--targets takes an earlier run's JSON: `--targets runs/<id>/targets.json`"))
        except ValueError as e:
            raise Blocked(T(f"--targets 파일이 JSON 이 아니다: {targets_file} ({e})\n  → 편집 중 쉼표·괄호가 깨졌는지 확인하라",
                            f"--targets file is not JSON: {targets_file} ({e})\n  → check for a broken comma or bracket from editing"))
    if pins and not from_shape:   # 모양 리그는 메타리그를 쓰지 않는다(본 이름이 실행마다 다르다)
        try:
            need_pin_names(pins, preset)
        except Blocked as e:
            if not from_skeleton:
                raise
            # --from-skeleton 은 메타리그에 못 맞추면 원본 본 이름 그대로의 일반 리그로 간다 — 그 이름일 수 있어 막지 않고 알린다
            _log(quiet, "  ⚠ " + str(e).splitlines()[0] + T(" (일반 리그로 가면 원본 본 이름으로 쓰인다)", " (used as a source bone name if this becomes a generic rig)"))
    need_blender(cfg["blender"])   # 실행 폴더를 만들기 전에
    r = Run(root, run_id, cfg, quiet)
    _log(quiet, f"rig {run_id} · {preset} · {mesh}")
    # 1 분석
    r.state("analyze", "running")
    a = r.blender("analyze", {"mesh": mesh, "blend": str(r.dir / "01_analyzed.blend"), "facing": facing, "preset": preset})
    atomic_write(r.dir / "analysis.json", json.dumps(a, ensure_ascii=False, indent=2))
    _log(quiet, f"[1/6] import: {a['stats'].get('import')}")
    # 1a 포즈 정규화(rest_pose=t): 팔이 많이 내려가 있으면 **재기 전에** 수평으로 펴서 다시 잰다.
    # 팔이 몸에 붙어 있으면 관절 찾기가 흔들린다(실측: 팔 75° 손 22.6cm, 90° 46.2cm 오차에 발목 검출 실패로 거절)
    want_rest = rest_pose or cfg["rig"].get("rest_pose", "keep")
    norm = None
    if want_rest == "t" and preset == "humanoid":
        r.state("normalize_pose", "running")
        # 50° 이상에서만 미리 편다: 45° 정도는 fit_generate 의 정규화(정확히 맞춘 메타리그를 쓴다)가 더 낫다(2.62 vs 2.96cm)
        norm = r.blender("normalize_pose", {"mesh": mesh, "out": str(r.dir / "00_normalized.glb"), "facing": facing,
                                            "landmarks": a["landmarks"], "threshold_deg": 50.0})
        if norm.get("applied"):
            mesh = norm["out"]; facing = "neg-y"   # 이미 정규화된 방향으로 나왔다
            a = r.blender("analyze", {"mesh": mesh, "blend": str(r.dir / "01_analyzed.blend"), "facing": facing, "preset": preset})
            atomic_write(r.dir / "analysis.json", json.dumps(a, ensure_ascii=False, indent=2))
            _log(quiet, T(f"[1/6] 포즈 정규화: 팔 {norm['angles_deg']}° → 수평으로 펴고 다시 분석", f"[1/6] pose: arms at {norm['angles_deg']}° → straightened to horizontal, analysed again"))
        else:
            _log(quiet, T(f"[1/6] 포즈 정규화: 팔 {norm.get('angles_deg')}° — 이미 수평에 가까워 손대지 않는다", f"[1/6] pose: arms at {norm.get('angles_deg')}° — already near horizontal, left as is"))
    if a["landmarks"].get("suspect"):
        _log(quiet, T(f"  ⚠ 분석을 믿기 어렵다: {'; '.join(a['landmarks']['suspect'])} → 결과가 나쁘면 `--pin 본=x,y,z` 로 관절을 직접 고정하고 재시도하라",
                      f"  ⚠ analysis is doubtful: {'; '.join(a['landmarks']['suspect'])} → if the result is bad, pin joints with `--pin bone=x,y,z` and retry"))
    _log(quiet, T(f"[1/6] analyze: 정점 {a['stats']['verts']:,} · 높이 {a['landmarks']['height']}m · 조각 {a['stats']['loose_parts']} · 비매니폴드 {a['stats']['nonmanifold_edges']} · 대칭 오차 {a['landmarks']['symmetry_error']} · 포즈 {a['landmarks']['pose_guess']}",
                    f"[1/6] analyze: verts {a['stats']['verts']:,} · height {a['landmarks']['height']}m · parts {a['stats']['loose_parts']} · non-manifold {a['stats']['nonmanifold_edges']} · symmetry error {a['landmarks']['symmetry_error']} · pose {a['landmarks']['pose_guess']}"))
    # 1b 거절 게이트: 모델을 부르기 전에 이 메시가 이 프리셋에 맞는지 본다.
    # 여기서 막으면 토큰이 0 이다(리그 1건 입력 8만 토큰). --force 로 넘길 수 있다
    block, warn = ([], []) if (from_skeleton or from_shape) else preflight(a["landmarks"], a["stats"], preset, cfg["gates"])
    if from_skeleton:
        warn.append(T("--from-skeleton: 관절을 원본 뼈대에서 그대로 받는다 — 실루엣 기반 거절 게이트는 건너뛴다",
                       "--from-skeleton: joints come straight from the source skeleton — the silhouette rejection gate is skipped"))
    if from_shape:
        warn.append(T("--from-shape: 메시 모양에서 뼈대를 만든다 — 해부학적 관절이 아니라 모양을 따라가는 조작 장치다. 렌더를 꼭 확인하라",
                       "--from-shape: the skeleton follows the mesh shape — controls, not anatomical joints. Check the renders"))
    for w in warn:
        _log(quiet, f"  ⚠ {w}")
    if block and not force:
        r.state("preflight", "rejected", reasons=block)
        # 파일에 원본 뼈대가 있으면 그게 가장 나은 탈출구다 — 추정할 필요 없이 관절을 그대로 받으면 된다
        hint = (T("\n  이 파일에는 원본 뼈대가 있다 → `--from-skeleton` 으로 관절을 그대로 받아라(토큰 0, 실루엣 추정 없음)",
                  "\n  this file carries its own skeleton → use `--from-skeleton` to take its joints as they are (0 tokens, no silhouette guessing)")
                if (a["stats"].get("import") or {}).get("had_armature") else "")
        # 손으로 고칠 출발점을 남긴다: 메타리그를 이 메시 크기로 맞춘 목표표. 거절된 메시도 사람이 관절만 옮기면 리깅된다(토큰 0)
        try:
            meta = r.blender("metarig_dump", {"preset": preset, "height": a["landmarks"]["height"], "ground_z": a["landmarks"]["ground_z"]})
            draft = meta["bones"]
            try:   # 메타리그 기본값보다, 메시에서 잰 것(어깨 높이·팔다리 중심선)을 반영한 결정적 추정이 출발점으로 낫다
                from .mock import mock_backend
                guess = mock_backend("fit", "", {"analysis.json": json.dumps({"stats": a["stats"], "landmarks": a["landmarks"], "bands": a["bands"][::2]}, ensure_ascii=False),
                                                 "metarig_bones.json": json.dumps(meta["bones"], ensure_ascii=False)})
                draft = {**draft, **{t["name"]: {"head": t["head"], "tail": t["tail"]} for t in guess["targets"]}}
                # 다리 중심선을 못 찾은 메시라도 바닥 띠에서 두 발 위치는 잰다(로봇 x 0.08 → 0.635, 정답 0.641).
                # 이 값은 초안에만 쓴다 — 결정적 추정기(벤치 기준선)는 건드리지 않는다
                fs = a["landmarks"].get("foot_split") or {}
                if fs.get("x"):
                    gz = a["landmarks"]["ground_z"]
                    az = fs.get("ankle_z", fs.get("top_z", gz)); hz = fs.get("hip_z") or a["landmarks"]["hip_z"]
                    kz = fs.get("knee_z") or az + (hz - az) * 0.5
                    for side, sg in (("L", 1), ("R", -1)):
                        lx = sg * fs["x"]
                        draft[f"thigh.{side}"] = {"head": [lx, 0.0, round(hz, 3)], "tail": [lx, 0.0, round(kz, 3)]}
                        draft[f"shin.{side}"] = {"head": [lx, 0.0, round(kz, 3)], "tail": [lx, 0.0, round(az, 3)]}
                        draft[f"foot.{side}"] = {"head": [lx, 0.0, round(az, 3)], "tail": [lx, -0.12, round(gz + 0.02, 3)]}
            except Exception:
                pass   # 추정이 실패해도 메타리그 기본값은 남긴다
            atomic_write(r.dir / "targets_draft.json", json.dumps(draft, ensure_ascii=False, indent=2))
            hint += T(f"\n  손으로 고칠 출발점을 남겼다: {r.dir / 'targets_draft.json'} (메타리그를 이 메시 크기로 맞춘 것)"
                      f"\n  관절을 옮긴 뒤 `bw rig {_arg(mesh, root)} --targets {_arg(r.dir / 'targets_draft.json', root)}` 로 돌리면 토큰 0 이다",
                      f"\n  a starting point to edit by hand: {r.dir / 'targets_draft.json'} (the metarig scaled to this mesh)"
                      f"\n  move the joints, then `bw rig {_arg(mesh, root)} --targets {_arg(r.dir / 'targets_draft.json', root)}` costs 0 tokens")
        except Exception as e:   # 초안은 부가 기능이다 — 실패해도 거절 이유는 그대로 알린다
            hint += T(f"\n  (목표표 초안을 만들지 못했다: {e})", f"\n  (could not write the targets draft: {e})")
        raise Blocked(T(f"이 메시는 {preset} 프리셋에 맞지 않는다(토큰 0 으로 중단):", f"this mesh does not fit the {preset} preset (stopped, 0 tokens):") +
                      "\n  - " + "\n  - ".join(block) + hint +
                      T("\n  그래도 추정으로 돌리려면 --force", "\n  to rig it anyway on a guess, add --force"))
    if block:
        _log(quiet, T("  ⚠ --force: 거절 사유를 무시하고 진행한다 — ", "  ⚠ --force: going ahead despite the rejection — ") + "; ".join(block))

    # 2 맞춤 판단(모델). --targets / --from-skeleton 이면 모델을 부르지 않는다(토큰 0)
    r.state("fit", "running")
    pins = dict(pins or {})
    source_symmetry = 0.0; source_leak = None
    gen_preset = preset; source_joints = None
    if from_shape:
        # 원본 뼈대가 없고 사람·개과 비율도 아닌 메시: 속 읽기가 찾은 팔다리 길을 따라 **뼈대를 직접 만든다**.
        # 해부학적 관절이 아니라 모양을 따라가는 조작 장치다 — 그 뒤는 일반 리그가 그대로 받는다
        sj = r.blender("shape_joints", {"mesh": mesh, "facing": facing, "preset": preset,
                                        "segments": cfg.get("shape", {}).get("segments", 3)})
        if not sj.get("joints"):
            r.state("fit", "rejected", reasons=[sj.get("error") or T("모양에서 뼈대를 못 만들었다", "could not build a skeleton from the shape")])
            raise Blocked("--from-shape: " + (sj.get("error") or T("메시 속에서 중심선을 못 찾았다", "found no centreline inside the mesh")))
        gen_preset = "generic"; source_joints = sj["joints"]
        fit = {"targets": {}, "reasoning": T(f"모양 리그: 속 중심선에서 팔다리 {sj['limbs']}개 · 본 {sj['bones']}개", f"shape rig: {sj['limbs']} limbs · {sj['bones']} bones from the inner centrelines"), "confidence": None}
        _log(quiet, T(f"[2/6] fit: 모양에서 뼈대를 만들었다 — 팔다리 {sj['limbs']}개 · 마디 {sj['segments']}개씩 · 본 {sj['bones']}개 · 모델 호출 0회",
                        f"[2/6] fit: skeleton built from the shape — {sj['limbs']} limbs · {sj['segments']} segments each · {sj['bones']} bones · 0 model calls"))
    elif from_skeleton:
        def _reject(why: str, reasons: list[str]) -> NoReturn:
            r.state("fit", "rejected", reasons=reasons)   # 거절도 상태로 남긴다(중간에 멈춘 실행과 구분)
            raise Blocked(why)
        gt = r.blender("gt_joints", {"mesh": mesh, "facing": facing, "preset": preset})
        if not gt.get("joints"):
            _reject(T("--from-skeleton: 이 파일에 원본 뼈대가 없다\n  → 기본 경로(--from-skeleton 없이)로 돌려라",
                      "--from-skeleton: this file has no skeleton of its own\n  → run the default route (without --from-skeleton)"), [T("뼈대 없음", "no skeleton")])
        tg, info = targets_from_skeleton(gt["joints"], preset, a["landmarks"]["height"], a["landmarks"].get("ground_z", 0.0))
        source_joints = gt["joints"]   # 메타리그 경로에서도 원작자 가중치를 자리로 옮길 수 있게 넘긴다
        source_leak = (gt.get("source_leak") or {}).get("ratio")   # 원작자 자신의 팔→몸통 누수(보정용)
        # 사람·개과 메타리그에 맞출 수 없는 몸(용·유령·문어·블롭)은 거절하는 대신 **원본 뼈대를 그대로 베낀
        # 일반 리그**로 간다. 관절 이름을 못 알아봐도, 팔다리가 없어도, 사슬이면 컨트롤을 만들 수 있다
        if info["limbs_absent"] or len(tg) < 6:
            why = (T("팔다리 없음: ", "no limbs: ") + ", ".join(info["limbs_absent"])) if info["limbs_absent"] \
                else T(f"알아본 관절 {len(tg)}개", f"{len(tg)} joints recognised")
            gen_preset = "generic"; source_joints = gt["joints"]
            fit = {"targets": {}, "reasoning": T(f"일반 리그: 원본 뼈대 {len(gt['joints'])}본을 그대로 베낌({why})", f"generic rig: copied the {len(gt['joints'])} source bones as they are ({why})"), "confidence": None}
            _log(quiet, T(f"[2/6] fit: 사람·개과 메타리그에 못 맞춘다({why}) → **일반 리그**로 간다 · 원본 본 {len(gt['joints'])}개 · 모델 호출 0회",
                            f"[2/6] fit: does not fit the human or canine metarig ({why}) → **generic rig** · {len(gt['joints'])} source bones · 0 model calls"))
        else:
            fit = {"targets": tg, "reasoning": T(f"원본 뼈대 {info['bones']}본에서 가져옴: {', '.join(info['matched'])}", f"taken from the {info['bones']} source bones: {', '.join(info['matched'])}"), "confidence": None}
        source_symmetry = info.get("source_symmetry", 0.0)
        if gen_preset == "generic":
            source_symmetry = 0.0
        else:
            _log(quiet, T(f"[2/6] fit: 원본 뼈대에서 목표 {len(tg)}개 · 모델 호출 0회 · 못 찾은 관절 {info['missing']}",
                   f"[2/6] fit: {len(tg)} targets from the source skeleton · 0 model calls · joints not found {info['missing']}") +
                 (T(f" · 한쪽만 있어 비춰 채운 본 {info['mirrored']}", f" · mirrored from the other side {info['mirrored']}") if info["mirrored"] else "") +
                 (T(f" · 원본 좌우 어긋남 {source_symmetry}m(이만큼은 우리 오차가 아니다)", f" · source left/right mismatch {source_symmetry}m (not our error)") if source_symmetry > 0.01 else ""))
    elif targets_file:
        fit = {"targets": targets_loaded, "reasoning": T(f"재사용: {targets_file}", f"reused: {targets_file}"), "confidence": None}
        _log(quiet, T(f"[2/6] fit: 파일 재사용 {targets_file} · 목표 본 {len(fit['targets'])}개 · 모델 호출 0회",
                        f"[2/6] fit: reusing {targets_file} · {len(fit['targets'])} target bones · 0 model calls"))
    else:
        meta = r.blender("metarig_dump", {"preset": preset, "height": a["landmarks"]["height"], "ground_z": a["landmarks"]["ground_z"]})
        inputs = {"analysis.json": json.dumps({"stats": a["stats"], "landmarks": a["landmarks"], "bands": a["bands"][::2]}, ensure_ascii=False),
                  "metarig_bones.json": json.dumps(meta["bones"], ensure_ascii=False)}
        if pins:
            inputs["pins.json"] = json.dumps(pins, ensure_ascii=False)
        fit = r.call("fit", "fit", inputs, schemas.FIT)
        fit["targets"] = {t["name"]: {"head": t["head"], "tail": t["tail"]} for t in fit["targets"]}   # 배열 → 이름별 dict
        # **모델이 빼고 답한 본은 결정적 배치로 메운다.** 모델이 자신 없는 본을 빼는 건 옳은 행동이지만
        # (실측: "다리 중심선이 z=0.098 까지만 와서 발목을 확인할 수 없어 shin·foot 을 제외했다"),
        # 그러면 그 본이 **메타리그 기본값 그대로** 남아 몸에서 한참 벗어난다.
        # mannequiny 실측 — 모델만: 평균 5.96cm(발 24.71cm) · 메우면: 평균 3.21cm(발 6.67cm).
        # 메우는 값은 `mock` 백엔드와 같은 함수, 즉 랜드마크에서 기계적으로 계산한 자리다(토큰 0).
        fit["targets"], filled = fill_missing_targets(fit["targets"], inputs)
        fit["filled_from_landmarks"] = filled
        _log(quiet, T(f"[2/6] fit: 목표 본 {len(fit['targets'])}개 · 확신 {fit.get('confidence')}", f"[2/6] fit: {len(fit['targets'])} target bones · confidence {fit.get('confidence')}")
                    + (T(f" · 모델이 뺀 {len(filled)}개는 랜드마크로 메움({', '.join(filled)})", f" · {len(filled)} the model left out, filled from landmarks ({', '.join(filled)})") if filled else ""))
    for name, v in pins.items():   # 사용자가 고정한 관절이 최종 결정권을 갖는다
        fit["targets"].setdefault(name, {}).update(v)
    if pins:
        _log(quiet, T(f"  📌 고정된 관절 {len(pins)}개: {', '.join(sorted(pins))}", f"  📌 {len(pins)} pinned joints: {', '.join(sorted(pins))}"))
    atomic_write(r.dir / "fit.json", json.dumps(fit, ensure_ascii=False, indent=2))
    atomic_write(r.dir / "targets.json", json.dumps(fit["targets"], ensure_ascii=False, indent=2))   # 손으로 고쳐 --targets 로 재사용
    # 3 생성·스키닝·통계
    r.state("generate", "running")
    g = r.blender("fit_generate", {"blend": str(r.dir / "01_analyzed.blend"), "out_blend": str(r.dir / "02_rigged.blend"), "preset": gen_preset,
                                   "source_joints": source_joints,
                                   # 원본이 좌우 대칭인 뼈대면 우리 결과도 대칭이어야 한다(보정이 만든 어긋남은 되돌린다)
                                   "source_symmetric": bool(from_skeleton and source_symmetry <= a["landmarks"]["height"] * 0.005),
                                   "targets": fit["targets"], "landmarks": a["landmarks"], "stats": a["stats"], "face": cfg["rig"]["face"], "pinned": sorted(pins),
                                   # 이미 메시를 T 로 펴 놨으면 fit_generate 에서 또 펴지 않는다
                                   "rest_pose": "keep" if (norm and norm.get("applied")) else want_rest,
                                   "weight_method": weights or cfg["rig"].get("weights", "auto"),
                                   "cross_trim": cfg["rig"].get("cross_trim", True),
                                   "from_skeleton": bool(from_skeleton),
                                   # 사람 메타리그를 사람 아닌 비율(로봇)에 씌울 때만 살집 보조 본도 부모 척추를 따라가게 한다.
                                   # 사족은 메타리그가 이미 네발짐승이라 기본 자리가 맞고, 따라가게 하면 오히려 몸 밖으로 나간다(말·늑대로 확인)
                                   "propagate_helpers": from_skeleton and gen_preset == "humanoid"})
    g["preset"] = preset   # bw motion 이 리그의 프리셋을 스스로 알도록 남긴다
    if norm:
        g["stats"]["normalize_pose"] = norm
    atomic_write(r.dir / "rig_stats.json", json.dumps(g, ensure_ascii=False, indent=2))
    st = g["stats"]
    _log(quiet, T(f"[3/6] generate: 리그 본 {st['rig_bones']} (변형 {st['deform_bones']}) · 가중치 없는 정점 {st['unweighted_verts']}(가까운 본으로 메운 {st.get('filled_unweighted', 0)}) · 상자 밖 {len(st['bones_outside_bbox'])}",
                    f"[3/6] generate: rig bones {st['rig_bones']} (deform {st['deform_bones']}) · unweighted verts {st['unweighted_verts']} ({st.get('filled_unweighted', 0)} filled from the nearest bone) · outside bbox {len(st['bones_outside_bbox'])}"))
    # 4 게이트
    fails = rig_gates(st, cfg["gates"], a["stats"]["verts"], source_symmetry, source_leak)
    _log(quiet, f"[4/6] gates: {T('통과', 'pass') if not fails else fails}")
    # 5 렌더 — `BW_NO_RENDER=1` 이면 건너뛴다.
    # 렌더는 **사람이 눈으로 보라고** 만드는 것이지 정확성 판정이 아니다(게이트는 위에서 이미 끝났다).
    # 화면 없는 CI 서버에서는 렌더러가 죽어 버려서(종료코드 -6), 이게 없으면 리깅이 멀쩡히 돌았는데도
    # 테스트가 통째로 실패한다. 시각 판정(judge)은 그림이 필요하므로 이때 함께 꺼진다.
    if os.environ.get("BW_NO_RENDER") == "1":
        views = {"images": [], "bone_proxies": 0, "skipped": "BW_NO_RENDER"}
        no_judge = True
        _log(quiet, T("[5/6] render: 건너뜀(BW_NO_RENDER=1) — 시각 판정도 함께 꺼진다", "[5/6] render: skipped (BW_NO_RENDER=1) — the visual judge is off too"))
    else:
        r.state("render", "running")
        views = r.blender("render_views", {"blend": str(r.dir / "02_rigged.blend"), "out_dir": str(r.dir), "stats": a["stats"], "size": cfg["render"]["size"]})
        _log(quiet, T(f"[5/6] render: {len(views['images'])}장 · 본 기둥 {views['bone_proxies']}", f"[5/6] render: {len(views['images'])} images · bone proxies {views['bone_proxies']}"))
    # 6 시각 판정(모델)
    judge = {"skipped": True}
    if not no_judge:
        r.state("judge", "running")
        imgs = [p for p in views["images"] if any(v in p for v in cfg["render"]["judge_views"])]
        judge = r.call("judge", "judge", {"context.txt": f"preset={preset}; height={a['landmarks']['height']}m; deform_bones={st['deform_bones']}"}, schemas.JUDGE, images=imgs)
        fails += judge_gates(judge)
        _log(quiet, T(f"[6/6] judge: 밖 {judge['bones_outside_mesh']} · 비율 {'ok' if judge['proportions_ok'] else '이상'} · 확신 {judge['confidence']}",
                          f"[6/6] judge: outside {judge['bones_outside_mesh']} · proportions {'ok' if judge['proportions_ok'] else 'off'} · confidence {judge['confidence']}"))
    # 보고서
    t = r.tokens(); status = "ok" if not fails else "needs_review"
    report = [f"# bonewright rig report · {run_id}", "", versions_line(a),
              f"- mesh: `{_shown(mesh, r.dir)}` · preset: {preset} · verts {a['stats']['verts']:,} · height {a['landmarks']['height']} m",
              f"- import: {json.dumps(a['stats'].get('import'), ensure_ascii=False)}",
              f"- landmarks: chibi={a['landmarks'].get('chibi')} · head_ratio={a['landmarks'].get('head_ratio')} · neck={a['landmarks'].get('neck_from')} · suspect={a['landmarks'].get('suspect')}",
              f"- rig: `{_shown(g['blend'], r.dir)}` · bones {st['rig_bones']} (deform {st['deform_bones']}) · moved metarig bones {len(st['moved_bones'])}",
              f"- weights ({st.get('weight_method')}): unweighted {st['unweighted_verts']} (filled by nearest bone {st.get('filled_unweighted', 0)}"
              + (f", rigid parts bound whole {st['rigid_islands_bound']}" if st.get("rigid_islands_bound") else "")
              + f") · sum {st['weight_sum_min']}–{st['weight_sum_max']} · symmetry err {st['symmetry_max_error']}",
              f"- gates: {'PASS' if not fails else 'FAIL: ' + '; '.join(fails)}" +
              (T(f" · ⚠ 조각 사이 빈틈을 지나는 본 {st['deform_gap_mesh']}: {st.get('deform_gap_mesh_bones', [])[:4]}",
                 f" · ⚠ bones crossing gaps between parts {st['deform_gap_mesh']}: {st.get('deform_gap_mesh_bones', [])[:4]}") if st.get("deform_gap_mesh") else ""),
              f"- judge: {json.dumps(judge, ensure_ascii=False)}",
              f"- renders: {', '.join(Path(p).name for p in views['images'])}",
              f"- targets: `runs/{run_id}/targets.json` " + T(f"(손으로 고쳐 `bw rig {_arg(mesh, root)} --targets runs/{run_id}/targets.json` 로 토큰 0 재실행)", f"(edit by hand and rerun with `bw rig {_arg(mesh, root)} --targets runs/{run_id}/targets.json`, 0 tokens)")
              + (T(f" · 고정 {sorted(pins)}", f" · pinned {sorted(pins)}") if pins else ""),
              f"- tokens: in {t['input']:,} / out {t['output']:,} · ≈${t['usd_upper']} upper · calls {len(r.usage)}", ""]
    atomic_write(r.dir / "report.md", "\n".join(report))
    r.state("final", status)
    _log(quiet, T(f"완료({status}) → {r.dir / 'report.md'}", f"done ({status}) → {r.dir / 'report.md'}"))
    return r.dir / "report.md"


def kimodo_paths(kroot: Path, k: dict) -> tuple[Path | None, Path | None]:
    """kimodo.cpp 의 생성기와 텍스트 인코더를 찾는다. 못 찾으면 None.

    생성기: 옛 빌드(`build-release/`)와 지금 원본의 `cmake --preset release`(`build/release/`) 둘 다 본다.
    텍스트 인코더: 설정값(`kimodo.text_bundle`, 기본은 옛 구성품 폴더)이 있으면 그것, 없으면 지금 원본의
    `download_gguf_weights.sh` 가 까는 GGUF 한 파일(옆에 `tokenizer.gguf`, 여럿이면 Q8_0 우선)."""
    gen = next((p for d in ("build-release", "build/release") for name in ("kmd-generate", "kmd-generate.exe")
                if (p := kroot / d / name).is_file()), None)
    text = kroot / k["text_bundle"]
    if not text.exists():
        mono = sorted((p for p in kroot.rglob("*.gguf") if p.name != "tokenizer.gguf" and (p.parent / "tokenizer.gguf").is_file()),
                      key=lambda p: ("q8_0" not in p.name.lower(), str(p)))
        text = mono[0] if mono else None
    return gen, text


def motion(root: Path, text: str | None = None, bvh: str | None = None, run_id: str | None = None, quiet: bool = False,
           rig_run: str | None = None, export: str | None = None, roll: bool = True, preset: str | None = None, bvh_up: str = "y", legs: str = "auto", bone_map: str | None = None) -> Path:
    """텍스트 → kimodo.cpp(Metal) → BVH → Blender 가져오기 → (rig_run 이 있으면) 그 리그에 리타겟 → (export 면) 변형 본만 든 GLB. 토큰 0."""
    cfg = load(root)
    # 입력 확인은 실행 폴더·Blender 전에: 잘못된 --rig·--bvh 로 기존 실행 기록을 덮지 않는다
    if not text and not bvh:
        bv = sample_bvh()   # 그대로 붙여 넣어 도는 BVH(저장소의 손 흔들기)
        raise Blocked(T(f"동작 출처가 없다\n  → `bw motion --bvh {bv} --rig <리그 run-id>`(리그 id 는 `bw status`) 또는 `bw motion --text \"a person walks\"`",
                        f"no motion source\n  → `bw motion --bvh {bv} --rig <rig run-id>` (rig ids: `bw status`) or `bw motion --text \"a person walks\"`"))
    if bvh and not text:
        bv = sample_bvh()
        need_bvh_bytes(need_file(bvh, "BVH", T(f"경로를 확인하라. 저장소의 샘플: `--bvh {bv}`, 그 밖엔 Mixamo·CMU 등에서 받거나 `--text` 로 만든다",
                                f"check the path. The repository's sample: `--bvh {bv}`; otherwise get one from Mixamo, CMU etc., or make one with `--text`"), (".bvh",)))
    if not rig_run:   # 리타겟 옵션은 `if rig_run:` 안에서만 쓰인다 — 말없이 버리면 기다린 끝에 GLB 가 없다
        unused = [f for f, on in (("--export", export), ("--map", bone_map), (f"--legs {legs}", legs != "auto"), ("--no-roll", not roll)) if on]
        if unused:
            raise Blocked(T(f"{' · '.join(unused)} 는 리그에 옮길 때만 쓴다\n  → `--rig <리그 run-id>` 를 함께 주거나(목록은 `bw status`) 그 옵션을 빼라",
                            f"{' · '.join(unused)} only apply when retargeting onto a rig\n  → add `--rig <rig run-id>` (list runs with `bw status`), or drop the option"))
    rig_blend = need_rig(root, rig_run, "--rig {}") if rig_run else None
    user_map = load_bone_map(bone_map) if bone_map else None
    run_id = run_id or time.strftime("motion-%Y%m%d-%H%M%S")
    k = cfg["kimodo"]; kroot = (root / k["root"]).resolve()
    if text:   # kimodo 도 실행 폴더·Blender 전에 본다(설치 안내가 더 구체적이다)
        gen, text_model = kimodo_paths(kroot, k)
        if gen is None:
            raise Blocked(T(f"kimodo.cpp 빌드가 없다: {kroot}/build/release/kmd-generate\n  → docs/GUIDE.md 의 \"Text → motion: building kimodo.cpp\" 절대로 빌드하거나, 텍스트 대신 `--bvh 파일` 을 써라",
                            f"kimodo.cpp is not built: {kroot}/build/release/kmd-generate\n  → build it as in \"Text → motion: building kimodo.cpp\" in docs/GUIDE.md, or use `--bvh file` instead of text"))
        if text_model is None:
            raise Blocked(T(f"kimodo.cpp 텍스트 인코더가 없다: {kroot / k['text_bundle']} 도, `tokenizer.gguf` 옆의 GGUF 도 없다\n"
                            "  → `scripts/download_gguf_weights.sh --output \"$PWD\" --model soma-rp-v1.1` 로 받거나, runs/config.json 의 kimodo.text_bundle 에 경로를 적어라",
                            f"kimodo.cpp text encoder not found: neither {kroot / k['text_bundle']} nor a GGUF beside `tokenizer.gguf`\n"
                            "  → get it with `scripts/download_gguf_weights.sh --output \"$PWD\" --model soma-rp-v1.1`, or set kimodo.text_bundle in runs/config.json"))
    need_blender(cfg["blender"])   # 실행 폴더를 만들기 전에
    r = Run(root, run_id, cfg, quiet)
    # 단계 번호는 실제로 도는 단계만 센다: `--bvh` 만이면 [1/1] 로 시작한다(10/10 까지 [3/3] 부터라 앞 단계가 빠진 줄 알았다)
    steps = (["kimodo", "bvh"] if text else []) + ["import"] + (["retarget"] if rig_run else []) + (["export"] if rig_run and export else [])
    def n(step: str) -> str:
        return f"[{steps.index(step) + 1}/{len(steps)}]"
    if text:
        r.state("kimodo", "running")
        (r.dir / "prompt.txt").write_text(text, encoding="utf-8")
        t = time.time()
        proc = subprocess.run([str(gen), str(kroot / k["model"]), str(text_model), str(r.dir / "prompt.txt"),
                               str(k["frames"]), str(k["steps"]), str(k["seed"]), str(r.dir / "motion")], capture_output=True, text=True)
        (r.logs).mkdir(exist_ok=True); (r.logs / "kimodo.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            r.state("kimodo", "failed"); raise Blocked(T("kimodo 실패: ", "kimodo failed: ") + proc.stderr[-500:])
        _log(quiet, f"{n('kimodo')} kimodo: {proc.stdout.strip()} · {time.time() - t:.1f}s")
        bvh = str(r.dir / "motion" / "motion.bvh")
        proc = subprocess.run([sys.executable, str(kroot / "scripts" / "export_bvh.py"), "--motion-dir", str(r.dir / "motion"), "--output", bvh, "--fps", "30", "--scale", "1.0"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise Blocked(T("BVH 변환 실패: ", "BVH conversion failed: ") + proc.stderr[-500:])
        _log(quiet, f"{n('bvh')} bvh: {bvh}")
    r.state("import", "running")
    from .retarget import detect_bvh_up
    if rig_run and preset is None:   # 리그 실행 기록에서 프리셋을 읽는다(없는 옛 실행은 humanoid). 위 축 판단에도 필요하다
        rs = root / "runs" / rig_run / "rig_stats.json"
        preset = (json.loads(rs.read_text()).get("preset") if rs.exists() else None) or "humanoid"
    if bvh_up == "auto":   # 위 축을 틀리면 조용히 망가진다(늑대 걷기: 발이 바닥에서 1m 뜸) → 머리·발 위치로 정한다
        bvh_up = detect_bvh_up(str(Path(bvh).resolve()), preset or "humanoid")
        _log(quiet, T(f"{n('import')} bvh 위 축 자동 판단: {bvh_up} (틀리면 --bvh-up 으로 직접 지정)", f"{n('import')} bvh up axis detected: {bvh_up} (if wrong, set it with --bvh-up)"))
    imp = r.blender("import_bvh", {"bvh": str(Path(bvh).resolve()), "out_blend": str(r.dir / "motion.blend"), "bvh_up": bvh_up})
    _log(quiet, T(f"{n('import')} import: 본 {imp['bones']} · 프레임 {imp['frames']} · {imp['fps']}fps · 루트 이동 {imp['root_move']}m",
                    f"{n('import')} import: bones {imp['bones']} · frames {imp['frames']} · {imp['fps']}fps · root move {imp['root_move']}m"))
    report = [f"# bonewright motion report · {run_id}", "", versions_line(imp), f"- source: {'text: ' + text if text else 'bvh: ' + _shown(bvh, r.dir)}",
              f"- armature: {imp['armature']} · bones {imp['bones']} · frames {imp['frames']} · fps {imp['fps']} · root move {imp['root_move']} m",
              "- blend: `motion.blend`"]
    if rig_run:
        from .retarget import bvh_mapping
        blend = rig_blend
        mapping = bvh_mapping(imp["bone_names"], preset)
        if bone_map:
            mapping, applied, unknown = apply_bone_map(mapping, user_map, imp["bone_names"])
            _log(quiet, T(f"  📄 --map {applied}개 적용", f"  📄 --map applied {applied}")
                        + (T(f" · BVH 에 없는 이름 {len(unknown)}개 무시: {', '.join(unknown[:4])}", f" · ignored {len(unknown)} names not in the BVH: {', '.join(unknown[:4])}") if unknown else ""))
        r.state("retarget", "running")
        fa, fb = imp["frames"] if imp.get("frames") else (1, 1)
        rf = sorted({fa, fa + (fb - fa) // 3, fa + 2 * (fb - fa) // 3, fb})
        an = json.loads((root / "runs" / rig_run / "analysis.json").read_text()) if (root / "runs" / rig_run / "analysis.json").exists() else {}
        rt = r.blender("retarget_bvh", {"blend": str(blend), "bvh": str(Path(bvh).resolve()), "mapping": mapping,
                                        "out_blend": str(r.dir / "retargeted.blend"), "out_dir": str(r.dir),
                                        "render_frames": rf, "height": (an.get("landmarks") or {}).get("height", 1.8), "roll": roll, "bvh_up": bvh_up, "legs": legs})
        _log(quiet, T(f"{n('retarget')} retarget: 본 {len(rt['mapped'])}개 옮김 · 못 옮긴 BVH 본 {len(rt['unmapped'])}개 · "
                      f"본 방향 오차 평균 {rt.get('mean_dir_deg')}° · 손발 위치 오차 평균 {rt.get('mean_end_cm')}cm(비율 차이 포함)",
                      f"{n('retarget')} retarget: {len(rt['mapped'])} bones moved · {len(rt['unmapped'])} BVH bones not moved · "
                      f"mean bone direction error {rt.get('mean_dir_deg')}° · mean hand/foot position error {rt.get('mean_end_cm')}cm (includes proportion difference)"))
        report += [f"- retarget → `{rig_run}`: mapped {len(rt['mapped'])} bones, unmapped {rt['unmapped']}",
                   f"- legs: {rt.get('legs')} · IK {rt.get('ik_legs') or []} · FK(no foot joint in source) {rt.get('ik_skipped') or []} · roll transfer: {rt.get('roll')} · hand/foot twist error vs BVH: " + ", ".join(f"{k} {v['mean_deg']}°(max {v['max_deg']})" for k, v in (rt.get('roll_deg') or {}).items()),
                   f"- bone direction error vs BVH (proportion-free): mean {rt.get('mean_dir_deg')}° · " +
                   ", ".join(f"{k} {v['mean_deg']}°(max {v['max_deg']}, rest offset {v['rest_deg']})" for k, v in (rt.get('dir_deg') or {}).items()),
                   f"- end-effector error vs BVH (hips-relative, scaled {rt['scale']}, proportion-limited): mean {rt.get('mean_end_cm')} cm · " +
                   ", ".join(f"{k} {v['mean_cm']}cm(max {v['max_cm']})" for k, v in (rt.get('end_cm') or {}).items()),
                   f"- foot contact (lowest toe per frame): {rt.get('foot_contact')}",
                   f"- foot slide during BVH stance frames: {rt.get('foot_slide')}",
                   f"- deformation (edge stretch vs rest at rendered frames): {rt.get('stretch') and {k: v for k, v in rt['stretch'].items() if k != 'per_frame'}}",
                   "- blend: `retargeted.blend`",
                   "- frames: " + " ".join(f"`{Path(p).name}`" for p in rt.get("renders", []))]
        atomic_write(r.dir / "retarget.json", json.dumps(rt, ensure_ascii=False, indent=2))
        if export:
            out = (r.dir / "animated.glb") if export == "auto" else Path(export).resolve()
            r.state("export", "running")
            ex = r.blender("export_anim", {"blend": str(r.dir / "retargeted.blend"), "out": str(out)})
            _log(quiet, T(f"{n('export')} export: {out.name} · 본 {ex['bones']} · 프레임 {ex['frames']} · 다시 읽어 손발 위치 차이 최대 {ex['max_diff_cm']}cm",
                              f"{n('export')} export: {out.name} · bones {ex['bones']} · frames {ex['frames']} · re-read hand/foot max difference {ex['max_diff_cm']}cm"))
            report += [f"- export: `{_shown(out, r.dir)}` · {ex['bones']} deform bones · {ex['verts']} verts · frames {ex['frames']} · "
                       f"re-import check at frame {ex['probe_frame']}: {ex['reimport_diff_cm']} (cm)"]
    else:
        report.append("- retarget: pass --rig <run-id> to move this motion onto a rig")
    report.append("")
    atomic_write(r.dir / "report.md", "\n".join(report)); r.state("final", "ok")
    _log(quiet, T(f"완료 → {r.dir / 'report.md'}", f"done → {r.dir / 'report.md'}"))
    return r.dir / "report.md"


def export_rig(root: Path, run_id: str, out: str | None = None, quiet: bool = False) -> Path:
    """리깅 결과 → 변형 본만 든 GLB(토큰 0). 다시 읽어 본 위치를 대조한다."""
    cfg = load(root)
    blend = need_rig(root, run_id, "bw export {}")
    dst = None
    if out:   # Blender 를 띄우기 전에(10/10 8회차: 폴더·.fbx 가 Blender 단계에서야 실패했다)
        dst = Path(out).expanduser()
        if dst.is_dir():
            dst = dst / f"{run_id}.glb"   # 폴더를 주면 그 안에 <id>.glb
        elif dst.suffix.lower() != ".glb":
            raise Blocked(T(f"내보내기는 GLB 만 쓴다: {out}\n  → `--out {Path(out).with_suffix('.glb')}` 처럼 .glb 로, 또는 폴더를 준다(그 안에 {run_id}.glb)",
                            f"export writes GLB only: {out}\n  → use a .glb path such as `--out {Path(out).with_suffix('.glb')}`, or a folder (it gets {run_id}.glb)"))
        if not dst.parent.is_dir():
            raise Blocked(T(f"출력 폴더가 없다: {dst.parent}\n  → 먼저 만들거나(`mkdir -p {dst.parent}`) 있는 폴더를 준다",
                            f"output folder does not exist: {dst.parent}\n  → create it first (`mkdir -p {dst.parent}`) or pass an existing one"))
        dst = dst.resolve()
    need_blender(cfg["blender"])   # 실행 폴더를 만들기 전에
    r = Run(root, run_id, cfg, quiet, state_file="export_state.json")
    dst = dst or (r.dir / "rigged.glb")
    ex = r.blender("export_rig", {"blend": str(blend), "out": str(dst)})
    _log(quiet, T(f"export: {dst} · 변형 본 {ex['bones']} · 정점 {ex['verts']}/{ex['verts_in_source']} · 다시 읽어 본 위치 차이 최대 {ex['max_diff_cm']}cm",
                    f"export: {dst} · deform bones {ex['bones']} · verts {ex['verts']}/{ex['verts_in_source']} · re-read bone max difference {ex['max_diff_cm']}cm"))
    atomic_write(r.dir / "export.json", json.dumps(ex, ensure_ascii=False, indent=2))
    return dst


def ffmpeg_install(system: str | None = None) -> str:
    """이 OS 에서 ffmpeg 를 까는 명령 하나(10/10 8회차: 한국어판은 macOS 의 brew 만, 영어판은 "install ffmpeg" 뿐이었다)."""
    import platform
    system = system or platform.system()
    return {"Darwin": "`brew install ffmpeg`", "Windows": "`winget install ffmpeg`"}.get(system, "`sudo apt install ffmpeg`")


def demo(root: Path, run_id: str, quiet: bool = False, size: int = 640, frames: int = 96) -> Path:
    """리그 결과 데모 영상(토큰 0): runs/<id>/02_rigged.blend → demo.mp4(+ ffmpeg 가 있으면 demo.gif)."""
    import shutil
    cfg = load(root)
    blend = need_rig(root, run_id, "bw demo {}")
    if os.environ.get("BW_NO_RENDER") == "1":   # Blender 확인보다 먼저: 없으면 "Blender not found" 가 진짜 이유를 가렸다
        # 데모 영상은 **그림이 목적**인 기능이라 통째로 막는다(화면 없는 서버에서는 렌더러가 죽는다)
        raise Blocked(T("BW_NO_RENDER=1 이라 데모 영상을 만들지 않는다\n  → 화면이 있는 환경에서 `BW_NO_RENDER` 를 지우고 다시 실행하라",
                        "BW_NO_RENDER=1, so no demo video is made\n  → unset `BW_NO_RENDER` and run again on a machine with a display"))
    need_blender(cfg["blender"])   # 실행 폴더를 만들기 전에
    r = Run(root, run_id, cfg, quiet, state_file="demo_state.json")
    a = json.loads((r.dir / "analysis.json").read_text(encoding="utf-8"))
    d = r.blender("render_demo", {"blend": str(blend), "out_dir": str(r.dir), "stats": a["stats"], "height": a["landmarks"]["height"], "size": size, "frames": frames})
    out = Path(d["frames_dir"])
    if shutil.which("ffmpeg"):   # PNG 연속 이미지 → mp4(H.264) → gif(12fps, 480px)
        mp4, gif = r.dir / "demo.mp4", r.dir / "demo.gif"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(d["fps"]), "-i", str(out / "f_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", str(gif)])
        out = mp4
    else:
        _log(quiet, T(f"ffmpeg 가 없어 PNG 프레임만 남긴다 → {ffmpeg_install()} 뒤 같은 명령을 다시",
                      f"no ffmpeg, so only PNG frames are kept → {ffmpeg_install()}, then run the same command again"))
    _log(quiet, T(f"demo: {out} · 프레임 {d['frames']} · 컨트롤 {d['controls']}", f"demo: {out} · frames {d['frames']} · controls {d['controls']}"))
    return out
