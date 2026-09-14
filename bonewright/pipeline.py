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
from .gates import judge_gates, preflight, rig_gates
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
        budget: int | None = None, no_judge: bool = False, facing: str = "auto", pins: dict | None = None, targets_file: str | None = None,
        force: bool = False, rest_pose: str | None = None, weights: str | None = None) -> Path:
    cfg = load(root, lang)
    if budget:
        cfg["budget"]["max_input_tokens"] = budget
    run_id = run_id or time.strftime("rig-%Y%m%d-%H%M%S")
    r = Run(root, run_id, cfg, quiet)
    mesh = str(Path(mesh).resolve())
    _log(quiet, f"rig {run_id} · {preset} · {mesh}")
    # 1 분석
    r.state("analyze", "running")
    a = r.blender("analyze", {"mesh": mesh, "blend": str(r.dir / "01_analyzed.blend"), "facing": facing, "preset": preset})
    atomic_write(r.dir / "analysis.json", json.dumps(a, ensure_ascii=False, indent=2))
    _log(quiet, f"[1/6] import: {a['stats'].get('import')}")
    if a["landmarks"].get("suspect"):
        _log(quiet, f"  ⚠ 분석을 믿기 어렵다: {'; '.join(a['landmarks']['suspect'])} → 결과가 나쁘면 `--pin 본=x,y,z` 로 관절을 직접 고정하고 재시도하라")
    _log(quiet, f"[1/6] analyze: 정점 {a['stats']['verts']:,} · 높이 {a['landmarks']['height']}m · 조각 {a['stats']['loose_parts']} · 비매니폴드 {a['stats']['nonmanifold_edges']} · 대칭 오차 {a['landmarks']['symmetry_error']} · 포즈 {a['landmarks']['pose_guess']}")
    # 1b 거절 게이트: 모델을 부르기 전에 이 메시가 이 프리셋에 맞는지 본다.
    # 여기서 막으면 토큰이 0 이다(리그 1건 입력 8만 토큰). --force 로 넘길 수 있다
    block, warn = preflight(a["landmarks"], a["stats"], preset, cfg["gates"])
    for w in warn:
        _log(quiet, f"  ⚠ {w}")
    if block and not force:
        r.state("preflight", "rejected", reasons=block)
        raise Blocked("이 메시는 " + preset + " 프리셋에 맞지 않는다(토큰 0 으로 중단):\n  - " + "\n  - ".join(block) +
                      "\n  그래도 돌리려면 --force, 관절을 직접 찍으려면 --pin 본=x,y,z")
    if block:
        _log(quiet, "  ⚠ --force: 거절 사유를 무시하고 진행한다 — " + "; ".join(block))

    # 2 맞춤 판단(모델). --targets 가 있으면 모델을 부르지 않는다(토큰 0)
    r.state("fit", "running")
    pins = dict(pins or {})
    if targets_file:
        fit = {"targets": json.loads(Path(targets_file).read_text(encoding="utf-8")), "reasoning": f"재사용: {targets_file}", "confidence": None}
        _log(quiet, f"[2/6] fit: 파일 재사용 {targets_file} · 목표 본 {len(fit['targets'])}개 · 모델 호출 0회")
    else:
        meta = r.blender("metarig_dump", {"preset": preset, "height": a["landmarks"]["height"], "ground_z": a["landmarks"]["ground_z"]})
        inputs = {"analysis.json": json.dumps({"stats": a["stats"], "landmarks": a["landmarks"], "bands": a["bands"][::2]}, ensure_ascii=False),
                  "metarig_bones.json": json.dumps(meta["bones"], ensure_ascii=False)}
        if pins:
            inputs["pins.json"] = json.dumps(pins, ensure_ascii=False)
        fit = r.call("fit", "fit", inputs, schemas.FIT)
        fit["targets"] = {t["name"]: {"head": t["head"], "tail": t["tail"]} for t in fit["targets"]}   # 배열 → 이름별 dict
        _log(quiet, f"[2/6] fit: 목표 본 {len(fit['targets'])}개 · 확신 {fit.get('confidence')}")
    for name, v in pins.items():   # 사용자가 고정한 관절이 최종 결정권을 갖는다
        fit["targets"].setdefault(name, {}).update(v)
    if pins:
        _log(quiet, f"  📌 고정된 관절 {len(pins)}개: {', '.join(sorted(pins))}")
    atomic_write(r.dir / "fit.json", json.dumps(fit, ensure_ascii=False, indent=2))
    atomic_write(r.dir / "targets.json", json.dumps(fit["targets"], ensure_ascii=False, indent=2))   # 손으로 고쳐 --targets 로 재사용
    # 3 생성·스키닝·통계
    r.state("generate", "running")
    g = r.blender("fit_generate", {"blend": str(r.dir / "01_analyzed.blend"), "out_blend": str(r.dir / "02_rigged.blend"), "preset": preset,
                                   "targets": fit["targets"], "landmarks": a["landmarks"], "stats": a["stats"], "face": cfg["rig"]["face"], "pinned": sorted(pins),
                                   "rest_pose": rest_pose or cfg["rig"].get("rest_pose", "keep"),
                                   "weight_method": weights or cfg["rig"].get("weights", "auto")})
    atomic_write(r.dir / "rig_stats.json", json.dumps(g, ensure_ascii=False, indent=2))
    st = g["stats"]
    _log(quiet, f"[3/6] generate: 리그 본 {st['rig_bones']} (변형 {st['deform_bones']}) · 가중치 없는 정점 {st['unweighted_verts']}(가까운 본으로 메운 {st.get('filled_unweighted', 0)}) · 상자 밖 {len(st['bones_outside_bbox'])}")
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
              f"- import: {json.dumps(a['stats'].get('import'), ensure_ascii=False)}",
              f"- landmarks: chibi={a['landmarks'].get('chibi')} · head_ratio={a['landmarks'].get('head_ratio')} · neck={a['landmarks'].get('neck_from')} · suspect={a['landmarks'].get('suspect')}",
              f"- rig: `{g['blend']}` · bones {st['rig_bones']} (deform {st['deform_bones']}) · moved metarig bones {len(st['moved_bones'])}",
              f"- weights ({st.get('weight_method')}): unweighted {st['unweighted_verts']} (filled by nearest bone {st.get('filled_unweighted', 0)}) · sum {st['weight_sum_min']}–{st['weight_sum_max']} · symmetry err {st['symmetry_max_error']}",
              f"- gates: {'PASS' if not fails else 'FAIL: ' + '; '.join(fails)}",
              f"- judge: {json.dumps(judge, ensure_ascii=False)}",
              f"- renders: {', '.join(Path(p).name for p in views['images'])}",
              f"- targets: `{r.dir / 'targets.json'}` (손으로 고쳐 `bw rig <mesh> --targets` 로 토큰 0 재실행)" + (f" · 고정 {sorted(pins)}" if pins else ""),
              f"- tokens: in {t['input']:,} / out {t['output']:,} · ≈${t['usd_upper']} upper · calls {len(r.usage)}", ""]
    atomic_write(r.dir / "report.md", "\n".join(report))
    r.state("final", status)
    _log(quiet, f"완료({status}) → {r.dir / 'report.md'}")
    return r.dir / "report.md"


