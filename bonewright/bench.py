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
from .i18n import T
from .manifest import atomic_write

# 우리 변형 본 → 원본 뼈대 이름 후보(정규화된 핵심 이름). 앞에서부터 우선 매칭
JOINT_MAP = {
    # Godot 데모는 단수형 hip 을 쓴다. "spine" 은 맨 뒤다 — 골반 이름이 따로 있으면 그쪽이 먼저 잡히고,
    # 없을 때만(Rigify 로 리깅된 파일을 다시 읽을 때) 척추 밑동을 골반으로 본다
    "spine": ["hips", "hip", "pelvis", "spine"],
    "spine.004": ["neck"],
    "spine.006": ["head"],
    "shoulder": ["shoulder", "clavicle", "shldr", "collar"],   # DAZ 는 lShldr / lCollar 로 쓴다
    # 숫자 체인 규약(CesiumMan 의 arm_joint_L_1/2/3)은 번호로 어깨·팔꿈치·손목을 구분한다 → 번호 붙은 후보를 먼저 본다
    "upper_arm": ["upperarm", "armjoint1", "arm1", "arm"],
    "forearm": ["lowerarm", "forearm", "armjoint2", "arm2"],
    # 손목 이름이 없고 손바닥만 있는 리그가 있다(three.js RobotExpressive: LowerArm → Palm1/2/3).
    # "palm" 을 맨 뒤에 두어 진짜 손목이 있으면 그쪽이 먼저 잡히게 한다
    "hand": ["wrist", "hand", "armjoint3", "arm3", "palm"],
    "thigh": ["upperleg", "upleg", "thigh", "legjoint1", "leg1"],
    "shin": ["lowerleg", "shin", "calf", "legjoint2", "leg2", "leg"],
    "foot": ["foot", "ankle", "legjoint3", "leg3"],
}
SIDED = ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot",
         "front_thigh", "front_shin", "front_foot")
# 사족(늑대 메타리그): 앞다리는 front_*, 뒷다리는 사람과 같은 이름을 쓴다.
# 사족 원본 리그는 앞다리를 보통 팔 이름(LeftUpperArm)으로 부른다
# Quaternius 동물 규약(BackLeg/BackUpperLeg/…)은 이름이 관절보다 한 칸씩 밀려 있다. 이름이 아니라
# 실제 본 좌표로 확인했다(늑대, Y 가 위, 바닥 y≈0.07): BackLeg 1.76=고관절 · BackUpperLeg 1.34=무릎 ·
# BackLowerLeg 0.82=비절, FrontUpperLeg 1.46=어깨 · FrontLowerLeg 1.12=팔꿈치. 그래서 아래처럼 붙인다.
# 앞발은 이 규약에 대응 본이 없다(FrontLowerLeg 가 발까지 한 본이다) → 매칭 없이 남는다
QUAD_MAP = {
    # 늑대 메타리그에서 'spine' 은 골반이 아니라 꼬리 밑동이다(y=+0.96, 고관절은 +0.34) — 골반 높이의 본은 spine.003 이다.
    # 게다가 Rigify 는 늑대 척추를 두 사슬로 쪼개면서 DEF 번호를 한 칸 민다(목표 없이 생성해 확인:
    # 메타 spine~spine.003 → DEF-spine.001~004, spine.004 부터는 번호가 일치). 그래서 골반은 DEF-spine.004 다.
    # 이걸 틀리면 우리 오차가 아니라 본 이름 관습 차이가 숫자로 찍힌다(DEF-spine 으로 맞댔을 때 102%)
    "spine.004": ["hips", "hip", "pelvis", "root", "back"],   # Quaternius 는 골반을 Back 이라 부른다(Body 는 아마추어 원점이라 뺀다)
    "front_thigh": ["upperarm", "arm1", "arm", "frontupperleg"],
    "front_shin": ["lowerarm", "forearm", "arm2", "frontlowerleg"],
    "front_foot": ["wrist", "hand", "arm3"],
    "thigh": ["upperleg", "upleg", "thigh", "leg1", "backleg"],
    "shin": ["lowerleg", "shin", "calf", "leg2", "leg", "backupperleg"],
    "foot": ["foot", "ankle", "leg3", "backlowerleg"],
}


