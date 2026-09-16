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

    # 아래 세 비율은 정답 자산 11종(Quaternius 동물 10 + Khronos fox)의 원작자 뼈대에서 **실측한 규약**이다. 해부학 상수가 아니다.
    # 늑대 메타리그 한 종의 비율을 모든 동물에 쓰던 것이 사족 오차의 주범이었다(어깨 높이 18%·뒷다리 y 0.4~0.5m).
    SHOULDER_OVER_HIP = 0.80   # 어깨 높이 / 고관절 높이(등 높이를 못 재면 쓰는 대비책). 늑대 메타리그는 0.94, 정답 10종은 0.77~0.84
    # 등 높이 기준(있으면 우선): 그 자리 등 높이 × 비율. 정답 9~10종을 같은 띠 조건으로 실측 — 고관절 0.80±0.06, 어깨 0.635±0.04.
    # 총키 기준(0.59±0.08 / 0.49±0.08)보다 흩어짐이 절반이라, 목이 길거나(알파카) 뿔이 있는 체형에서 특히 낫다.
    # 남은 흩어짐은 체형 차이다(소 0.72 ↔ 말·사슴 0.87): '몸 두께의 일정 비율만큼 등 아래'라는 가설도 재 봤지만 0.35~0.76 으로 더 나빴다
    HIP_OVER_BACK, SHOULDER_OVER_BACK = 0.80, 0.635
    back_hind, back_front = L["quad"].get("back_hind_z"), L["quad"].get("back_front_z")

    HIP_AHEAD, KNEE_AHEAD, HOCK_BEHIND = 0.15, 0.26, 0.09   # 뒷발 기준 몸 길이 비율. 정답: 고관절 0.09~0.22 앞, 무릎 0.16~0.30 앞, 비절 0.09 뒤
    KNEE_DOWN, HOCK_DOWN = 0.274, 0.564   # 고관절→발끝 높이에서 내려온 비율. 무릎 ±0.019 로 가장 일정하다(11종 전부)
    # 앞다리만 두 무리로 갈린다: 개과는 팔꿈치가 높고(0.23~0.25) 다리가 뒤로 꺾이고, 발굽 동물은 중간 높이(0.46~0.53) 수직 기둥이다.
    # 메시에서 잰 '앞다리 기울기'로 어느 쪽인지 고른다(11종 전부 0.08 경계로 갈림) — 하나의 평균값을 쓰면 한쪽이 11~15% 틀린다
    dog_type = (L["quad"].get("front_lean") or 0.0) > 0.08
    ELBOW_DOWN = 0.24 if dog_type else 0.50
    ELBOW_DEV = 0.077 if dog_type else -0.02   # 어깨→발끝 직선에서 팔꿈치가 뒤로(+) 벗어나는 양, 몸 길이 비
    SHOULDER_BEHIND = 0.13 if dog_type else 0.02   # 어깨가 앞발보다 뒤에 있는 양(몸 길이 비). 정답: 개과 0.12~0.14, 발굽 0.00~0.05
    PELVIS_AHEAD = 0.08        # 골반(척추에서 뒷다리가 붙는 점): 정답 -0.01~-0.14(평균 0.084, 표준편차 0.043)
    PELVIS_ABOVE_HIP = 0.036   # 골반이 고관절보다 높은 양(키 비). 정답 0.007~0.172 중앙값 0.036 — 나머지는 리그 관습 차이다
    body_len = (th - tf) if abs(th - tf) > 1e-6 else None   # 뒷발 y − 앞발 y (앞이 -Y 라 양수)

    # 골반 앞뒤 자리: 메타리그 그대로면 골반이 뒷발보다 뒤(+0.13)에 서는데 정답은 앞(-0.08)이다. 척추를 통째로 옮기면 목·가슴까지
    # 밀리므로, 골반에서 최대로 밀고 어깨 쪽으로 가면서 0 이 되게 잦아들린다(z 는 건드리지 않는다 — 정답의 골반 높이는
    # 0.44~0.88 로 리그마다 제각각인 '루트 본 관습'이라 맞출 근거가 없다)
    # 골반 기준점은 '뒷다리가 붙는 척추 점'이다 — 늑대 메타리그에서 넙다리 본 머리(y 0.342)가 아니라 척추 점(y 0.408)이라
    # 넙다리 머리로 맞추면 몸 길이 배율만큼(개 자산에서 0.15m) 어긋난다. 척추 본 머리 중 넙다리 머리에 가장 가까운 점을 쓴다
    def spine_anchor():
        if "thigh.L" not in meta: return None
        h = meta["thigh.L"]["head"]
        cands = [v["head"] for n, v in meta.items() if n.startswith("spine")]
        if not cands: return None
        return min(cands, key=lambda p: sum((p[i] - h[i]) ** 2 for i in range(3)))
    _anchor = spine_anchor()
    pelvis_now = remap(_anchor)[1] if _anchor else None
    pelvis_now_z = remap(_anchor)[2] if _anchor else None
    sh_now = remap([0.0, meta["front_thigh.L"]["head"][1], 0.0])[1] if "front_thigh.L" in meta else None
    dy = dz = 0.0
    if body_len and pelvis_now is not None and sh_now is not None and abs(pelvis_now - sh_now) > 1e-6:
        dy = (th - PELVIS_AHEAD * body_len) - pelvis_now
        # 골반 높이: 정답의 '골반 본' 높이는 리그 관습이라 0.44~0.88 로 제각각이지만, **고관절 바로 위 얼마**인지는 덜 흩어진다
        # (키의 0.7~17%, 중앙값 3.6%). 고관절 목표 높이 + 3.6% 에 두고, 어깨 쪽으로 가면서 0 으로 잦아들린다
        if back_hind and pelvis_now_z is not None:
            dz = (HIP_OVER_BACK * back_hind + PELVIS_ABOVE_HIP * L["height"]) - pelvis_now_z
    def taper(p):
        if not dy and not dz: return p
        t = min(1.0, max(0.0, (p[1] - sh_now) / (pelvis_now - sh_now)))   # 골반에서 1, 어깨에서 0
        return [p[0], p[1] + dy * t, p[2] + dz * t]

    out = []
    # 척추도 같이 옮긴다. 안 옮기면 몸통이 메타리그 길이 그대로 남아 골반이 꼬리 쪽에 박힌다
    for n, v in meta.items():
        # pelvis.L/R(엉덩이 벌어짐 본)은 척추 골반 점에 붙어 있다 — 같이 안 옮기면 골반만 움직여 살 밖으로 튀어나온다(게이트 실패로 확인)
        # breast.L/R(가슴 본)도 갈비뼈에 붙어 있어 척추와 같이 움직여야 한다(소에서 살 밖으로 남았다)
        if (n.startswith("spine") or n.startswith("pelvis.") or n.startswith("breast.")) and ky is not None:
            out.append({"name": n, "head": [round(x, 4) for x in taper(remap(v["head"]))],
                        "tail": [round(x, 4) for x in taper(remap(v["tail"]))]})
    hip_z = None
    hip_name = next((n for n in QCHAIN.get(("hind", "L"), ()) if n in meta), None)
    if hip_name:
        hip_z = remap(meta[hip_name]["head"])[2]
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
        sz = 1.0
        if A[2] > B[2]:
            want = None
            if key[0] == "front":
                want = SHOULDER_OVER_BACK * back_front if back_front else (SHOULDER_OVER_HIP * hip_z if hip_z is not None else None)
            elif back_hind:
                want = HIP_OVER_BACK * back_hind
            if want is not None:
                sz = max(0.4, min(1.6, (want - B[2]) / (A[2] - B[2])))
        def squash(p):   # 발끝(B)을 기준으로 z 만 누른다
            return [p[0], p[1], B[2] + (p[2] - B[2]) * sz]
        A = squash(A); span = A[2] - B[2]
        d = [target[i] - B[i] for i in range(3)]
        def moved(p):
            p = squash(p)
            t = min(1.0, max(0.0, (A[2] - p[2]) / span))   # 고관절에서 0, 발끝에서 1
            return [round(p[i] + d[i] * t, 4) for i in range(3)]
        placed = {n: {"head": moved(remap(meta[n]["head"])), "tail": moved(remap(meta[n]["tail"]))} for n in chain}
        # 사슬의 관절을 정답 규약 비율로 직접 놓는다(메타리그 모양 대신). pts[0]=고관절/어깨, pts[-1]=발끝, 사이가 관절이다.
        # 정답 10종 실측: 무릎은 고관절→발끝의 27.4%±1.9(거의 완벽히 일정), 비절 56.4%±6.3, 팔꿈치 42.7%±11.6.
        # 앞뒤(y)는 뒷다리만 규약이 뚜렷하다 — 무릎은 뒷발보다 몸길이의 0.26 앞, 비절은 0.09 뒤.
        # 앞다리는 어깨→발끝 직선에 무리별 굽힘(ELBOW_DEV)만 얹는다: 늑대 메타리그 그대로 두면 발굽 동물의 팔꿈치가 앞뒤로 0.72m 어긋난다(소)
        pts = [placed[chain[0]]["head"]] + [placed[n]["tail"] for n in chain]
        top, toe = pts[0], pts[-1]
        drop = top[2] - toe[2]
        if drop > 1e-6 and body_len:
            rules = ({0: (0.0, th - HIP_AHEAD * body_len), 1: (KNEE_DOWN, th - KNEE_AHEAD * body_len),
                      2: (HOCK_DOWN, th + HOCK_BEHIND * body_len)}
                     if key[0] == "hind" else {0: (0.0, tf + SHOULDER_BEHIND * body_len), 1: (ELBOW_DOWN, None)})
            for i, (dz_, y) in sorted(rules.items()):
                if 0 <= i < len(pts) - 1:
                    if i > 0:
                        pts[i][2] = round(top[2] - dz_ * drop, 4)
                    if y is not None:
                        pts[i][1] = round(y, 4)
            top, drop = pts[0], pts[0][2] - toe[2]   # 고관절/어깨 y 가 바뀌었으니 직선화 기준도 갱신
            if key[0] == "front":
                for i in range(1, len(pts) - 1):
                    t = min(1.0, max(0.0, (top[2] - pts[i][2]) / drop))
                    bend = ELBOW_DEV * body_len * (1.0 - abs(2.0 * t - 1.0))   # 팔꿈치(가운데)에서 최대, 어깨·발끝에서 0
                    pts[i][1] = round(top[1] + (toe[1] - top[1]) * t + bend, 4)
            for i, n in enumerate(chain):
                placed[n]["head"] = list(pts[i]); placed[n]["tail"] = list(pts[i + 1])
        for n in chain:
            out.append({"name": n, "head": placed[n]["head"], "tail": placed[n]["tail"]})
        # 어깨뼈(shoulder.L/R)는 앞다리의 부모다 — 앞다리를 옮겼으면 꼬리가 새 어깨 자리에 붙도록 통째로 따라와야 한다
        sh = f"shoulder.{key[1]}"
        if key[0] == "front" and sh in meta:
            o = remap(meta[sh]["tail"]); dlt = [pts[0][i] - o[i] for i in range(3)]
            out.append({"name": sh, "head": [round(remap(meta[sh]["head"])[i] + dlt[i], 4) for i in range(3)],
                        "tail": [round(pts[0][i], 4) for i in range(3)]})
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
            # 다리 중심선을 못 찾은 메시라도, 조각으로 만든 모델이면 조각 뭉치가 곧 마디다(analyze 의 foot_split).
            # 그게 있으면 사람 비율로 때운 값 대신 그걸 쓴다(로봇: x 0.08 → 0.635, 고관절 0.44 → 1.67, 정답 0.641 / 1.537)
            fs = L.get("foot_split") or {}
            lx = x * (fs["x"] if fs.get("x") else max(0.08, thw * 0.6))
            hz = fs.get("hip_z") or L["hip_z"]; kz = fs.get("knee_z") or L["knee_z"]; az = fs.get("ankle_z") or L["ankle_z"]
            t[f"thigh.{s}"] = {"head": [lx, y, hz], "tail": [lx, y, kz]}
            t[f"shin.{s}"] = {"head": [lx, y, kz], "tail": [lx, y, az]}
            t[f"foot.{s}"] = {"head": [lx, y, az], "tail": [lx, y - 0.12, L["ground_z"] + 0.02]}
        meta = json.loads(inputs["metarig_bones.json"])
        out = []
        for name, v in t.items():
            base = meta.get(name, {"head": [0, 0, 0], "tail": [0, 0, 0.05]})
            out.append({"name": name, "head": v.get("head", base["head"]), "tail": v.get("tail", base["tail"])})
        return {"targets": out, "reasoning": "mock: 랜드마크 비례 배치", "confidence": 0.5}
    if step == "judge":
        return {"bones_outside_mesh": [], "proportions_ok": True, "issues": [], "confidence": 0.5, "notes": "mock"}
    raise ValueError(step)
