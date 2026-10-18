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



def guide() -> str:
    """안내에 넣을 docs/GUIDE.md 의 위치. 저장소 폴더면 상대 경로, 다른 폴더면 저장소의 절대 경로(공백이면 따옴표),
    설치본만이면 '저장소의 docs/GUIDE.md'. 10/12 14회차: 임시 폴더에서 `bw doctor` 가 열 수 없는 상대 경로를 줬다."""
    from .i18n import T
    p = Path(__file__).resolve().parents[1] / "docs" / "GUIDE.md"
    if not p.is_file():
        return T("저장소의 docs/GUIDE.md", "docs/GUIDE.md in the repository")
    if Path("docs/GUIDE.md").resolve() == p:
        return "docs/GUIDE.md"
    return f'"{p}"' if any(c.isspace() for c in str(p)) else str(p)


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
    return T(f"⚠ 설정 파일에 모르는 키 {len(bad)}개 — 무시하고 기본값으로 돈다: {', '.join(bad)} ({p})\n  → 이름을 고쳐라. 쓸 수 있는 키는 {guide()} 의 \"Settings (`runs/config.json`)\"",
             f"⚠ {len(bad)} unknown key(s) in the settings file, ignored (defaults used): {', '.join(bad)} ({p})\n  → fix the name; the keys are listed under \"Settings (`runs/config.json`)\" in {guide()}")


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


def _type_name(v) -> str:
    """설정 형 오류 문구의 형 이름(화면 언어를 따른다 — 10/11 11회차: 한국어 화면에서도 number·string 이었다)."""
    from .i18n import T
    names = {bool: T("참/거짓(true·false)", "true/false"), int: T("숫자", "number"), float: T("숫자", "number"),
             str: T("문자열", "string"), list: T("목록", "list"), dict: "{...}"}
    return names.get(type(v), type(v).__name__)


def type_problems(user: dict, known: dict = DEFAULTS, prefix: str = "") -> list[str]:
    """기본값과 형(型)이 다른 키: "budget.max_input_tokens: number expected (default 600000), got string". 모르는 키는 건너뛴다
    (unknown_keys 가 따로 알린다). 10/11 11회차: "lots"·"t" 같은 값이 첫 모델 호출·rig 단계에서 TypeError 로 떨어졌다."""
    out = []
    for k, v in user.items():
        if k not in known:
            continue
        d = known[k]
        if isinstance(d, dict):
            out += type_problems(v, d, f"{prefix}{k}.") if isinstance(v, dict) else [f"{prefix}{k}: {{...}} ← {_type_name(v)} {json.dumps(v, ensure_ascii=False)}"]
            continue
        number = isinstance(d, (int, float)) and not isinstance(d, bool)
        ok = (isinstance(v, (int, float)) and not isinstance(v, bool)) if number else isinstance(v, type(d))
        if not ok:
            out.append(f"{prefix}{k}: {_type_name(d)} ({json.dumps(d, ensure_ascii=False)}) ← {_type_name(v)} {json.dumps(v, ensure_ascii=False)}")
    return out


# 명령줄과 같은 선택지(cli 의 choices). 10/11 11회차: `--lang fr` 은 argparse 가 막는데 설정의 "lang": "fr" 은 받아들였다
CHOICES = {"lang": ("", "ko", "en"), "rig.rest_pose": ("keep", "t"), "rig.weights": ("auto", "proxy")}


def choice_problems(user: dict) -> list[str]:
    out = []
    for key, allowed in CHOICES.items():
        node = user
        for part in key.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if node is not None and node not in allowed:
            near = difflib.get_close_matches(str(node).lower(), [a for a in allowed if a], n=1, cutoff=0.5)
            shown = " | ".join(json.dumps(a) for a in allowed)
            out.append(f"{key}: {json.dumps(node, ensure_ascii=False)} → {shown}" + (f" ({json.dumps(near[0])}?)" if near else ""))
    return out


def load(root: Path, lang: str | None = None) -> dict:
    if (msg := backend_problem()):
        from .pipeline import Blocked   # pipeline 이 이 모듈을 import 하므로 여기서
        raise Blocked(msg)
    cfg = DEFAULTS
    p = root / "runs" / "config.json"
    if p.exists():
        user = _read_user_config(p)
        if (bad := type_problems(user)):
            from .i18n import T
            from .pipeline import Blocked
            listing = "\n  ".join(bad)
            raise Blocked(T(f"설정 파일 값의 형이 틀렸다: {p}\n  {listing}\n  → 화살표 왼쪽(기본값과 같은 형)으로 고치거나 그 키를 지운다. 키 표: {guide()} 의 \"Settings (`runs/config.json`)\"",
                            f"wrong type in the settings file: {p}\n  {listing}\n  → use the type on the left of the arrow (the default's), or delete the key. Keys: \"Settings (`runs/config.json`)\" in {guide()}"))
        if (bad := choice_problems(user)):
            from .i18n import T
            from .pipeline import Blocked
            listing = "\n  ".join(bad)
            raise Blocked(T(f"설정 파일에 쓸 수 없는 값: {p}\n  {listing}\n  → 화살표 오른쪽 값 중 하나로 고치거나 그 키를 지운다(명령줄 선택지와 같다)",
                            f"value not allowed in the settings file: {p}\n  {listing}\n  → use one of the values right of the arrow, or delete the key (same choices as on the command line)"))
        cfg = _merge(cfg, user)
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
