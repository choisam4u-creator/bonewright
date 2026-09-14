"""테스트용 가짜 모델: 분석 랜드마크에서 기계적으로 목표 본 위치를 만든다(BW_BACKEND=mock)."""
import json


# 사족 다리 사슬(Rigify 늑대 메타리그 이름). 앞다리는 front_*, 뒷다리는 사람과 같은 이름을 쓴다
QCHAIN = {("front", s): [f"front_thigh.{s}", f"front_shin.{s}", f"front_foot.{s}", f"front_toe.{s}"] for s in ("L", "R")}
QCHAIN.update({("hind", s): [f"thigh.{s}", f"shin.{s}", f"foot.{s}", f"toe.{s}"] for s in ("L", "R")})


def _quad_fit(L, meta):
    """사족: 우리가 잰 건 '발 네 개의 바닥 위치'뿐이다(무릎·발목은 살 안쪽이라 표면에서 안 보인다).
    그래서 메타리그 다리 사슬의 발끝을 잰 발 자리로 옮기고, 사이 관절은 높이 비율대로 따라오게 한다.
    관절 비율을 지어내지 않고 Rigify 늑대 메타리그(실제 늑대를 본뜬 모델)에서 그대로 가져오는 셈이다."""
    feet = L["quad"]["feet"]

    def tip_y(names):
        for n in names:
            if n in meta: return meta[n]["tail"][1]
        return None
    # 몸 길이 맞추기: 메타리그는 키로만 균일 확대돼 몸 길이가 안 맞는다(늑대 메시에서 고관절 y 가 1.1 어긋났다).
    # 메타리그의 앞발끝~뒷발끝 y 범위를 우리가 잰 앞발~뒷발 y 범위에 포개면 고관절·어깨가 제자리를 찾는다
    mf, mh = tip_y(["front_toe.L", "front_foot.L"]), tip_y(["toe.L", "foot.L"])
    tf = (feet["front_L"][1] + feet["front_R"][1]) / 2
    th = (feet["hind_L"][1] + feet["hind_R"][1]) / 2
    ky = (tf - th) / (mf - mh) if (mf is not None and mh is not None and abs(mf - mh) > 1e-6) else None
    def remap(p):
        return p if ky is None else [p[0], th + (p[1] - mh) * ky, p[2]]

    out = []
    # 척추도 같이 옮긴다. 안 옮기면 몸통이 메타리그 길이 그대로 남아 골반이 꼬리 쪽에 박힌다
    for n, v in meta.items():
        if n.startswith("spine") and ky is not None:
            out.append({"name": n, "head": [round(x, 4) for x in remap(v["head"])],
                        "tail": [round(x, 4) for x in remap(v["tail"])]})
    for key, names in QCHAIN.items():
        chain = [n for n in names if n in meta]
        target = feet.get(f"{key[0]}_{key[1]}")
        if len(chain) < 2 or not target:
            continue
        A = remap(meta[chain[0]]["head"])   # 다리가 몸에 붙는 곳(고관절·어깨) — 몸 길이만 맞춘 자리
        B = remap(meta[chain[-1]]["tail"])  # 메타리그 발끝
        span = A[2] - B[2]
        if abs(span) < 1e-6:
            continue
        d = [target[i] - B[i] for i in range(3)]
        def moved(p):
            t = min(1.0, max(0.0, (A[2] - p[2]) / span))   # 고관절에서 0, 발끝에서 1
            return [round(p[i] + d[i] * t, 4) for i in range(3)]
        for n in chain:
            out.append({"name": n, "head": moved(remap(meta[n]["head"])), "tail": moved(remap(meta[n]["tail"]))})
    return {"targets": out, "reasoning": "mock 사족: 잰 발 위치에 메타리그 다리 사슬을 심는다", "confidence": 0.5}


def mock_backend(step: str, prompt: str, inputs: dict) -> dict:
    if step == "fit":
        a = json.loads(inputs["analysis.json"]); L = a["landmarks"]
        if L.get("quad", {}).get("ok"):
            return _quad_fit(L, json.loads(inputs["metarig_bones.json"]))
        sw, y = L["shoulder_halfwidth"], 0.0
        meta0 = json.loads(inputs["metarig_bones.json"])
        t = {"spine": {"head": [0, y, L["hip_z"]], "tail": meta0.get("spine", {"tail": [0, y, L["hip_z"] + 0.1]})["tail"]}}   # 척추·목·머리는 균일 스케일에 맡긴다
        thw, tx, tz = L["torso_halfwidth"], L["arm_tip_x"], L["arm_tip_z"]
        for s, x in (("L", 1), ("R", -1)):
            ax = L.get(f"arm_axis_{s}") or []
            if len(ax) >= 4:   # 중심선 표본 위에 배치: 어깨=첫 표본, 팔꿈치 45%, 손목 82%, 손끝 97%
                pts = [p[:3] for p in ax]
                seg = [((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2 + (pts[i + 1][2] - pts[i][2]) ** 2) ** 0.5 for i in range(len(pts) - 1)]
                total = sum(seg)
                def at(f):
                    d = f * total
                    for i, ln in enumerate(seg):
                        if d <= ln or i == len(seg) - 1:
                            k = min(1.0, d / ln) if ln else 0
                            return [round(pts[i][j] + (pts[i + 1][j] - pts[i][j]) * k, 3) for j in range(3)]
                        d -= ln
                sh, el, wr, tip = at(0.0), at(0.45), at(0.82), at(0.97)
            else:
                sh = [x * thw * 0.8, y, L["shoulder_z"]]; tip = [x * (tx - 0.02), y, tz]
                mid = lambda a, b, f: [a[0] + (b[0] - a[0]) * f, y, a[2] + (b[2] - a[2]) * f]
                el, wr = mid(sh, tip, 0.45), mid(sh, tip, 0.85)
            t[f"shoulder.{s}"] = {"head": [x * 0.04, y, L["shoulder_z"] + 0.02], "tail": sh}
            t[f"upper_arm.{s}"] = {"head": sh, "tail": el}
            t[f"forearm.{s}"] = {"head": el, "tail": wr}
            t[f"hand.{s}"] = {"head": wr, "tail": tip}
            lx = x * max(0.08, thw * 0.6)
            t[f"thigh.{s}"] = {"head": [lx, y, L["hip_z"]], "tail": [lx, y, L["knee_z"]]}
            t[f"shin.{s}"] = {"head": [lx, y, L["knee_z"]], "tail": [lx, y, L["ankle_z"]]}
            t[f"foot.{s}"] = {"head": [lx, y, L["ankle_z"]], "tail": [lx, y - 0.12, L["ground_z"] + 0.02]}
        meta = json.loads(inputs["metarig_bones.json"])
        out = []
        for name, v in t.items():
            base = meta.get(name, {"head": [0, 0, 0], "tail": [0, 0, 0.05]})
            out.append({"name": name, "head": v.get("head", base["head"]), "tail": v.get("tail", base["tail"])})
        return {"targets": out, "reasoning": "mock: 랜드마크 비례 배치", "confidence": 0.5}
    if step == "judge":
        return {"bones_outside_mesh": [], "proportions_ok": True, "issues": [], "confidence": 0.5, "notes": "mock"}
    raise ValueError(step)
