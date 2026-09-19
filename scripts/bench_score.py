#!/usr/bin/env python3
"""벤치 자산 전부를 **문서에 적힌 순서대로** 리깅해 완성도 점수를 낸다(토큰 0).

점수를 손으로 고르지 않기 위한 장치다. 자산마다 아래 사다리를 그대로 탄다:

  1. `--from-skeleton`  — 파일에 쓸 만한 원본 뼈대가 있으면 관절을 그대로 받는다
  2. `--preset`         — 뼈대가 없거나 반쪽이면 실루엣에서 추정한다
  3. `--from-shape`     — 실루엣 게이트가 막으면 메시 속 중심선에서 뼈대를 만든다

한 단계라도 `ok` 가 나오면 통과, 전부 `needs_review`/`rejected` 면 실패로 센다.
자산 목록도 폴더에서 읽는다 — 골라 담을 여지를 남기지 않는다.

**리깅 게이트만으로는 부족하다.** 게이트는 **정지 자세**만 본다. 2026-09-19 에 가중치를 건드리는 변경
두 건이 게이트를 통과하면서 실제 변형은 나쁘게 만들었고(가로트림 4.71→7.88배, 원작자 가중치 이전
5.78→11.25배), 둘 다 **움직여 재서야** 드러났다. 그래서 `--motion-*` 로 BVH 를 주면 통과한 자산마다
동작을 옮겨 **메시 늘어남**까지 재고, 점수를 두 줄로 낸다: 리깅 점수와 **동작까지 통과한 점수**.

    python3 scripts/bench_score.py --assets <폴더> --home <작업폴더> \
        --motion-humanoid walk.bvh --motion-quad wolf_walk.bvh
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

QUAD_HINT = ("animals",)          # 네발짐승 폴더는 프리셋이 다르다
SKIP_DIRS = ("raw",)              # 내려받은 원본 사본 — 같은 모델이 두 번 세어진다


def run(cli_args, home, sub="rig"):
    import os
    env = dict(os.environ, BW_HOME=str(home), BW_BACKEND="mock")
    p = subprocess.run([sys.executable, "-m", "bonewright.cli", sub, *cli_args, "--quiet"],
                       capture_output=True, text=True, env=env, timeout=1800)
    return p.returncode, (p.stdout + p.stderr)[-400:]


MIN_MAPPED = 4      # 이만큼도 안 붙었으면 동작이 리그에 닿지 않은 것이다
WIDE = 0.01         # 2배 넘게 늘어난 모서리가 이 비율을 넘으면 '넓게' 망가진 것이다


def verdict(st, a):
    """늘어남을 **깊이와 넓이 둘 다**로 판정한다.

    가장 늘어난 모서리 하나(깊이)만 보면 순위가 뒤집힌다 — Bull 은 11.63배지만 망가진 모서리가
    3635개 중 8개(0.22%)뿐이고, frog 는 4.55배인데 7540개 중 90개(1.19%)다. 정점 몇 개가 튀는 것과
    메시가 넓게 찢기는 것은 다른 문제라 따로 부른다."""
    deep, wide = st
    if wide >= WIDE:
        return "찢김"
    return "국소 튐" if deep >= a.stretch_max else "통과"


def stretch(home, run_id):
    """리타겟 결과의 (가장 늘어난 모서리 배수, 2배 넘게 늘어난 모서리 비율). **못 재면 None**.

    붙은 본 수를 먼저 본다. 이름 없는 일반 사슬 리그(`Limb3_2`)는 BVH 이름과 안 맞아 **본이 하나도
    안 붙는다**. 그러면 메시가 아예 안 움직여 늘어남이 정확히 1.00 으로 나오고, 그걸 '통과'로 세면
    **동작을 못 옮긴 자산이 만점을 받는다**(실제로 66종 중 32종이 그랬다). 측정 불가로 돌린다."""
    try:
        d = json.loads((Path(home) / "runs" / run_id / "retarget.json").read_text())
    except Exception:
        return None
    if len(d.get("mapped") or {}) < MIN_MAPPED:
        return None
    st = d["stretch"]
    return st["max_edge_ratio"], st["edges_over_2x"] / max(1, st["edges"])


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
    ap.add_argument("--motion-humanoid", help="사람형 리그에 옮겨 볼 BVH")
    ap.add_argument("--motion-quad", help="네발 리그에 옮겨 볼 BVH")
    ap.add_argument("--stretch-max", type=float, default=6.0, help="동작 통과 기준: 메시 늘어남 최대 배수")
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
        won = won_rid = None
        for step, extra in (("뼈대", ["--from-skeleton"]), ("프리셋", []), ("모양", ["--from-shape"])):
            rid = f"sc_{name}_{step}"
            run([str(f), "--preset", preset, *extra, "--run-id", rid, "--no-judge"], a.home)
            if status(a.home, rid) == "ok":
                won, won_rid = step, rid
                break
        ok += bool(won)
        bvh = a.motion_quad if preset == "quadruped" else a.motion_humanoid
        st = None
        if won and bvh:
            mid = f"{won_rid}_mo"
            run(["--bvh", bvh, "--rig", won_rid, "--run-id", mid], a.home, sub="motion")
            st = stretch(a.home, mid)
        rows.append((name, preset, won or "실패", st, round(time.time() - t0, 1)))
        mark = "-" if st is None else verdict(st, a)
        sv = "  -  " if st is None else f"{st[0]:5.2f}"
        wv = "   - " if st is None else f"{100 * st[1]:4.1f}%"
        print(f"[{i:3d}/{len(files)}] {name:28s} {preset:10s} {won or '실패':6s} 늘어남 {sv} 넓이 {wv} {mark:7s} {rows[-1][4]:6.1f}s",
              file=out, flush=True)
    moved = [r for r in rows if r[3] is not None]
    good = [r for r in moved if verdict(r[3], a) == "통과"]
    print(f"\n리깅 점수     {ok}/{len(files)} = {100 * ok / max(1, len(files)):.1f}%", file=out, flush=True)
    if moved:
        print(f"동작까지 통과 {len(good)}/{len(moved)} = {100 * len(good) / len(moved):.1f}%"
              f"  (깊이 {a.stretch_max}배 미만 + 넓이 {100 * WIDE:.0f}% 미만 · 본이 {MIN_MAPPED}개 이상 붙어 실제로 움직인 자산만)", file=out, flush=True)
    for n, p, w, st, _t in rows:
        if w == "실패":
            print(f"  리깅 실패: {n} ({p})", file=out, flush=True)
    for label in ("찢김", "국소 튐"):
        for n, p, w, st, _t in rows:
            if st is not None and verdict(st, a) == label:
                print(f"  동작 {label}: {n} ({p}) 늘어남 {st[0]}배 · 망가진 모서리 {100 * st[1]:.2f}%",
                      file=out, flush=True)


if __name__ == "__main__":
    main()
