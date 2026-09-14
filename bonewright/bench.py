"""정답 대조 벤치마크(토큰 0): 원본 뼈대가 든 캐릭터에서 뼈대를 떼고 우리가 리깅한 뒤,
원작자가 만든 관절 위치와 cm 단위로 비교한다. 게이트·시각 판정과 달리 '숫자로' 회귀를 잡는 수단이다.

주의: '정답'은 원작자의 리그일 뿐 해부학적 진리가 아니다. 리그마다 발목·어깨를 두는 관습이 달라서
절대 오차보다 '같은 자산에서 버전 간 오차가 커졌는가'를 보는 용도로 쓴다."""
import json
import re
import time
from pathlib import Path

from . import pipeline
from .blender import run_script
from .config import load
from .manifest import atomic_write

# 우리 변형 본 → 원본 뼈대 이름 후보(정규화된 핵심 이름). 앞에서부터 우선 매칭
JOINT_MAP = {
    "spine": ["hips", "pelvis"],
    "spine.004": ["neck"],
    "spine.006": ["head"],
    "shoulder": ["shoulder", "clavicle"],
    "upper_arm": ["upperarm", "arm"],
    "forearm": ["lowerarm", "forearm"],
    "hand": ["wrist", "hand"],
    "thigh": ["upperleg", "upleg", "thigh"],
    "shin": ["lowerleg", "leg", "shin", "calf"],
    "foot": ["foot", "ankle"],
}
SIDED = ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot")


def _norm(name: str) -> tuple[str, str | None]:
    """'mixamorig:LeftForeArm' → ('forearm', 'L'), 'UpperLeg.R' → ('upperleg', 'R')"""
    n = name.lower().split(":")[-1]
    side = None
    for pat, s in ((r"[._-]l$", "L"), (r"[._-]r$", "R"), (r"^left", "L"), (r"^right", "R"),
                   (r"left", "L"), (r"right", "R"), (r"[._-]l[._-]", "L"), (r"[._-]r[._-]", "R")):
        if re.search(pat, n):
            side = s; n = re.sub(pat, "", n); break
    return re.sub(r"[^a-z]", "", n), side


KEYWORDS = {k for v in JOINT_MAP.values() for k in v}
PREFIXES = ("mixamorig", "valvebiped", "bip01", "bip", "def", "org", "ctrl", "j", "cc", "ch", "character", "root")


def _cores(core: str) -> set[str]:
    """리그마다 붙이는 접두사를 벗긴다. 벗긴 결과가 우리가 아는 관절 이름일 때만 인정한다
    (예: Bip01_L_UpperArm → bipupperarm → upperarm, VRM 의 J_Bip_L_UpperArm → jbipupperarm → upperarm)"""
    out = {core}
    for _ in range(3):   # 접두사가 겹쳐 붙은 경우(J_Bip_L_...)까지 단계적으로 벗긴다
        for c in list(out):
            for pre in PREFIXES:
                rest = c[len(pre):]
                if c.startswith(pre) and len(rest) >= 3:
                    out.add(rest)
    return out


def _gt_lookup(joints: dict) -> dict:
    """정답 뼈대를 (핵심이름, 좌우) → head 좌표로 뒤집는다"""
    out = {}
    for name, v in joints.items():
        core, side = _norm(name)
        for c in _cores(core):
            out.setdefault((c, side), v["head"])
    return out


def compare(ours: dict, gt_joints: dict, height: float) -> list[dict]:
    """우리 DEF 본과 정답 관절을 짝지어 거리를 잰다"""
    look = _gt_lookup(gt_joints)
    rows = []
    for ours_base, cands in JOINT_MAP.items():
        for side in (("L", "R") if ours_base in SIDED else (None,)):
            our_name = f"DEF-{ours_base}" + (f".{side}" if side else "")
            if our_name not in ours:
                continue
            hit = next((look[(c, side)] for c in cands if (c, side) in look), None)
            if hit is None:
                rows.append({"joint": our_name, "gt": None, "error_cm": None}); continue
            a, b = ours[our_name]["head"], hit
            d = sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5
            rows.append({"joint": our_name, "ours": [round(v, 4) for v in a], "gt": [round(v, 4) for v in b],
                         "error_cm": round(d * 100, 2), "error_pct_height": round(d / height * 100, 2) if height else None})
    return rows


