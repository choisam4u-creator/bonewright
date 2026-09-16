"""원본 뼈대 → 메타리그 목표(토큰 0).

파일에 이미 뼈대가 들어 있으면 관절을 다시 찾을 필요가 없다 — 원작자가 이미 찍어 놓았다. 그 관절을 그대로 받아
Rigify 메타리그 이름으로 옮기면, 실루엣으로는 관절을 못 찾는 캐릭터(로봇·양식화·앉은 자세)도 리깅할 수 있다.
얻는 것은 위치가 아니라 **조작 장치**다: IK/FK, 동작 리타겟, 게임용 변형 본만 내보내기.

이름 대조는 벤치마크가 쓰는 규약 사전(JOINT_MAP/QUAD_MAP)을 그대로 쓴다 — 자산 17종으로 다듬어 둔 것이다.
관절 좌표는 head 뿐 아니라 tail 도 받는다: 사슬 끝(손목·발목)이 원본에 없을 때 마지막 본의 tail 이 곧 그 끝이다
(Quaternius 동물은 FrontLowerLeg 한 본이 팔꿈치부터 발까지다 — tail 을 쓰면 앞발이 제자리에 온다)."""
import re

# 손가락: 원본에 마디가 있으면 그대로 받는다. 이름 규약이 제각각이라(index_01_l, LeftHandIndex1, Index2.L, f_index.02.L)
# 손가락 이름 **뒤에 오는 첫 숫자**를 마디 번호로 읽는다. 번호가 없으면 1 번이다(RobotExpressive 의 Thumb / Thumb2)
FINGERS = {"thumb": "thumb", "index": "f_index", "middle": "f_middle", "ring": "f_ring",
           "pinky": "f_pinky", "little": "f_pinky"}
PALM_OF = {"f_index": "palm.01", "f_middle": "palm.02", "f_ring": "palm.03", "f_pinky": "palm.04"}

# 사족 전용 추가 대응(QUAD_MAP 에 없는 것)
QUAD_EXTRA = {"neck": ["neck"], "head": ["head"], "shoulder": ["frontshoulder", "shoulder", "clavicle"]}
# 늑대 메타리그 사슬: 골반에서 앞쪽(등→목→머리)과 뒤쪽(꼬리)으로 갈라진다
WOLF_BACK = ["spine.004", "spine.005", "spine.006", "spine.007", "spine.008"]
WOLF_NECK = ["spine.009", "spine.010"]
WOLF_TAIL = ["spine.003", "spine.002", "spine.001", "spine"]


def _lookup(joints: dict) -> dict:
    """원본 뼈대를 (핵심이름, 좌우) → {head, tail} 로 뒤집는다. 끝 번호는 별도 키로도 등록한다(Tail1, Neck2 …)"""
    from .bench import _cores, _norm
    out = {}
    for name, v in joints.items():
        core, side = _norm(name)
        m = re.search(r"(\d+)$", name)
        idx = str(int(m.group(1))) if m else ""
        w = {**v, "name": name}
        for c in _cores(core):
            out.setdefault((c, side), w)
            if idx:
                out.setdefault((c + idx, side), w)
    return out


