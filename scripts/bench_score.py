#!/usr/bin/env python3
"""벤치 자산 전부를 **문서에 적힌 순서대로** 리깅해 완성도 점수를 낸다(토큰 0).

점수를 손으로 고르지 않기 위한 장치다. 자산마다 아래 사다리를 그대로 탄다:

  1. `--from-skeleton`  — 파일에 쓸 만한 원본 뼈대가 있으면 관절을 그대로 받는다
  2. `--preset`         — 뼈대가 없거나 반쪽이면 실루엣에서 추정한다
  3. `--from-shape`     — 실루엣 게이트가 막으면 메시 속 중심선에서 뼈대를 만든다

한 단계라도 `ok` 가 나오면 통과, 전부 `needs_review`/`rejected` 면 실패로 센다.
자산 목록도 폴더에서 읽는다 — 골라 담을 여지를 남기지 않는다.

    python3 scripts/bench_score.py --assets <폴더> --home <작업폴더> [--only 이름]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

QUAD_HINT = ("animals",)          # 네발짐승 폴더는 프리셋이 다르다
SKIP_DIRS = ("raw",)              # 내려받은 원본 사본 — 같은 모델이 두 번 세어진다


def run(cli_args, home, env_extra=None):
    import os
    env = dict(os.environ, BW_HOME=str(home), BW_BACKEND="mock", **(env_extra or {}))
    p = subprocess.run([sys.executable, "-m", "bonewright.cli", "rig", *cli_args, "--no-judge", "--quiet"],
                       capture_output=True, text=True, env=env, timeout=1800)
    return p.returncode, (p.stdout + p.stderr)[-400:]


def status(home, run_id):
    try:
        return json.loads((Path(home) / "runs" / run_id / "state.json").read_text()).get("status")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True, help="벤치 자산 뿌리 폴더")
    ap.add_argument("--home", required=True, help="BW_HOME 으로 쓸 폴더")
    ap.add_argument("--only", help="이름에 이 문자열이 든 자산만")
    ap.add_argument("--out", help="줄별 결과를 적을 파일")
    a = ap.parse_args()
    root = Path(a.assets)
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in (".glb", ".gltf")
                   and not any(d in p.parts for d in SKIP_DIRS))
    if a.only:
        files = [p for p in files if a.only in p.name]
    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    ok = 0
    rows = []
    for i, f in enumerate(files, 1):
        name = f.stem
        preset = "quadruped" if any(h in str(f) for h in QUAD_HINT) else "humanoid"
        t0 = time.time()
        won = None
        for step, extra in (("뼈대", ["--from-skeleton"]), ("프리셋", []), ("모양", ["--from-shape"])):
            rid = f"sc_{name}_{step}"
            run([str(f), "--preset", preset, *extra, "--run-id", rid], a.home)
            if status(a.home, rid) == "ok":
                won = step
                break
        ok += bool(won)
        rows.append((name, preset, won or "실패", round(time.time() - t0, 1)))
        print(f"[{i:3d}/{len(files)}] {name:28s} {preset:10s} {won or '실패':6s} {rows[-1][3]:6.1f}s", file=out, flush=True)
    print(f"\n합계 {ok}/{len(files)} = {100 * ok / max(1, len(files)):.1f}%", file=out, flush=True)
    for n, p, w, _t in rows:
        if w == "실패":
            print(f"  실패: {n} ({p})", file=out, flush=True)


if __name__ == "__main__":
    main()