def _norm(name: str) -> tuple[str, str | None]:
    """'mixamorig:LeftForeArm' → ('forearm', 'L'), 'UpperLeg.R' → ('upperleg', 'R')"""
    n = name.lower().split(":")[-1]
    side = None
    n = re.sub(r"[._-]?\d+$", "", n)   # 끝의 번호는 의미 없다(b_LeftUpperArm_09)
    for pat, s in ((r"[._-]l$", "L"), (r"[._-]r$", "R"), (r"^l[._-]", "L"), (r"^r[._-]", "R"),
                   (r"^left", "L"), (r"^right", "R"), (r"left", "L"), (r"right", "R"),
                   (r"[._-]l[._-]", "L"), (r"[._-]r[._-]", "R")):
        if re.search(pat, n):
            side = s; n = re.sub(pat, "", n); break
    core = re.sub(r"[^a-z]", "", n)
    # DAZ 규약은 구분자 없이 l/r 을 앞에 붙인다(lShldr, lForeArm). 'leg' 의 l 까지 떼면 안 되므로,
    # 떼고 남은 것이 **우리가 아는 관절 이름일 때만** 좌우로 인정한다
    if side is None and len(core) > 3 and core[0] in "lr" and core not in KEYWORDS:
        rest = core[1:]
        if rest in KEYWORDS or (_cores(rest) & KEYWORDS):
            return rest, ("L" if core[0] == "l" else "R")
    return core, side


KEYWORDS = {k for v in JOINT_MAP.values() for k in v}
PREFIXES = ("mixamorig", "valvebiped", "bip01", "bip", "def", "org", "ctrl", "skeleton", "b", "j", "cc", "ch", "character", "root", "base")
DECOR = ("joint", "jnt", "bind", "bone", "ctrl", "skin", "twist")   # 뼈 이름에 붙는 장식어


def _cores(core: str) -> set[str]:
    """리그마다 붙이는 접두사를 벗긴다. 벗긴 결과가 우리가 아는 관절 이름일 때만 인정한다
    (예: Bip01_L_UpperArm → bipupperarm → upperarm, VRM 의 J_Bip_L_UpperArm → jbipupperarm → upperarm)"""
    out = {core}
    for d in DECOR:
        if core.endswith(d) and len(core) - len(d) >= 3: out.add(core[:-len(d)])
        if core.startswith(d) and len(core) - len(d) >= 3: out.add(core[len(d):])
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
        m = re.search(r"(\d+)$", name)   # 끝 번호(체인 순서). 의미 없는 인덱스일 수도 있어 별도 키로만 등록한다
        idx = str(int(m.group(1))) if m else ""
        for c in _cores(core):
            out.setdefault((c, side), v["head"])
            if idx:
                out.setdefault((c + idx, side), v["head"])
    return out


def compare(ours: dict, gt_joints: dict, height: float, preset: str = "humanoid") -> list[dict]:
    """우리 DEF 본과 정답 관절을 짝지어 거리를 잰다"""
    joint_map = QUAD_MAP if preset == "quadruped" else JOINT_MAP
    look = _gt_lookup(gt_joints)
    # 골반 관습 차이 걸러내기: 어떤 리그는 Hips 본을 아래로 그린다(머리가 넙다리 관절보다 한참 아래).
    # 그런 리그에서 Hips 를 골반으로 비교하면 우리 오차가 아니라 관습 차이가 숫자로 찍힌다 → 비교에서 뺀다
    pelvis_key = "spine" if "spine" in joint_map else "spine.004"   # 사족 골반은 DEF-spine.004 (위 주석 참고)
    pelvis = next((look[(c, None)] for c in joint_map[pelvis_key] if (c, None) in look), None)
    thighs = [look[(c, s)] for c in joint_map["thigh"] for s in ("L", "R") if (c, s) in look]
    if pelvis and thighs and height:
        if pelvis[2] < min(t[2] for t in thighs) - height * 0.05:
            for c in joint_map[pelvis_key]:
                look.pop((c, None), None)
    # 좌우는 **이름이 아니라 좌표 부호**로 정한다. 가져오기가 메시를 180° 돌리면 원본의 'Left' 본이 우리 -X 로 가서,
    # 이름만 믿고 맞대면 우리 왼다리를 원본 오른다리와 비교하게 된다 — 멀쩡한 리그가 다리 너비만큼 틀린 것으로 찍힌다
    # (RobotExpressive: DEF-thigh.L 실제 오차 13cm 인데 128cm 로 나왔다)
    for base in joint_map:
        if base not in SIDED:
            continue
        for c in joint_map[base]:
            l, r = look.get((c, "L")), look.get((c, "R"))
            if l and r and l[0] < r[0]:
                look[(c, "L")], look[(c, "R")] = r, l
    rows = []
    for ours_base, cands in joint_map.items():
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


DEF_SUB = re.compile(r"\.\d{3}$")   # Rigify 가 변형 본을 반으로 쪼개며 붙이는 꼬리(DEF-shin.L.001)