def _lerp(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def targets_from_skeleton(joints: dict, preset: str = "humanoid", height: float = 1.8, ground: float = 0.0) -> tuple[dict, dict]:
    """정답 뼈대 관절 → {메타리그 본: {head, tail}} 과 진단 정보. 못 찾은 본은 빼고 돌려준다(메타리그 기본값이 남는다)."""
    from .bench import JOINT_MAP, QUAD_MAP, SIDED   # bench 가 pipeline 을 부르므로 늦게 들여온다(순환 방지)
    quad = preset == "quadruped"
    jm = {**QUAD_MAP, **QUAD_EXTRA} if quad else JOINT_MAP
    look = _lookup(joints)
    found, missing = {}, []

    def at(base, side=None, part="head"):
        for c in jm.get(base, []):
            v = look.get((c, side))
            if v:
                return v["name"] if part == "name" else list(v[part])
        return None

    def path(end, stop):
        """원본 뼈대의 부모 사슬을 stop 본에서 end 본까지 따라가며 마디 점을 모은다.
        등뼈·꼬리는 곧은 선이 아니라 휘어 있어서, 양 끝만 이으면 본이 몸 밖으로 나간다"""
        if not (end and stop):
            return None
        seq, n = [], end
        while n and n != stop:
            seq.append(n); n = joints.get(n, {}).get("parent")
        if n != stop:
            return None
        return [list(joints[stop]["head"])] + [list(joints[m]["head"]) for m in reversed(seq)]

    # 0) 몸 한가운데 x. 메시에 의자·소품이 붙어 있으면 가져오기가 맞춘 x=0 이 몸의 한가운데가 아니다
    # (kira: 의자까지 합쳐 중심을 잡아 몸통이 x=+0.24 에 있다) → 좌우 판정·거울 반사는 이 값을 기준으로 한다
    center = [at(b)[0] for b in jm if b not in SIDED and at(b)]
    mx = sum(center) / len(center) if center else 0.0

    # 1) 관절 좌표 모으기. 좌우는 **이름이 아니라 좌표 부호**로 정한다 — 가져오기가 메시를 180° 돌리면
    # 원본의 'Left' 본이 우리 좌표에서 -X 로 가서, 이름만 믿으면 팔다리가 가위처럼 교차한다(로봇 렌더로 확인)
    def mirror(p_):
        return [2 * mx - p_[0], p_[1], p_[2]]
    pos, tail_of, mirrored = {}, {}, []
    for base in jm:
        if base in SIDED:
            cands = [(at(base, s), at(base, s, "tail")) for s in ("L", "R")]
            cands = [c for c in cands if c[0]]
            if len(cands) == 2:
                cands.sort(key=lambda q: -q[0][0])   # x 가 큰 쪽이 우리 기준 왼쪽(+X)
                for key, (h, t) in zip((f"{base}.L", f"{base}.R"), cands):
                    pos[key], tail_of[key] = h, t
            elif len(cands) == 1:
                # 한쪽만 있는 뼈대(반쪽만 리깅한 자산)는 몸 한가운데를 기준으로 비춰서 채운다
                h, t = cands[0]
                key, other = (f"{base}.L", f"{base}.R") if h[0] >= mx else (f"{base}.R", f"{base}.L")
                pos[key], tail_of[key] = h, t
                pos[other], tail_of[other] = mirror(h), (mirror(t) if t else None)
                mirrored.append(other)
            else:
                missing += [f"{base}.L", f"{base}.R"]
        else:
            h = at(base)
            if h:
                pos[base], tail_of[base] = h, at(base, part="tail")
            else:
                missing.append(base)

    # 1b) 사슬 끝이 비면 앞 마디의 tail 을 쓴다. tail 도 못 믿을 때만 방향으로 이어 붙인다.
    # 안 그러면 그 본이 메타리그 기본 자리에 남아 몸을 가로지르는 막대가 된다(로봇에는 손목 관절이 없었다 — 렌더로 확인)
    def extend(prev_key, cur_key, new_key, frac):
        a, b, t = pos.get(prev_key), pos.get(cur_key), tail_of.get(cur_key)
        if not (a and b) or new_key in pos:
            return
        far = sum((t[i] - b[i]) ** 2 for i in range(3)) ** 0.5 if t else 0.0
        seg = sum((b[i] - a[i]) ** 2 for i in range(3)) ** 0.5
        pos[new_key] = list(t) if far > seg * 0.2 else [b[i] + (b[i] - a[i]) * frac for i in range(3)]
        if new_key in missing:
            missing.remove(new_key)
    for side in ("L", "R"):
        if quad:
            extend(f"front_thigh.{side}", f"front_shin.{side}", f"front_foot.{side}", 0.8)
        else:
            extend(f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}", 0.85)   # 팔뚝 길이의 85% 가 손목~손끝
        extend(f"thigh.{side}", f"shin.{side}", f"foot.{side}", 0.9)

    # 2) 사슬을 '이 관절 → 다음 관절' 선분으로 만든다
    def put(name, a, b):
        if a and b and any(abs(a[i] - b[i]) > 1e-6 for i in range(3)):
            found[name] = {"head": list(a), "tail": list(b)}

    def chain(names, pts):
        """이름 목록을 꺾은선 pts 위에 길이 비례로 나눠 놓는다(사슬이 끊기지 않게 앞 tail = 뒤 head)"""
        pts = [p for p in (pts or []) if p]
        seg = [sum((pts[i + 1][k] - pts[i][k]) ** 2 for k in range(3)) ** 0.5 for i in range(len(pts) - 1)]
        total = sum(seg)
        if len(pts) < 2 or total <= 0:
            return

        def at_t(t):
            d = t * total
            for i, ln in enumerate(seg):
                if d <= ln or i == len(seg) - 1:
                    return _lerp(pts[i], pts[i + 1], d / ln if ln else 0.0)
                d -= ln
        n = len(names)
        for i, nm in enumerate(names):
            put(nm, at_t(i / n), at_t((i + 1) / n))

    if quad:
        pelvis, neck, head = pos.get("spine.004"), pos.get("neck"), pos.get("head")
        pn, nn, hn = at("spine.004", part="name"), at("neck", part="name"), at("head", part="name")
        # 등: 골반 → 목 밑. 목·머리: 목 밑 → 머리. 정수리 쪽 마지막 마디는 머리 길이만큼 더 뻗는다
        chain(WOLF_BACK, path(nn, pn) or [pelvis, neck])
        chain(WOLF_NECK, path(hn, nn) or [neck, head])
        if head:
            tip = tail_of.get("head") or [head[i] + (head[i] - (neck or head)[i]) * 0.6 for i in range(3)]
            put("spine.011", head, tip)
        # 꼬리: 골반에서 마지막 꼬리 마디까지. Rigify 늑대 리그는 꼬리 사슬의 시작을 골반과 같은 점에 두라고 요구한다
        # (다른 데서 시작하면 "Bone 'spine.003': Cannot connect chain - disjoint" 로 생성이 통째로 실패한다 — 늑대로 확인).
        # 꼬리가 없는 자산(꼬리 없는 동물)은 메타리그 기본 꼬리를 그대로 둔다
        tn_ = next((look[("tail" + str(i), None)] for i in range(12, 0, -1) if ("tail" + str(i), None) in look), None)
        if tn_ and pelvis:
            chain(WOLF_TAIL, (path(tn_["name"], pn) or [pelvis]) + [list(tn_["tail"])])
        for side in ("L", "R"):
            put(f"shoulder.{side}", pos.get(f"shoulder.{side}"), pos.get(f"front_thigh.{side}"))
            for a, b in (("front_thigh", "front_shin"), ("front_shin", "front_foot"),
                         ("thigh", "shin"), ("shin", "foot")):
                put(f"{a}.{side}", pos.get(f"{a}.{side}"), pos.get(f"{b}.{side}"))
            for foot, toe in ((f"front_foot.{side}", f"front_toe.{side}"), (f"foot.{side}", f"toe.{side}")):
                ank = pos.get(foot)
                if not ank:
                    continue
                # 발바닥은 **바닥에 닿는다**. 동물 뼈대는 보통 발목 아래 본이 없어서(늑대: BackLowerLeg 가 비절에서
                # 끝난다) 앞 본 길이의 비율로 이으면 발이 73cm 공중에 뜬다 — 리타게팅에서 짐승이 떠다닌다
                tip = tail_of.get(foot) or ank
                paw = [tip[0], tip[1], ground]
                put(foot, ank, paw)
                put(toe, paw, [paw[0], paw[1] - height * 0.04, ground])
    else:
        # 척추: 골반(spine) ~ 목(spine.004) ~ 머리(spine.006) 사이를 고르게 나눈다 — 원본에 척추 마디가 몇 개든 상관없다
        pelvis, neck, head = pos.get("spine"), pos.get("spine.004"), pos.get("spine.006")
        pn, nn, hn = at("spine", part="name"), at("spine.004", part="name"), at("spine.006", part="name")
        chain(["spine", "spine.001", "spine.002", "spine.003"], path(nn, pn) or [pelvis, neck])
        chain(["spine.004", "spine.005"], path(hn, nn) or [neck, head])
        if head:
            put("spine.006", head, [head[0], head[1], head[2] + height * 0.12])
        for side in ("L", "R"):
            # 쇄골 관절이 없는 뼈대가 많다(Khronos CesiumMan 은 arm_joint_L_1 부터 시작한다). 그냥 두면 사람 비율
            # 기본 자리에 남아 메시 밖으로 나간다 → 어깨 높이에서 중심선 쪽 1/4 지점을 뿌리로 삼는다
            ua = pos.get(f"upper_arm.{side}")
            sh = pos.get(f"shoulder.{side}") or ([ua[0] * 0.25, ua[1], ua[2]] if ua else None)
            put(f"shoulder.{side}", sh, ua)
            for a, b in (("upper_arm", "forearm"), ("forearm", "hand"), ("thigh", "shin"), ("shin", "foot")):
                put(f"{a}.{side}", pos.get(f"{a}.{side}"), pos.get(f"{b}.{side}"))
            hand = pos.get(f"hand.{side}")
            if hand:   # 손끝은 원본에 없을 수 있다 → 팔뚝 방향으로 손 길이만큼 뻗는다
                fa = pos.get(f"forearm.{side}")
                d = [hand[j] - fa[j] for j in range(3)] if fa else [0, 0, -height * 0.05]
                ln = sum(x * x for x in d) ** 0.5 or 1.0
                put(f"hand.{side}", hand, [hand[j] + d[j] / ln * height * 0.06 for j in range(3)])
            foot = pos.get(f"foot.{side}")
            if foot:   # 발끝: 앞(-Y)으로 발 길이만큼
                a_ = [foot[0], foot[1] - height * 0.07, max(0.0, foot[2] - height * 0.04)]
                put(f"foot.{side}", foot, a_)
                put(f"toe.{side}", a_, [a_[0], a_[1] - height * 0.04, a_[2]])
        # 손가락: 원본 마디를 메타리그 손가락에 그대로 얹는다. 안 하면 손가락이 사람 기본 비율 자리에 남는다
        digits = {}
        for name, v in joints.items():
            low = re.sub(r"[^a-z0-9]", "", name.lower().split(":")[-1])
            key = next((k for k in FINGERS if k in low), None)
            if not key:
                continue
            m_ = re.search(r"\d+", low.split(key, 1)[1])
            digits.setdefault((FINGERS[key], "L" if v["head"][0] >= mx else "R"), []).append((int(m_.group()) if m_ else 1, v))
        for (base, side), parts in digits.items():
            parts.sort(key=lambda q: q[0])
            for i, (_, v) in enumerate(parts[:3]):
                nxt = parts[i + 1][1]["head"] if i + 1 < min(len(parts), 3) else v["tail"]
                put(f"{base}.0{i + 1}.{side}", list(v["head"]), list(nxt))
            pal, wrist = PALM_OF.get(base), pos.get(f"hand.{side}")   # 중수골: 손목 → 그 손가락 첫 마디
            if pal and wrist:
                put(f"{pal}.{side}", wrist, list(parts[0][1]["head"]))
    # 원본 뼈대 자체의 좌우 어긋남. 우리가 만든 오차와 구분하려고 잰다(게이트가 이만큼은 봐준다)
    sym = [((pos[f"{b}.L"][0] + pos[f"{b}.R"][0]) ** 2 + sum((pos[f"{b}.L"][i] - pos[f"{b}.R"][i]) ** 2 for i in (1, 2))) ** 0.5
           for b in jm if f"{b}.L" in pos and f"{b}.R" in pos]
    # 원본 뼈대가 통째로 빠뜨린 팔다리는 채워 넣을 근거가 없다 — 메타리그 기본 자리에 남아 몸을 뚫는다
    need = ("front_thigh", "thigh") if quad else ("upper_arm", "thigh")
    gone = [b for b in need if f"{b}.L" not in pos and f"{b}.R" not in pos]
    return found, {"matched": sorted(pos), "missing": sorted(set(missing)), "bones": len(joints),
                   "mirrored": sorted(mirrored), "center_x": round(mx, 4), "limbs_absent": gone,
                   "source_symmetry": round(max(sym), 4) if sym else 0.0}
