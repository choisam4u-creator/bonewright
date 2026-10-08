"""기본 설정. runs/config.json 이 있으면 덮어쓴다(중첩 병합)."""
import json
import os
from pathlib import Path

from .i18n import lang as screen_lang

DEFAULTS = {
    "lang": "",            # 모델 프롬프트 언어(ko|en). 비우면 화면 언어(BW_LANG, 없으면 로캘)를 따른다
    "default_model": "gpt-6-astra",
    "models": {"fit": {"model": "gpt-6-astra", "effort": "medium"}, "judge": {"model": "gpt-6-astra", "effort": "low"}},
    "budget": {"max_input_tokens": 600_000, "price_input_per_m": 10.0, "price_output_per_m": 50.0},
    "codex": {"timeout": 600, "ignore_user_config": True, "extra_args": ["--skip-git-repo-check", "--ephemeral"]},
    "blender": {"app": "", "prefer_module": True, "timeout": 600},      # app 비우면 자동 탐색
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


def load(root: Path, lang: str | None = None) -> dict:
    cfg = DEFAULTS
    p = root / "runs" / "config.json"
    if p.exists():
        cfg = _merge(cfg, json.loads(p.read_text(encoding="utf-8")))
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
