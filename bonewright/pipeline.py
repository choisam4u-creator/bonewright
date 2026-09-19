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
from .from_skeleton import targets_from_skeleton
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
        force: bool = False, rest_pose: str | None = None, weights: str | None = None, from_skeleton: bool = False, from_shape: bool = False) -> Path:
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
            _log(quiet, f"[1/6] 포즈 정규화: 팔 {norm['angles_deg']}° → 수평으로 펴고 다시 분석")
        else:
            _log(quiet, f"[1/6] 포즈 정규화: 팔 {norm.get('angles_deg')}° — 이미 수평에 가까워 손대지 않는다")
    if a["landmarks"].get("suspect"):
        _log(quiet, f"  ⚠ 분석을 믿기 어렵다: {'; '.join(a['landmarks']['suspect'])} → 결과가 나쁘면 `--pin 본=x,y,z` 로 관절을 직접 고정하고 재시도하라")
    _log(quiet, f"[1/6] analyze: 정점 {a['stats']['verts']:,} · 높이 {a['landmarks']['height']}m · 조각 {a['stats']['loose_parts']} · 비매니폴드 {a['stats']['nonmanifold_edges']} · 대칭 오차 {a['landmarks']['symmetry_error']} · 포즈 {a['landmarks']['pose_guess']}")
    # 1b 거절 게이트: 모델을 부르기 전에 이 메시가 이 프리셋에 맞는지 본다.
    # 여기서 막으면 토큰이 0 이다(리그 1건 입력 8만 토큰). --force 로 넘길 수 있다
    block, warn = ([], []) if (from_skeleton or from_shape) else preflight(a["landmarks"], a["stats"], preset, cfg["gates"])
    if from_skeleton:
        warn.append("--from-skeleton: 관절을 원본 뼈대에서 그대로 받는다 — 실루엣 기반 거절 게이트는 건너뛴다")
    if from_shape:
        warn.append("--from-shape: 메시 모양에서 뼈대를 만든다 — 해부학적 관절이 아니라 모양을 따라가는 조작 장치다. 렌더를 꼭 확인하라")
    for w in warn:
        _log(quiet, f"  ⚠ {w}")
    if block and not force:
        r.state("preflight", "rejected", reasons=block)
        # 파일에 원본 뼈대가 있으면 그게 가장 나은 탈출구다 — 추정할 필요 없이 관절을 그대로 받으면 된다
        hint = ("\n  이 파일에는 원본 뼈대가 있다 → `--from-skeleton` 으로 관절을 그대로 받아라(토큰 0, 실루엣 추정 없음)"
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
            hint += (f"\n  손으로 고칠 출발점을 남겼다: {r.dir / 'targets_draft.json'} (메타리그를 이 메시 크기로 맞춘 것)"
                     f"\n  관절을 옮긴 뒤 `bw rig <mesh> --targets {r.dir / 'targets_draft.json'}` 로 돌리면 토큰 0 이다")
        except Exception as e:   # 초안은 부가 기능이다 — 실패해도 거절 이유는 그대로 알린다
            hint += f"\n  (목표표 초안을 만들지 못했다: {e})"
        raise Blocked("이 메시는 " + preset + " 프리셋에 맞지 않는다(토큰 0 으로 중단):\n  - " + "\n  - ".join(block) + hint +
                      "\n  그래도 추정으로 돌리려면 --force")
    if block:
        _log(quiet, "  ⚠ --force: 거절 사유를 무시하고 진행한다 — " + "; ".join(block))

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
            r.state("fit", "rejected", reasons=[sj.get("error") or "모양에서 뼈대를 못 만들었다"])
            raise Blocked("--from-shape: " + (sj.get("error") or "메시 속에서 중심선을 못 찾았다"))
        gen_preset = "generic"; source_joints = sj["joints"]
        fit = {"targets": {}, "reasoning": f"모양 리그: 속 중심선에서 팔다리 {sj['limbs']}개 · 본 {sj['bones']}개", "confidence": None}
        _log(quiet, f"[2/6] fit: 모양에서 뼈대를 만들었다 — 팔다리 {sj['limbs']}개 · 마디 {sj['segments']}개씩 · 본 {sj['bones']}개 · 모델 호출 0회")
    elif from_skeleton:
        def _reject(why: str, reasons: list[str]):
            r.state("fit", "rejected", reasons=reasons)   # 거절도 상태로 남긴다(중간에 멈춘 실행과 구분)
            raise Blocked(why)
        gt = r.blender("gt_joints", {"mesh": mesh, "facing": facing, "preset": preset})
        if not gt.get("joints"):
            _reject("--from-skeleton: 이 파일에 원본 뼈대가 없다 — 기본 경로(--from-skeleton 없이)로 돌려라", ["뼈대 없음"])
        tg, info = targets_from_skeleton(gt["joints"], preset, a["landmarks"]["height"], a["landmarks"].get("ground_z", 0.0))
        source_joints = gt["joints"]   # 메타리그 경로에서도 원작자 가중치를 자리로 옮길 수 있게 넘긴다
        source_leak = (gt.get("source_leak") or {}).get("ratio")   # 원작자 자신의 팔→몸통 누수(보정용)
        # 사람·개과 메타리그에 맞출 수 없는 몸(용·유령·문어·블롭)은 거절하는 대신 **원본 뼈대를 그대로 베낀
        # 일반 리그**로 간다. 관절 이름을 못 알아봐도, 팔다리가 없어도, 사슬이면 컨트롤을 만들 수 있다
        if info["limbs_absent"] or len(tg) < 6:
            why = ("팔다리 없음: " + ", ".join(info["limbs_absent"])) if info["limbs_absent"] else f"알아본 관절 {len(tg)}개"
            gen_preset = "generic"; source_joints = gt["joints"]
            fit = {"targets": {}, "reasoning": f"일반 리그: 원본 뼈대 {len(gt['joints'])}본을 그대로 베낌({why})", "confidence": None}
            _log(quiet, f"[2/6] fit: 사람·개과 메타리그에 못 맞춘다({why}) → **일반 리그**로 간다 · 원본 본 {len(gt['joints'])}개 · 모델 호출 0회")
        else:
            fit = {"targets": tg, "reasoning": f"원본 뼈대 {info['bones']}본에서 가져옴: {', '.join(info['matched'])}", "confidence": None}
        source_symmetry = info.get("source_symmetry", 0.0)
        if gen_preset == "generic":
            source_symmetry = 0.0
        else:
            _log(quiet, f"[2/6] fit: 원본 뼈대에서 목표 {len(tg)}개 · 모델 호출 0회 · 못 찾은 관절 {info['missing']}" +
                 (f" · 한쪽만 있어 비춰 채운 본 {info['mirrored']}" if info["mirrored"] else "") +
                 (f" · 원본 좌우 어긋남 {source_symmetry}m(이만큼은 우리 오차가 아니다)" if source_symmetry > 0.01 else ""))
    elif targets_file:
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
    g = r.blender("fit_generate", {"blend": str(r.dir / "01_analyzed.blend"), "out_blend": str(r.dir / "02_rigged.blend"), "preset": gen_preset,
                                   "source_joints": source_joints,
                                   # 원본이 좌우 대칭인 뼈대면 우리 결과도 대칭이어야 한다(보정이 만든 어긋남은 되돌린다)
                                   "source_symmetric": bool(from_skeleton and source_symmetry <= a["landmarks"]["height"] * 0.005),
                                   "targets": fit["targets"], "landmarks": a["landmarks"], "stats": a["stats"], "face": cfg["rig"]["face"], "pinned": sorted(pins),
                                   # 이미 메시를 T 로 펴 놨으면 fit_generate 에서 또 펴지 않는다
                                   "rest_pose": "keep" if (norm and norm.get("applied")) else want_rest,
                                   "weight_method": weights or cfg["rig"].get("weights", "auto"),
                                   "cross_trim": cfg["rig"].get("cross_trim", True),
                                   # 사람 메타리그를 사람 아닌 비율(로봇)에 씌울 때만 살집 보조 본도 부모 척추를 따라가게 한다.
                                   # 사족은 메타리그가 이미 네발짐승이라 기본 자리가 맞고, 따라가게 하면 오히려 몸 밖으로 나간다(말·늑대로 확인)
                                   "propagate_helpers": from_skeleton and gen_preset == "humanoid"})
    g["preset"] = preset   # bw motion 이 리그의 프리셋을 스스로 알도록 남긴다
    if norm:
        g["stats"]["normalize_pose"] = norm
    atomic_write(r.dir / "rig_stats.json", json.dumps(g, ensure_ascii=False, indent=2))
    st = g["stats"]
    _log(quiet, f"[3/6] generate: 리그 본 {st['rig_bones']} (변형 {st['deform_bones']}) · 가중치 없는 정점 {st['unweighted_verts']}(가까운 본으로 메운 {st.get('filled_unweighted', 0)}) · 상자 밖 {len(st['bones_outside_bbox'])}")
    # 4 게이트
    fails = rig_gates(st, cfg["gates"], a["stats"]["verts"], source_symmetry, source_leak)
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
              f"- weights ({st.get('weight_method')}): unweighted {st['unweighted_verts']} (filled by nearest bone {st.get('filled_unweighted', 0)}"
              + (f", rigid parts bound whole {st['rigid_islands_bound']}" if st.get("rigid_islands_bound") else "")
              + f") · sum {st['weight_sum_min']}–{st['weight_sum_max']} · symmetry err {st['symmetry_max_error']}",
              f"- gates: {'PASS' if not fails else 'FAIL: ' + '; '.join(fails)}" +
              (f" · ⚠ 조각 사이 빈틈을 지나는 본 {st['deform_gap_mesh']}: {st.get('deform_gap_mesh_bones', [])[:4]}" if st.get("deform_gap_mesh") else ""),
              f"- judge: {json.dumps(judge, ensure_ascii=False)}",
              f"- renders: {', '.join(Path(p).name for p in views['images'])}",
              f"- targets: `{r.dir / 'targets.json'}` (손으로 고쳐 `bw rig <mesh> --targets` 로 토큰 0 재실행)" + (f" · 고정 {sorted(pins)}" if pins else ""),
              f"- tokens: in {t['input']:,} / out {t['output']:,} · ≈${t['usd_upper']} upper · calls {len(r.usage)}", ""]
    atomic_write(r.dir / "report.md", "\n".join(report))
    r.state("final", status)
    _log(quiet, f"완료({status}) → {r.dir / 'report.md'}")
    return r.dir / "report.md"