def _our_base(name: str) -> tuple[str, str | None]:
    """'DEF-shin.L.001' → ('shin', 'L'), 'DEF-spine.006' → ('spine.006', None).
    메타리그 번호(spine.006)는 의미가 있으니 남기고, 쪼개기 꼬리(.001)만 뗀다 —
    둘 다 '.001' 꼴이라 좌우 표시가 그 앞에 있는지로 가른다"""
    n = name[4:] if name.startswith("DEF-") else name
    side = None
    m = re.search(r"\.([LR])(?:\.\d{3})?$", n)
    if m:
        side = m.group(1)
        n = n[:m.start()]
    else:
        n = DEF_SUB.sub("", n) if re.search(r"\.[LR]\.", n) else n
    return n, side


def skin_score(pairs: list, preset: str = "humanoid") -> dict:
    """스키닝 일치도: '이 정점을 주로 움직이는 본'이 원본과 같은가.
    이름 규약이 리그마다 달라 그대로는 못 맞대므로 _norm/_cores 로 핵심 이름까지 벗겨서 비교한다.
    옮길 수 없는 이름(원본에만 있는 보조 본 등)은 분모에서 빼고 mapped 로 따로 보고한다 —
    비교가 안 된 걸 '틀렸다'로 세면 숫자가 거짓말이 된다."""
    joint_map = QUAD_MAP if preset == "quadruped" else JOINT_MAP
    want = {}   # 정규화된 원본 이름 → 우리 본 기준이름
    for base, cands in joint_map.items():
        for c in cands:
            want[c] = base
    agree = side_ok = mapped = 0
    for pair in pairs:
        ours_name, gt_name = pair[0], pair[1]   # skin_compare 는 [우리 본, 원본 본] 두 칸(예전 형식은 거리까지 세 칸)
        gcore, gside = _norm(gt_name)
        gbase = next((want[c] for c in _cores(gcore) if c in want), None)
        if gbase is None:
            continue
        obase, oside = _our_base(ours_name)
        mapped += 1
        if gside == oside:
            side_ok += 1
            if obase == gbase:
                agree += 1
    n = len(pairs) or 1
    return {"verts_compared": len(pairs), "mapped": round(mapped / n, 3),
            "agree": round(agree / mapped, 3) if mapped else None,
            "agree_side": round(side_ok / mapped, 3) if mapped else None}