def motion(root: Path, text: str | None = None, bvh: str | None = None, run_id: str | None = None, quiet: bool = False,
           rig_run: str | None = None, export: str | None = None, roll: bool = True, preset: str = "humanoid", bvh_up: str = "y", legs: str = "auto") -> Path:
    """텍스트 → kimodo.cpp(Metal) → BVH → Blender 가져오기 → (rig_run 이 있으면) 그 리그에 리타겟 → (export 면) 변형 본만 든 GLB. 토큰 0."""
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
    imp = r.blender("import_bvh", {"bvh": str(Path(bvh).resolve()), "out_blend": str(r.dir / "motion.blend"), "bvh_up": bvh_up})
    _log(quiet, f"[3/3] import: 본 {imp['bones']} · 프레임 {imp['frames']} · {imp['fps']}fps · 루트 이동 {imp['root_move']}m")
    report = [f"# bonewright motion report · {run_id}", "", f"- source: {'text: ' + text if text else 'bvh: ' + bvh}",
              f"- armature: {imp['armature']} · bones {imp['bones']} · frames {imp['frames']} · fps {imp['fps']} · root move {imp['root_move']} m",
              f"- blend: `{r.dir / 'motion.blend'}`"]
    if rig_run:
        from .retarget import bvh_mapping
        blend = root / "runs" / rig_run / "02_rigged.blend"
        if not blend.exists():
            raise Blocked(f"리깅 결과가 없다: {blend}")
        mapping = bvh_mapping(imp["bone_names"], preset)
        r.state("retarget", "running")
        fa, fb = imp["frames"] if imp.get("frames") else (1, 1)
        rf = sorted({fa, fa + (fb - fa) // 3, fa + 2 * (fb - fa) // 3, fb})
        an = json.loads((root / "runs" / rig_run / "analysis.json").read_text()) if (root / "runs" / rig_run / "analysis.json").exists() else {}
        rt = r.blender("retarget_bvh", {"blend": str(blend), "bvh": str(Path(bvh).resolve()), "mapping": mapping,
                                        "out_blend": str(r.dir / "retargeted.blend"), "out_dir": str(r.dir),
                                        "render_frames": rf, "height": (an.get("landmarks") or {}).get("height", 1.8), "roll": roll, "bvh_up": bvh_up, "legs": legs})
        _log(quiet, f"[4/4] retarget: 본 {len(rt['mapped'])}개 옮김 · 못 옮긴 BVH 본 {len(rt['unmapped'])}개 · "
                    f"본 방향 오차 평균 {rt.get('mean_dir_deg')}° · 손발 위치 오차 평균 {rt.get('mean_end_cm')}cm(비율 차이 포함)")
        report += [f"- retarget → `{rig_run}`: mapped {len(rt['mapped'])} bones, unmapped {rt['unmapped']}",
                   f"- legs: {rt.get('legs')} · IK {rt.get('ik_legs') or []} · FK(no foot joint in source) {rt.get('ik_skipped') or []} · roll transfer: {rt.get('roll')} · hand/foot twist error vs BVH: " + ", ".join(f"{k} {v['mean_deg']}°(max {v['max_deg']})" for k, v in (rt.get('roll_deg') or {}).items()),
                   f"- bone direction error vs BVH (proportion-free): mean {rt.get('mean_dir_deg')}° · " +
                   ", ".join(f"{k} {v['mean_deg']}°(max {v['max_deg']}, rest offset {v['rest_deg']})" for k, v in (rt.get('dir_deg') or {}).items()),
                   f"- end-effector error vs BVH (hips-relative, scaled {rt['scale']}, proportion-limited): mean {rt.get('mean_end_cm')} cm · " +
                   ", ".join(f"{k} {v['mean_cm']}cm(max {v['max_cm']})" for k, v in (rt.get('end_cm') or {}).items()),
                   f"- foot contact (lowest toe per frame): {rt.get('foot_contact')}",
                   f"- foot slide during BVH stance frames: {rt.get('foot_slide')}",
                   f"- deformation (edge stretch vs rest at rendered frames): {rt.get('stretch') and {k: v for k, v in rt['stretch'].items() if k != 'per_frame'}}",
                   f"- blend: `{r.dir / 'retargeted.blend'}`",
                   "- frames: " + " ".join(f"`{Path(p).name}`" for p in rt.get("renders", []))]
        atomic_write(r.dir / "retarget.json", json.dumps(rt, ensure_ascii=False, indent=2))
        if export:
            out = (r.dir / "animated.glb") if export == "auto" else Path(export).resolve()
            r.state("export", "running")
            ex = r.blender("export_anim", {"blend": str(r.dir / "retargeted.blend"), "out": str(out)})
            _log(quiet, f"[5/5] export: {out.name} · 본 {ex['bones']} · 프레임 {ex['frames']} · 다시 읽어 손발 위치 차이 최대 {ex['max_diff_cm']}cm")
            report += [f"- export: `{out}` · {ex['bones']} deform bones · {ex['verts']} verts · frames {ex['frames']} · "
                       f"re-import check at frame {ex['probe_frame']}: {ex['reimport_diff_cm']} (cm)"]
    else:
        report.append("- retarget: pass --rig <run-id> to move this motion onto a rig")
    report.append("")
    atomic_write(r.dir / "report.md", "\n".join(report)); r.state("final", "ok")
    _log(quiet, f"완료 → {r.dir / 'report.md'}")
    return r.dir / "report.md"


def demo(root: Path, run_id: str, quiet: bool = False, size: int = 640, frames: int = 96) -> Path:
    """리그 결과 데모 영상(토큰 0): runs/<id>/02_rigged.blend → demo.mp4(+ ffmpeg 가 있으면 demo.gif)."""
    import shutil
    cfg = load(root)
    r = Run(root, run_id, cfg, quiet)
    blend = r.dir / "02_rigged.blend"
    if not blend.exists():
        raise Blocked(f"리그 결과가 없다: {blend}")
    a = json.loads((r.dir / "analysis.json").read_text(encoding="utf-8"))
    d = r.blender("render_demo", {"blend": str(blend), "out_dir": str(r.dir), "stats": a["stats"], "height": a["landmarks"]["height"], "size": size, "frames": frames})
    out = Path(d["frames_dir"])
    if shutil.which("ffmpeg"):   # PNG 연속 이미지 → mp4(H.264) → gif(12fps, 480px)
        mp4, gif = r.dir / "demo.mp4", r.dir / "demo.gif"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(d["fps"]), "-i", str(out / "f_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse", str(gif)])
        out = mp4
    else:
        _log(quiet, "ffmpeg 가 없어 PNG 프레임만 남긴다 (brew install ffmpeg)")
    _log(quiet, f"demo: {out} · 프레임 {d['frames']} · 컨트롤 {d['controls']}")
    return out