def motion(root: Path, text: str | None = None, bvh: str | None = None, run_id: str | None = None, quiet: bool = False,
           rig_run: str | None = None, export: str | None = None, roll: bool = True, preset: str | None = None, bvh_up: str = "y", legs: str = "auto") -> Path:
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
    from .retarget import detect_bvh_up
    if rig_run and preset is None:   # 리그 실행 기록에서 프리셋을 읽는다(없는 옛 실행은 humanoid). 위 축 판단에도 필요하다
        rs = root / "runs" / rig_run / "rig_stats.json"
        preset = (json.loads(rs.read_text()).get("preset") if rs.exists() else None) or "humanoid"
    if bvh_up == "auto":   # 위 축을 틀리면 조용히 망가진다(늑대 걷기: 발이 바닥에서 1m 뜸) → 머리·발 위치로 정한다
        bvh_up = detect_bvh_up(str(Path(bvh).resolve()), preset or "humanoid")
        _log(quiet, f"[3/3] bvh 위 축 자동 판단: {bvh_up} (틀리면 --bvh-up 으로 직접 지정)")
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


def export_rig(root: Path, run_id: str, out: str | None = None, quiet: bool = False) -> Path:
    """리깅 결과 → 변형 본만 든 GLB(토큰 0). 다시 읽어 본 위치를 대조한다."""
    cfg = load(root)
    r = Run(root, run_id, cfg, quiet)
    blend = r.dir / "02_rigged.blend"
    if not blend.exists():
        raise Blocked(f"리깅 결과가 없다: {blend}")
    dst = Path(out).resolve() if out else (r.dir / "rigged.glb")
    ex = r.blender("export_rig", {"blend": str(blend), "out": str(dst)})
    _log(quiet, f"export: {dst} · 변형 본 {ex['bones']} · 정점 {ex['verts']}/{ex['verts_in_source']} · 다시 읽어 본 위치 차이 최대 {ex['max_diff_cm']}cm")
    atomic_write(r.dir / "export.json", json.dumps(ex, ensure_ascii=False, indent=2))
    return dst


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