def run(root: Path, meshes: list[str], run_id: str | None = None, quiet: bool = False, facing: str = "auto",
        preset: str = "humanoid", skin: bool = False, weights: str | None = None, rest_pose: str | None = None,
        gt_mesh: str | None = None) -> Path:
    cfg = load(root)
    run_id = run_id or time.strftime("bench-%Y%m%d-%H%M%S")
    out_dir = root / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results, csv = [], ["asset,joint,error_cm,error_pct_height,ours_x,ours_y,ours_z,gt_x,gt_y,gt_z"]
    for i, mesh in enumerate(meshes, 1):
        name = Path(mesh).stem
        row = {"asset": name, "mesh": str(mesh)}
        try:
            # gt_mesh: 정답을 '다른 파일'에서 가져온다 — 포즈를 바꾼 변형본(A 포즈)을 원본 T 포즈 뼈대와 맞대려고 쓴다
            gt = run_script("gt_joints", {"mesh": str(Path(gt_mesh or mesh).resolve()), "facing": facing, "preset": preset}, cfg["blender"], out_dir / "logs")
            if not gt.get("joints"):
                row["error"] = T("원본 뼈대 없음 — 벤치마크 대상이 아니다", "no skeleton of its own — not a benchmark asset"); results.append(row); continue
            rid = f"{run_id}-{name}"
            pipeline.rig(root, mesh, preset, run_id=rid, quiet=True, no_judge=True, facing=facing, force=True, weights=weights,
                         rest_pose=rest_pose)   # 벤치는 거절 대상도 재야 회귀를 본다
            ours = run_script("dump_bones", {"blend": str(root / "runs" / rid / "02_rigged.blend")}, cfg["blender"], out_dir / "logs")["bones"]
            rows = compare(ours, gt["joints"], gt["height"], preset)
            errs = [r["error_cm"] for r in rows if r.get("error_cm") is not None]
            row.update({"height": gt["height"], "gt_bones": gt["bones"], "matched": len(errs), "unmatched": len(rows) - len(errs),
                        "mean_cm": round(sum(errs) / len(errs), 2) if errs else None,
                        "median_cm": round(sorted(errs)[len(errs) // 2], 2) if errs else None,
                        "max_cm": round(max(errs), 2) if errs else None,
                        "worst": max(rows, key=lambda r: r.get("error_cm") or -1)["joint"] if errs else None,
                        "joints": rows})
            if skin:   # 스키닝도 잰다(토큰 0). 관절만 맞고 가중치가 엉망이면 쓸 수 없다
                try:
                    sc = run_script("skin_compare", {"mesh": str(Path(mesh).resolve()),
                                                     "blend": str(root / "runs" / rid / "02_rigged.blend"),
                                                     "facing": facing, "preset": preset}, cfg["blender"], out_dir / "logs")
                    row["skin"] = skin_score(sc.get("pairs") or [], preset)
                    row["skin"]["influence"] = sc.get("influence")   # 위치 지표(이름 규약과 무관): 영향 중심 거리
                    row["skin"]["regions"] = sc.get("regions")       # 부위별(손·발·팔·다리·머리·몸통) — 어디를 고쳐야 하는지
                except Exception as e:
                    row["skin"] = {"error": str(e).splitlines()[0][:120]}
            for r in rows:
                if r.get("error_cm") is not None:
                    csv.append(f"{name},{r['joint']},{r['error_cm']},{r['error_pct_height']}," +
                               ",".join(str(v) for v in r["ours"]) + "," + ",".join(str(v) for v in r["gt"]))
        except Exception as e:  # 자산 하나가 실패해도 나머지는 계속한다
            row["error"] = str(e).splitlines()[0][:160]
        results.append(row)
        if not quiet:
            s = row.get("error") or T(f"관절 {row.get('matched')}개 · 평균 {row.get('mean_cm')}cm · 최대 {row.get('max_cm')}cm ({row.get('worst')})",
                                      f"{row.get('matched')} joints · mean {row.get('mean_cm')}cm · max {row.get('max_cm')}cm ({row.get('worst')})")
            sk = row.get("skin") or {}
            if sk.get("agree") is not None:
                s += T(f" · 스키닝 일치 {round(sk['agree'] * 100, 1)}%(매핑 {round(sk['mapped'] * 100)}%)",
                       f" · skin agreement {round(sk['agree'] * 100, 1)}% (mapped {round(sk['mapped'] * 100)}%)")
            inf = sk.get("influence") or {}
            if inf.get("mean_cm") is not None:
                s += T(f" · 영향중심 {inf['mean_cm']}cm(키의 {inf['mean_pct_height']}%, 10%초과 {round(inf['frac_over_10pct'] * 100)}%)",
                       f" · influence centre {inf['mean_cm']}cm ({inf['mean_pct_height']}% of height, {round(inf['frac_over_10pct'] * 100)}% over 10%)")
            print(f"[bench {i}/{len(meshes)}] {name}: {s}", flush=True)
    ok = [r for r in results if r.get("mean_cm") is not None]
    summary = {"assets": len(results), "measured": len(ok),
               "mean_cm": round(sum(r["mean_cm"] for r in ok) / len(ok), 2) if ok else None,
               "worst_asset": max(ok, key=lambda r: r["max_cm"])["asset"] if ok else None}
    summary["preset"] = preset
    atomic_write(out_dir / "bench.json", json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))
    atomic_write(out_dir / "bench.csv", "\n".join(csv) + "\n")
    md = [f"# bonewright bench · {run_id}", "",
          T(f"- 자산 {summary['assets']}개 중 측정 {summary['measured']}개 · 전체 평균 오차 {summary['mean_cm']} cm · 최악 자산 {summary['worst_asset']}",
            f"- measured {summary['measured']} of {summary['assets']} assets · overall mean error {summary['mean_cm']} cm · worst asset {summary['worst_asset']}"),
          T("- '정답'은 원작자의 리그다(해부학적 진리가 아니다). 버전 간 회귀 탐지용으로 읽어라.",
            "- The 'reference' is the original author's rig, not anatomical truth. Read this to catch regressions between versions."), "",
          T("| 자산 | 키(m) | 관절 | 평균(cm) | 중앙값(cm) | 최대(cm) | 최악 관절 |", "| Asset | Height (m) | Joints | Mean (cm) | Median (cm) | Max (cm) | Worst joint |"),
          "|---|---|---|---|---|---|---|"]
    for r in results:
        if r.get("error"):
            md.append(f"| {r['asset']} | - | - | - | - | - | {r['error']} |")
        else:
            md.append(f"| {r['asset']} | {r['height']} | {r['matched']} | {r['mean_cm']} | {r['median_cm']} | {r['max_cm']} | {r['worst']} |")
    atomic_write(out_dir / "report.md", "\n".join(md) + "\n")
    if not quiet:
        print(T(f"\n요약: 측정 {summary['measured']}/{summary['assets']} · 평균 {summary['mean_cm']}cm → {out_dir / 'report.md'}",
                f"\nsummary: measured {summary['measured']}/{summary['assets']} · mean {summary['mean_cm']}cm → {out_dir / 'report.md'}"))
    return out_dir / "report.md"