def run(root: Path, meshes: list[str], run_id: str | None = None, quiet: bool = False, facing: str = "auto") -> Path:
    cfg = load(root)
    run_id = run_id or time.strftime("bench-%Y%m%d-%H%M%S")
    out_dir = root / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results, csv = [], ["asset,joint,error_cm,error_pct_height,ours_x,ours_y,ours_z,gt_x,gt_y,gt_z"]
    for i, mesh in enumerate(meshes, 1):
        name = Path(mesh).stem
        row = {"asset": name, "mesh": str(mesh)}
        try:
            gt = run_script("gt_joints", {"mesh": str(Path(mesh).resolve()), "facing": facing}, cfg["blender"], out_dir / "logs")
            if not gt.get("joints"):
                row["error"] = "원본 뼈대 없음 — 벤치마크 대상이 아니다"; results.append(row); continue
            rid = f"{run_id}-{name}"
            pipeline.rig(root, mesh, "humanoid", run_id=rid, quiet=True, no_judge=True, facing=facing)
            ours = run_script("dump_bones", {"blend": str(root / "runs" / rid / "02_rigged.blend")}, cfg["blender"], out_dir / "logs")["bones"]
            rows = compare(ours, gt["joints"], gt["height"])
            errs = [r["error_cm"] for r in rows if r.get("error_cm") is not None]
            row.update({"height": gt["height"], "gt_bones": gt["bones"], "matched": len(errs), "unmatched": len(rows) - len(errs),
                        "mean_cm": round(sum(errs) / len(errs), 2) if errs else None,
                        "median_cm": round(sorted(errs)[len(errs) // 2], 2) if errs else None,
                        "max_cm": round(max(errs), 2) if errs else None,
                        "worst": max(rows, key=lambda r: r.get("error_cm") or -1)["joint"] if errs else None,
                        "joints": rows})
            for r in rows:
                if r.get("error_cm") is not None:
                    csv.append(f"{name},{r['joint']},{r['error_cm']},{r['error_pct_height']}," +
                               ",".join(str(v) for v in r["ours"]) + "," + ",".join(str(v) for v in r["gt"]))
        except Exception as e:  # 자산 하나가 실패해도 나머지는 계속한다
            row["error"] = str(e).splitlines()[0][:160]
        results.append(row)
        if not quiet:
            s = row.get("error") or f"관절 {row.get('matched')}개 · 평균 {row.get('mean_cm')}cm · 최대 {row.get('max_cm')}cm ({row.get('worst')})"
            print(f"[bench {i}/{len(meshes)}] {name}: {s}", flush=True)
    ok = [r for r in results if r.get("mean_cm") is not None]
    summary = {"assets": len(results), "measured": len(ok),
               "mean_cm": round(sum(r["mean_cm"] for r in ok) / len(ok), 2) if ok else None,
               "worst_asset": max(ok, key=lambda r: r["max_cm"])["asset"] if ok else None}
    atomic_write(out_dir / "bench.json", json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))
    atomic_write(out_dir / "bench.csv", "\n".join(csv) + "\n")
    md = [f"# bonewright bench · {run_id}", "",
          f"- 자산 {summary['assets']}개 중 측정 {summary['measured']}개 · 전체 평균 오차 {summary['mean_cm']} cm · 최악 자산 {summary['worst_asset']}",
          "- '정답'은 원작자의 리그다(해부학적 진리가 아니다). 버전 간 회귀 탐지용으로 읽어라.", "",
          "| 자산 | 키(m) | 관절 | 평균(cm) | 중앙값(cm) | 최대(cm) | 최악 관절 |", "|---|---|---|---|---|---|---|"]
    for r in results:
        if r.get("error"):
            md.append(f"| {r['asset']} | - | - | - | - | - | {r['error']} |")
        else:
            md.append(f"| {r['asset']} | {r['height']} | {r['matched']} | {r['mean_cm']} | {r['median_cm']} | {r['max_cm']} | {r['worst']} |")
    atomic_write(out_dir / "report.md", "\n".join(md) + "\n")
    if not quiet:
        print(f"\n요약: 측정 {summary['measured']}/{summary['assets']} · 평균 {summary['mean_cm']}cm → {out_dir / 'report.md'}")
    return out_dir / "report.md"
