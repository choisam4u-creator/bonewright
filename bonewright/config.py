"""기본 설정. runs/config.json 이 있으면 덮어쓴다(중첩 병합)."""
import difflib
import json
import os
from pathlib import Path

from .i18n import lang as screen_lang

DEFAULTS = {
    "lang": "",            # 모델 프롬프트 언어(ko|en). 비우면 화면 언어(BW_LANG, 없으면 로캘)를 따른다
    "models": {"fit": {"model": "gpt-6-astra", "effort": "medium"}, "judge": {"model": "gpt-6-astra", "effort": "low"}},
    "budget": {"max_input_tokens": 600_000, "price_input_per_m": 10.0, "price_output_per_m": 50.0},
    "codex": {"timeout": 600, "ignore_user_config": True, "extra_args": ["--skip-git-repo-check", "--ephemeral"]},
    "blender": {"app": "", "timeout": 600},      # app 비우면 자동 탐색(앱이 먼저, 없으면 bpy 휠 — blender.py)
    "rig": {"face": False, "rest_pose": "keep", "weights": "auto", "cross_trim": True},   # 살을 가로지르는 본 떼기: 빈 공간을 길게 지나는 영향만 뗀다(스침은 안 뗀다)
    "render": {"size": 512, "judge_views": ["front", "side"]},
    "gates": {"max_unweighted_ratio": 0.0, "weight_sum_min": 0.98, "weight_sum_max": 1.02, "symmetry_max_error": 0.03, "max_weight_leak_ratio": 0.005, "max_deform_outside_mesh": 0,
              "deform_bones_min": 60, "max_bones_outside_bbox": 0,
              "min_height_m": 0.3, "max_height_m": 20.0, "max_symmetry_error_ratio": 0.03},
    "kimodo": {"root": "vendor/kimodo.cpp", "model": "models/kimodo-soma-rp-v1.1-f32.gguf", "text_bundle": "generated/llm2vec-text-bundle",
               "frames": 60, "steps": 50, "seed": 1},
}


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def _read_user_config(p: Path) -> dict:
    """runs/config.json 을 읽는다. 깨졌으면 '예상 못 한 오류'(이슈 신고 안내)가 아니라 고칠 자리를 짚는 Blocked."""
    from .i18n import T
    from .pipeline import Blocked   # pipeline 이 이 모듈을 import 하므로 여기서
    try:
        user = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Blocked(T(f"설정 파일이 JSON 이 아니다: {p} ({e.lineno}줄 {e.colno}칸: {e.msg})\n  → 그 자리를 고치거나(끝 쉼표·작은따옴표가 흔하다) 파일을 지우면 기본값으로 돈다",
                        f"the settings file is not valid JSON: {p} (line {e.lineno}, column {e.colno}: {e.msg})\n  → fix that spot (a trailing comma or single quotes are the usual cause), or delete the file to use the defaults")) from None
    if not isinstance(user, dict):
        raise Blocked(T(f"설정 파일은 {{...}} 객체여야 한다: {p} (지금 {type(user).__name__})\n  → 예: {{\"lang\": \"en\"}}",
                        f"the settings file must be a {{...}} object: {p} (got {type(user).__name__})\n  → for example {{\"lang\": \"en\"}}"))
    return user


def _unknown(user: dict, known: dict, prefix: str = "") -> list[str]:
    out = []
    for k, v in user.items():
        if k not in known:
            near = difflib.get_close_matches(k, list(known), n=1)
            out.append(f"{prefix}{k}" + (f" (→ {prefix}{near[0]}?)" if near else ""))
        elif isinstance(v, dict) and isinstance(known[k], dict):
            out += _unknown(v, known[k], f"{prefix}{k}.")
    return out


def unknown_keys(root: Path) -> list[str]:
    """runs/config.json 에서 기본 설정에 없는 키(대개 오타) — 조용히 무시되면 설정이 안 먹은 줄 모른다.
    파일이 없거나 깨졌으면 빈 목록(깨진 파일은 load 가 Blocked 로 짚는다)."""
    p = root / "runs" / "config.json"
    try:
        user = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return _unknown(user, DEFAULTS) if isinstance(user, dict) else []


def unknown_keys_line(root: Path) -> str | None:
    """경고 한 줄(없으면 None). 멈추지는 않는다."""
    from .i18n import T
    bad = unknown_keys(root)
    if not bad:
        return None
    p = root / "runs" / "config.json"
    return T(f"⚠ 설정 파일에 모르는 키 {len(bad)}개 — 무시하고 기본값으로 돈다: {', '.join(bad)} ({p})\n  → 이름을 고쳐라. 쓸 수 있는 키는 docs/GUIDE.md 의 \"Settings (`runs/config.json`)\"",
             f"⚠ {len(bad)} unknown key(s) in the settings file, ignored (defaults used): {', '.join(bad)} ({p})\n  → fix the name; the keys are listed under \"Settings (`runs/config.json`)\" in docs/GUIDE.md")


BACKENDS = ("codex", "mock")


def backend_problem() -> str | None:
    """BW_BACKEND 가 codex·mock 이 아니면 그 문구(아니면 None). 10/11 11회차: `Mock`·`moc` 같은 오타가 말없이
    codex(유료 모델 호출)로 돌았다 — 토큰 0 을 기대한 사용자가 돈을 쓴다."""
    from .i18n import T
    v = os.environ.get("BW_BACKEND")
    if v is None or v in BACKENDS:
        return None
    near = difflib.get_close_matches(v.strip().lower(), BACKENDS, n=1, cutoff=0.5)
    fix = f"BW_BACKEND={near[0]}" if near else "BW_BACKEND=mock"
    return T(f"BW_BACKEND={v!r} 는 모르는 값이다(codex 또는 mock). 그대로 두면 유료 모델 호출로 돌 수 있어 멈춘다\n  → `{fix}` 로 고치거나, 모델 호출이면 BW_BACKEND 를 지운다",
             f"BW_BACKEND={v!r} is not a known value (codex or mock); stopping rather than risk paid model calls\n  → set `{fix}`, or unset BW_BACKEND for model calls")


def load(root: Path, lang: str | None = None) -> dict:
    if (msg := backend_problem()):
        from .pipeline import Blocked   # pipeline 이 이 모듈을 import 하므로 여기서
        raise Blocked(msg)
    cfg = DEFAULTS
    p = root / "runs" / "config.json"
    if p.exists():
        cfg = _merge(cfg, _read_user_config(p))
    if lang:
        cfg = _merge(cfg, {"lang": lang})
    if cfg.get("lang") not in ("ko", "en"):   # --lang > runs/config.json > BW_LANG·로캘
        cfg = _merge(cfg, {"lang": screen_lang()})
    return cfg


def find_root() -> Path:
    env = os.environ.get("BW_HOME")
    if env:
        return Path(env)
    here = Path.cwd()
    for p in [here, *here.parents]:
        if (p / "bonewright").is_dir() or (p / "runs").is_dir():
            return p
    return here
