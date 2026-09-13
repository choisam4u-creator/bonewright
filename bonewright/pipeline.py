"""파이프라인: rig(분석 → 맞춤 판단 → 생성·스키닝 → 게이트 → 렌더 → 시각 판정 → 보고서), motion(kimodo → BVH → 가져오기)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import schemas
from .blender import run_script
from .codex import CodexError, UsageLimit, run_step
from .config import load
from .gates import judge_gates, rig_gates
from .ledger import append as ledger_append
from .manifest import atomic_write
from .mock import mock_backend

PROMPTS = Path(__file__).parent / "prompts"


class Blocked(RuntimeError):
    pass


def _prompt(name: str, lang: str) -> str:
    return (PROMPTS / lang / f"{name}.md").read_text(encoding="utf-8")


def _log(quiet: bool, msg: str) -> None:
    if not quiet:
        print(f"[bw {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


class Run:
    def __init__(self, root: Path, run_id: str, cfg: dict, quiet: bool = False):
        self.root, self.run_id, self.cfg, self.quiet = root, run_id, cfg, quiet
        self.dir = root / "runs" / run_id
        self.logs = self.dir / "logs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.usage: list[dict] = []

    def state(self, step: str, status: str, **extra) -> None:
        atomic_write(self.dir / "state.json", json.dumps({"step": step, "status": status, "at": time.time(), "pid": os.getpid(),
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
            raise Blocked(f"예산 상한 도달: 입력 {self.tokens()['input']:,} ≥ {limit:,}")
        _log(self.quiet, f"  → {name} (파일 {len(inputs)}개, 이미지 {len(images or [])}장)")
        try:
            result, usage = run_step(name, _prompt(name, self.cfg["lang"]), schema, inputs, self.cfg["models"][role], self.cfg["codex"], self.logs,
                                     mock=mock_backend, images=images, heartbeat=lambda m: _log(self.quiet, f"    … {name} {m}"))
        except UsageLimit as e:
            self.state(name, "usage_limit", resets_at=e.resets_at)
            raise Blocked(f"{e} → 리셋 뒤 `bw resume {self.run_id}`")
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
        r = run_script(name, params, self.cfg["blender"], self.logs)
        _log(self.quiet, f"  ⚙ {name} {time.time() - t:.1f}s")
        return r


def rig(root: Path, mesh: str, preset: str = "humanoid", run_id: str | None = None, lang: str | None = None, quiet: bool = False,
        budget: int | None = None, no_judge: bool = False) -> Path:
    cfg = load(root, lang)
    if budget:
        cfg["budget"]["max_input_tokens"] = budget
    run_id = run_id or time.strftime("rig-%Y%m%d-%H%M%S")
    r = Run(root, run_id, cfg, quiet)
    mesh = str(Path(mesh).resolve())
    _log(quiet, f"rig {run_id} · {preset} · {mesh}")
    # 1 분석
    r.state("analyze", "running")
    a = r.blender("analyze", {"mesh": mesh, "blend": str(r.dir / "01_analyzed.blend")})
    atomic_write(r.dir / "analysis.json", json.dumps(a, ensure_ascii=False, indent=2))
    _log(quiet, f"[1/6] analyze: 정점 {a['stats']['verts']:,} · 높이 {a['landmarks']['height']}m · 조각 {a['stats']['loose_parts']} · 비매니폴드 {a['stats']['nonmanifold_edges']} · 대칭 오차 {a['landmarks']['symmetry_error']} · 포즈 {a['landmarks']['pose_guess']}")
    # 2 맞춤 판단(모델)
    r.state("fit", "running")
    meta = r.blender("metarig_dump", {"preset": preset, "height": a["landmarks"]["height"], "ground_z": a["landmarks"]["ground_z"]})
    fit = r.call("fit", "fit", {"analysis.json": json.dumps({"stats": a["stats"], "landmarks": a["landmarks"], "bands": a["bands"][::2]}, ensure_ascii=False),
                               "metarig_bones.json": json.dumps(meta["bones"], ensure_ascii=False)}, schemas.FIT)
    fit["targets"] = {t["name"]: {"head": t["head"], "tail": t["tail"]} for t in fit["targets"]}   # 배열 → 이름별 dict
    atomic_write(r.dir / "fit.json", json.dumps(fit, ensure_ascii=False, indent=2))
    _log(quiet, f"[2/6] fit: 목표 본 {len(fit['targets'])}개 · 확신 {fit.get('confidence')}")
    # 3 생성·스키닝·통계
    r.state("generate", "running")
    g = r.blender("fit_generate", {"blend": str(r.dir / "01_analyzed.blend"), "out_blend": str(r.dir / "02_rigged.blend"), "preset": preset,
                                   "targets": fit["targets"], "landmarks": a["landmarks"], "stats": a["stats"], "face": cfg["rig"]["face"]})
    atomic_write(r.dir / "rig_stats.json", json.dumps(g, ensure_ascii=False, indent=2))
    st = g["stats"]
    _log(quiet, f"[3/6] generate: 리그 본 {st['rig_bones']} (변형 {st['deform_bones']}) · 가중치 없는 정점 {st['unweighted_verts']} · 상자 밖 {len(st['bones_outside_bbox'])}")
    # 4 게이트
    fails = rig_gates(st, cfg["gates"], a["stats"]["verts"])
    _log(quiet, f"[4/6] gates: {'통과' if not fails else fails}")
    # 5 렌더
    r.state("render", "running")
    views = r.blender("render_views", {"blend": str(r.dir / "02_rigged.blend"), "out_dir": str(r.dir), "stats": a["stats"], "size": cfg["render"]["size"]})
    _log(quiet, f"[5/6] render: {len(views['images'])}장 · 본 기둥 {views['bone_proxies']}")
    # 6 시각 판정(모델)
    judge = {"skipped": True}
    if not no_judge:
        r.state("judge", "running")
        imgs = [p for p in views["images"] if any(v in p for v in cfg["render"]["judge_views"])]
        judge = r.call("judge", "judge", {"context.txt": f"preset={preset}; height={a['landmarks']['height']}m; deform_bones={st['deform_bones']}"}, schemas.JUDGE, images=imgs)
        fails += judge_gates(judge)
        _log(quiet, f"[6/6] judge: 밖 {judge['bones_outside_mesh']} · 비율 {'ok' if judge['proportions_ok'] else '이상'} · 확신 {judge['confidence']}")
    # 보고서
    t = r.tokens(); status = "ok" if not fails else "needs_review"
    report = [f"# bonewright rig report · {run_id}", "",
              f"- mesh: `{mesh}` · preset: {preset} · verts {a['stats']['verts']:,} · height {a['landmarks']['height']} m",
              f"- rig: `{g['blend']}` · bones {st['rig_bones']} (deform {st['deform_bones']}) · moved metarig bones {len(st['moved_bones'])}",
              f"- weights ({st.get('weight_method')}): unweighted {st['unweighted_verts']} · sum {st['weight_sum_min']}–{st['weight_sum_max']} · symmetry err {st['symmetry_max_error']}",
              f"- gates: {'PASS' if not fails else 'FAIL: ' + '; '.join(fails)}",
              f"- judge: {json.dumps(judge, ensure_ascii=False)}",
              f"- renders: {', '.join(Path(p).name for p in views['images'])}",
              f"- tokens: in {t['input']:,} / out {t['output']:,} · ≈${t['usd_upper']} upper · calls {len(r.usage)}", ""]
    atomic_write(r.dir / "report.md", "\n".join(report))
    r.state("final", status)
    _log(quiet, f"완료({status}) → {r.dir / 'report.md'}")
    return r.dir / "report.md"


def motion(root: Path, text: str | None = None, bvh: str | None = None, run_id: str | None = None, quiet: bool = False) -> Path:
    """텍스트 → kimodo.cpp(Metal) → BVH → Blender 가져오기. 토큰 0. 리타겟은 v0.2."""
    cfg = load(root)
    run_id = run_id or time.strftime("motion-%Y%m%d-%H%M%S")
    r = Run(root, run_id, cfg, quiet)
    k = cfg["kimodo"]; kroot = (root / k["root"]).resolve()
    if text:
        gen = kroot / "build-release" / "kmd-generate"
        if not gen.exists():
            raise Blocked(f"kimodo.cpp 빌드가 없다: {gen}. docs/research-20260913.html 7절의 빌드 절차 참고")
        r.state("kimodo", "running")
        (r.dir / "prompt.txt").write_text(text, encoding="utf-8")
        t = time.time()
        proc = subprocess.run([str(gen), str(kroot / k["model"]), str(kroot / k["text_bundle"]), str(r.dir / "prompt.txt"),
                               str(k["frames"]), str(k["steps"]), str(k["seed"]), str(r.dir / "motion")], capture_output=True, text=True)
        (r.logs).mkdir(exist_ok=True); (r.logs / "kimodo.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            r.state("kimodo", "failed"); raise Blocked(f"kimodo 실패: {proc.stderr[-500:]}")
        _log(quiet, f"[1/3] kimodo: {proc.stdout.strip()} · {time.time() - t:.1f}s")
        bvh = str(r.dir / "motion" / "motion.bvh")
        proc = subprocess.run([sys.executable, str(kroot / "scripts" / "export_bvh.py"), "--motion-dir", str(r.dir / "motion"), "--output", bvh, "--fps", "30", "--scale", "1.0"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise Blocked(f"BVH 변환 실패: {proc.stderr[-500:]}")
        _log(quiet, f"[2/3] bvh: {bvh}")
    if not bvh:
        raise Blocked("--text 또는 --bvh 가 필요하다")
    r.state("import", "running")
    imp = r.blender("import_bvh", {"bvh": str(Path(bvh).resolve()), "out_blend": str(r.dir / "motion.blend")})
    _log(quiet, f"[3/3] import: 본 {imp['bones']} · 프레임 {imp['frames']} · {imp['fps']}fps · 루트 이동 {imp['root_move']}m")
    report = [f"# bonewright motion report · {run_id}", "", f"- source: {'text: ' + text if text else 'bvh: ' + bvh}",
              f"- armature: {imp['armature']} · bones {imp['bones']} · frames {imp['frames']} · fps {imp['fps']} · root move {imp['root_move']} m",
              f"- blend: `{r.dir / 'motion.blend'}`", "- retarget to Rigify: not yet (v0.2)", ""]
    atomic_write(r.dir / "report.md", "\n".join(report)); r.state("final", "ok")
    _log(quiet, f"완료 → {r.dir / 'report.md'}")
    return r.dir / "report.md"
