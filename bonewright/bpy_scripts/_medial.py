"""메시 속을 복셀로 채워 '가장 깊은 길'을 따라 팔다리 끝을 찾는다(토큰 0).

실루엣 띠(analyze.py)는 몸을 높이로 잘라 폭을 재는 방식이라, 팔이 몸에 붙어 있거나 자세가 있거나
사람 비례가 아니면 팔·다리를 아예 못 찾는다. 이 모듈은 겉모양 대신 **속**을 본다:

  1. 기둥마다 광선을 쏴 메시 안쪽 복셀을 채운다
  2. 복셀마다 표면까지 거리를 잰다(체임퍼 근사)
  3. 깊은 복셀부터 서로 안 겹치게 최대구를 놓는다 — 구 중심이 곧 몸의 중심선이다
  4. 구끼리 이어 그래프를 만들고, 한가운데에서 가장 먼 점들을 고른다 = 손끝·발끝·머리끝·꼬리끝

**무엇을 주고 무엇을 안 주는지 분명히 한다.**
  · 준다: 팔다리 **끝**과 끝까지 가는 **경로**. 자산 10종에서 끝점이 나왔고, 그중 정답 뼈대와 맞댄
    6종(mannequiny 손 3.4%·발 3.5%, kira 손 3.0%·손목 4.1%, quat_pp_41j 발목 0.1%, 늑대·여우·말 네 발)
    은 키의 1~4% 안에 들었다.
  · 안 준다: 골반·어깨·무릎·팔꿈치 높이. 몸통의 중심선은 선이 아니라 **면**이라, 팔다리 경로가 몸통을
    제각각 가로지른다. 두 다리 경로가 만나는 지점을 골반으로 삼아 봤지만 자산에 따라 30cm 이상
    틀렸다(godot 0.81 대 정답 0.63) — 그래서 이 모듈은 그 값을 내지 않는다. 몸통 안쪽 관절은
    실루엣이 읽은 값이나 비율이 담당한다.
"""
import math
import heapq


def _fill(obj, mn, mx, h, nx, ny, nz, ox, oy, oz):
    """기둥마다 아래에서 위로 광선을 쏴 교차점 짝 사이를 '안'으로 채운다"""
    from mathutils import Vector      # bpy 밖(테스트)에서도 기하 함수만 쓸 수 있게 늦게 들여온다
    occ = bytearray(nx * ny * nz)
    zlo, zhi = oz - h, oz + nz * h + h
    for i in range(nx):
        x = ox + (i + 0.5) * h
        for j in range(ny):
            y = oy + (j + 0.5) * h
            z = zlo
            hits = []
            for _ in range(64):
                ok, loc, _n, _f = obj.ray_cast(Vector((x, y, z)), Vector((0, 0, 1)), distance=zhi - z)
                if not ok:
                    break
                hits.append(loc.z)
                z = loc.z + h * 1e-3
            for a in range(0, len(hits) - 1, 2):
                z0, z1 = hits[a], hits[a + 1]
                k0 = max(0, int((z0 - oz) / h)); k1 = min(nz - 1, int((z1 - oz) / h))
                for k in range(k0, k1 + 1):
                    if z0 <= oz + (k + 0.5) * h <= z1:
                        occ[(i * ny + j) * nz + k] = 1
    return occ


# 1, √2, √3 의 정수 근사(체임퍼 거리)
_W = (10, 14, 17)
_FWD = ((-1, 0, 0), (0, -1, 0), (0, 0, -1), (-1, -1, 0), (-1, 1, 0), (-1, 0, -1), (-1, 0, 1),
        (0, -1, -1), (0, -1, 1), (-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1))


def _distance(occ, nx, ny, nz):
    """안쪽 복셀마다 표면까지 거리. 앞뒤로 한 번씩 훑는 체임퍼 근사(정확한 유클리드 거리는 필요 없다)"""
    INF = 1 << 28
    dist = [INF if occ[p] else 0 for p in range(nx * ny * nz)]
    for rev in (False, True):
        ri = range(nx - 1, -1, -1) if rev else range(nx)
        for i in ri:
            rj = range(ny - 1, -1, -1) if rev else range(ny)
            for j in rj:
                rk = range(nz - 1, -1, -1) if rev else range(nz)
                for k in rk:
                    p = (i * ny + j) * nz + k
                    if not occ[p]:
                        continue
                    best = dist[p]
                    for d in _FWD:
                        di, dj, dk = (-d[0], -d[1], -d[2]) if rev else d
                        a, b, c = i + di, j + dj, k + dk
                        if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz:
                            v = dist[((a * ny + b) * nz + c)] + _W[abs(d[0]) + abs(d[1]) + abs(d[2]) - 1]
                            if v < best:
                                best = v
                    dist[p] = best
    return dist


def _spheres(occ, dist, h, nx, ny, nz, ox, oy, oz):
    """깊은 복셀부터 골라 이미 놓인 구 안쪽이 아닐 때만 새 구를 놓는다(최대구 채우기)"""
    cells = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                p = (i * ny + j) * nz + k
                if occ[p]:
                    cells.append((dist[p], i, j, k))
    cells.sort(reverse=True)
    out = []
    rmin = h * 0.8
    for dv, i, j, k in cells:
        r = dv / 10.0 * h
        if r < rmin:
            break
        c = (ox + (i + 0.5) * h, oy + (j + 0.5) * h, oz + (k + 0.5) * h)
        if all((c[0] - s[0]) ** 2 + (c[1] - s[1]) ** 2 + (c[2] - s[2]) ** 2 >= s[3] * s[3] for s in out):
            out.append((c[0], c[1], c[2], r))
    return out


def _graph(spheres):
    """겹치는 구끼리 잇는다. 조각으로 만든 모델은 덩어리가 끊기므로 가장 가까운 짝으로 다리를 놓는다"""
    n = len(spheres)
    adj = [[] for _ in range(n)]
    for a in range(n):
        ax, ay, az, ar = spheres[a]
        for b in range(a + 1, n):
            bx, by, bz, br = spheres[b]
            dd = math.dist((ax, ay, az), (bx, by, bz))
            if dd < (ar + br) * 1.1:
                adj[a].append((b, dd)); adj[b].append((a, dd))

    def comps():
        seen = [-1] * n; c = 0
        for s0 in range(n):
            if seen[s0] >= 0:
                continue
            stack = [s0]; seen[s0] = c
            while stack:
                u = stack.pop()
                for v, _w in adj[u]:
                    if seen[v] < 0:
                        seen[v] = c; stack.append(v)
            c += 1
        return seen, c

    seen, ncomp = comps()
    bridges = 0
    while ncomp > 1 and bridges < 64:
        grp0 = [i for i in range(n) if seen[i] == seen[0]]
        other = [i for i in range(n) if seen[i] != seen[0]]
        best = None
        for a in grp0:
            ax, ay, az, _r = spheres[a]
            for b in other:
                bx, by, bz, _r2 = spheres[b]
                dd = (ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2
                if best is None or dd < best[0]:
                    best = (dd, a, b)
        if best is None:
            break
        dd, a, b = best; dd = dd ** 0.5
        adj[a].append((b, dd)); adj[b].append((a, dd)); bridges += 1
        seen, ncomp = comps()
    return adj, bridges


def _dijkstra(adj, n, src):
    D = [float("inf")] * n; P = [-1] * n; D[src] = 0.0
    q = [(0.0, src)]
    while q:
        d, u = heapq.heappop(q)
        if d > D[u] + 1e-12:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < D[v] - 1e-12:
                D[v] = nd; P[v] = u; heapq.heappush(q, (nd, v))
    return D, P


def read_shape(obj, mn, mx, grid=48, min_branch=0.12):
    """메시 속 중심선에서 끝점과 경로를 뽑는다. 실패하면 None 을 돌려준다(부르는 쪽이 실루엣 값을 쓴다)"""
    size = [mx[i] - mn[i] for i in range(3)]
    if min(size) <= 0:
        return None
    h = max(size) / max(8, grid)
    pad = 2
    nx = int(size[0] / h) + 1 + 2 * pad
    ny = int(size[1] / h) + 1 + 2 * pad
    nz = int(size[2] / h) + 1 + 2 * pad
    if nx * ny * nz > 2_500_000:      # 너무 큰 격자는 시간이 폭발한다 → 포기하고 실루엣에 맡긴다
        return None
    ox, oy, oz = mn[0] - pad * h, mn[1] - pad * h, mn[2] - pad * h
    occ = _fill(obj, mn, mx, h, nx, ny, nz, ox, oy, oz)
    if sum(occ) < 64:
        return None
    dist = _distance(occ, nx, ny, nz)
    sp = _spheres(occ, dist, h, nx, ny, nz, ox, oy, oz)
    n = len(sp)
    if n < 16:
        return None
    adj, bridges = _graph(sp)

    # 뿌리: 양 끝을 두 번 훑어(가장 먼 점 → 그 점에서 가장 먼 점) 그 사이 한가운데.
    # 가장 굵은 구를 뿌리로 삼으면 머리가 뿌리가 되어 머리를 못 찾는다(실험으로 확인)
    s0 = max(range(n), key=lambda s: sp[s][3])
    Da, _Pa = _dijkstra(adj, n, s0)
    a = max(range(n), key=lambda i: Da[i] if Da[i] < float("inf") else -1)
    Db, Pb = _dijkstra(adj, n, a)
    b = max(range(n), key=lambda i: Db[i] if Db[i] < float("inf") else -1)
    if Db[b] == float("inf") or Db[b] <= 0:
        return None
    seq = []; u = b
    while u != -1:
        seq.append(u); u = Pb[u]
    half = Db[b] / 2.0
    root = min(seq, key=lambda i: abs(Db[i] - half))

    D0, P0 = _dijkstra(adj, n, root)
    reach = [i for i in range(n) if D0[i] < float("inf")]
    mind = {i: D0[i] for i in reach}
    claimed = set()
    thr = max(size) * min_branch
    tips = []
    for _ in range(30):
        if len(tips) >= 10:
            break
        cand = max(reach, key=lambda i: mind[i])
        if mind[cand] < thr:
            break
        p = []; u = cand
        while u != -1 and u not in claimed:
            p.append(u); u = P0[u]
        joint = u
        if p:
            blen = sum(math.dist(sp[q0][:3], sp[q1][:3]) for q0, q1 in zip(p, p[1:]))
            if joint != -1:
                blen += math.dist(sp[p[-1]][:3], sp[joint][:3])
            if blen >= thr:
                if joint != -1:
                    p.append(joint)
                tips.append({"p": list(sp[cand][:3]), "r": sp[cand][3], "branch": round(blen, 4),
                             "path": [list(sp[q][:4]) for q in p]})
                claimed.update(p)
        Dc, _Pc = _dijkstra(adj, n, cand)
        for i in reach:
            mind[i] = min(mind[i], Dc[i])
    if not tips:
        return None
    return {"root": list(sp[root][:4]), "voxel": round(h, 4), "spheres": n, "bridges": bridges,
            "tips": tips}


def _sm(p, rounds=3):
    p = [list(q[:3]) for q in p]
    for _ in range(rounds):
        q = [p[0]]
        for i in range(1, len(p) - 1):
            q.append([(p[i - 1][k] + 2 * p[i][k] + p[i + 1][k]) / 4 for k in range(3)])
        q.append(p[-1]); p = q
    return p


def resample(pts, n=8, rounds=3):
    """등간격 재표본. 복셀 경로는 계단처럼 지그재그라 그냥 쓰면 호길이가 부풀어 오른다.
    rounds 는 다듬는 횟수 — 모서리를 찾을 때는 1 로 줄인다(3 이면 직각도 15도로 뭉개진다)"""
    pts = _sm(pts, rounds) if (len(pts) > 2 and rounds) else [list(q[:3]) for q in pts]
    if len(pts) < 2:
        return []
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    L = sum(seg)
    if L <= 0:
        return []
    out = []
    for i in range(n):
        t = L * i / (n - 1); acc = 0.0; k = 0
        while k < len(seg) and acc + seg[k] < t:
            acc += seg[k]; k += 1
        if k >= len(seg):
            out.append(list(pts[-1])); continue
        f = (t - acc) / seg[k] if seg[k] > 0 else 0.0
        out.append([pts[k][j] + (pts[k + 1][j] - pts[k][j]) * f for j in range(3)])
    return out


def classify(shape, height, ground, quad=False):
    """끝점에 역할을 붙인다. 사람: 발 둘·손 둘·머리 / 사족: 발 넷·머리·꼬리.
    좌우는 이름이 아니라 **x 부호**로 정한다(가져오기가 메시를 180° 돌리는 파일이 많다)."""
    tips = shape["tips"]
    if not tips:
        return {}
    low = [t for t in tips if t["p"][2] < ground + height * 0.28]
    out = {}
    if quad:
        if len(low) < 4:
            return {}
        # 앞다리/뒷다리로 가르기: y 로 벌어진 곳에서 끊는다. 다만 **가장 크게 벌어진 곳이 답이 아닐 수 있다** —
        # 여우는 꼬리가 바닥까지 늘어져 발 무리에 끼는데, 그러면 최대 틈이 꼬리를 떼어 내는 자리가 된다.
        # 그래서 "양쪽 무리에 좌(+x)와 우(-x)가 모두 있는" 첫 번째 틈을 쓴다(늑대·여우·말 3종 정답 대조로 확인)
        ys = sorted((t["p"][1], i) for i, t in enumerate(low))
        gaps = sorted(((ys[i + 1][0] - ys[i][0], i) for i in range(len(ys) - 1)), reverse=True)
        pair = None
        for _g, gi in gaps:
            cut = (ys[gi][0] + ys[gi + 1][0]) / 2
            a = [t for t in low if t["p"][1] <= cut]
            b = [t for t in low if t["p"][1] > cut]
            if all(any(t["p"][0] > 0 for t in grp) and any(t["p"][0] <= 0 for t in grp) for grp in (a, b)):
                pair = (a, b); break
        if pair is None:
            return {}
        grpA, grpB = pair
        taken = [id(t) for t in grpA] + [id(t) for t in grpB]
        rest = sorted([t for t in tips if id(t) not in taken], key=lambda t: -t["branch"])[:2]
        if len(rest) < 2:
            return {}

        # 머리와 꼬리: 경로가 굵은 쪽이 머리다(꼬리는 가늘다). 이름도 방향도 쓰지 않는다
        def thick(t):
            rs = [q[3] for q in t["path"]]
            return sum(rs) / len(rs)
        head, tail = (rest[0], rest[1]) if thick(rest[0]) > thick(rest[1]) else (rest[1], rest[0])
        front, hind = ((grpA, grpB) if abs(grpA[0]["p"][1] - head["p"][1]) < abs(grpB[0]["p"][1] - head["p"][1])
                       else (grpB, grpA))
        for grp, key in ((front, "front"), (hind, "hind")):
            grp = sorted(grp, key=lambda t: -t["p"][0])     # 가장 바깥 좌·우만 발로 본다(가운데 꼬리는 뺀다)
            out[f"{key}.L"] = grp[0]; out[f"{key}.R"] = grp[-1]
        out["head"] = head; out["tail"] = tail
        return out
    feet = sorted(low, key=lambda t: (t["p"][2], -t["branch"]))
    fL = next((t for t in feet if t["p"][0] > 0), None)
    fR = next((t for t in feet if t["p"][0] <= 0), None)
    rest = [t for t in tips if t is not fL and t is not fR]
    head = max(rest, key=lambda t: t["p"][2]) if rest else None
    rest = [t for t in rest if t is not head]
    hL = max([t for t in rest if t["p"][0] > 0], key=lambda t: t["branch"], default=None)
    hR = max([t for t in rest if t["p"][0] <= 0], key=lambda t: t["branch"], default=None)
    for k, v in (("foot.L", fL), ("foot.R", fR), ("hand.L", hL), ("hand.R", hR), ("head", head)):
        if v:
            out[k] = v
    return out


def arm_axis(tip, torso_hw, samples=8):
    """팔 끝 경로에서 **몸통 밖 구간만** 잘라 실루엣 팔 중심선과 같은 모양([x,y,z,r])으로 돌려준다.
    몸통 안쪽은 중심선이 아니라 면이라 믿을 수 없다 — 어깨 높이는 실루엣이 잰 값을 쓴다"""
    pts = [q for q in tip["path"]][::-1]        # 몸통 쪽 → 손끝 순
    outside = [q for q in pts if abs(q[0]) > torso_hw]
    if len(outside) < 2:
        return []
    rs = [q[3] for q in outside]
    xs = resample(outside, samples)
    if not xs:
        return []
    return [[round(v, 4) for v in p] + [round(rs[min(i * len(rs) // max(1, len(xs)), len(rs) - 1)], 4)]
            for i, p in enumerate(xs)]


def ankle_from(tip, ground, height, window=2):
    """발끝 경로에서 발목을 찾는다: 다리에서 발로 꺾이는 모서리.

    꺾임 각은 **바로 옆 표본이 아니라 window 칸 떨어진 표본**으로 잰다. 재표본과 다듬기를 거치면
    직각 모서리도 여러 칸에 걸쳐 완만해져서, 옆 칸끼리만 보면 90도 꺾임을 30도로 읽는다(테스트로 확인).
    꺾임이 없는 곧은 다리에서는 None 을 돌려준다 — 없는 관절을 지어내지 않는다."""
    pts = resample([q for q in tip["path"]][::-1], 16, rounds=1)
    if len(pts) < 2 * window + 3:
        return None
    best = None
    for i in range(window, len(pts) - window):
        if pts[i][2] > ground + height * 0.25:      # 발목은 바닥 가까이에 있다
            continue
        a = [pts[i][k] - pts[i - window][k] for k in range(3)]
        b = [pts[i + window][k] - pts[i][k] for k in range(3)]
        la = math.sqrt(sum(v * v for v in a)); lb = math.sqrt(sum(v * v for v in b))
        if la < 1e-6 or lb < 1e-6:
            continue
        cos = sum(a[k] * b[k] for k in range(3)) / (la * lb)
        ang = math.acos(max(-1.0, min(1.0, cos)))
        if best is None or ang > best[0]:
            best = (ang, pts[i])
    if best is None or best[0] < 0.5:               # 30도 미만이면 모서리로 보지 않는다
        return None
    return best[1]


def _at_z(pts, z):
    """폴리라인에서 높이 z 인 지점(위에서부터 처음 만나는 구간). 없으면 None"""
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        lo, hi = (a, b) if a[2] <= b[2] else (b, a)
        if lo[2] <= z <= hi[2]:
            t = (z - lo[2]) / (hi[2] - lo[2]) if hi[2] > lo[2] else 0.0
            return [lo[j] + (hi[j] - lo[j]) * t for j in range(3)]
    return None


def crotch_from(tipL, tipR, steps=24):
    """가랑이 = 두 다리 경로가 **합쳐지는** 높이.

    처음에는 "두 경로가 가장 낮게 맞닿는 곳"으로 잡았는데, 치마·로브 안에서 두 다리가 낮은 데서
    한 번 스치기만 해도 거기로 끌려 내려갔다(quat_pp_41j 2.053, 정답 고관절 2.673 — 62cm 빗나감).
    합류는 되돌아가지 않는다: 가랑이 위로는 계속 붙어 있고 아래로는 갈라진다. 그래서 위에서
    내려오며 **계속 붙어 있던** 마지막 높이를 쓴다(같은 자산 2.575 — 9.8cm).

    두 경로를 마디 번호로 짝지으면 안 된다. 한쪽 경로는 뿌리까지 가고 다른 쪽은 그 경로 중간에서
    끊기므로(먼저 자리 잡은 가지에서 멈춘다) 시작 높이가 서로 다르다 — 격자를 48 로 바꾸기만 해도
    이 때문에 값이 통째로 사라졌다. 그래서 **같은 높이끼리** 견준다."""
    if not (tipL and tipR):
        return None
    if len(tipL["path"]) < 3 or len(tipR["path"]) < 3:
        return None
    a = resample([q for q in tipL["path"]][::-1], 32, rounds=1)
    b = resample([q for q in tipR["path"]][::-1], 32, rounds=1)
    if not a or not b:
        return None
    ra = sum(q[3] for q in tipL["path"]) / len(tipL["path"])
    rb = sum(q[3] for q in tipR["path"]) / len(tipR["path"])
    reach = (ra + rb) * 1.2
    ztop = min(max(p[2] for p in a), max(p[2] for p in b))
    zbot = max(min(p[2] for p in a), min(p[2] for p in b))
    if ztop - zbot <= 0:
        return None
    last = None
    for i in range(steps):
        z = ztop - (ztop - zbot) * i / (steps - 1)
        pa, pb = _at_z(a, z), _at_z(b, z)
        if pa is None or pb is None:
            continue
        if math.dist(pa, pb) > reach:
            break
        last = z
    return last


def consistent(roles, height, tol=0.05):
    """이 속-읽기를 믿어도 되는가. 좌우가 있는 끝점(발·손)이 **거울처럼 맞아야** 한다.

    왜 필요한가: godot_player 는 어깨 견갑을 손으로 잘못 잡아 손 높이가 한쪽 0.73, 다른 쪽 1.96 으로
    나왔다. 그 상태로 발목을 채워 게이트를 통과시키면 오차 18% 짜리 리그를 아무 경고 없이 내보낸다.
    좌우가 어긋난 읽기는 '값을 보태는' 데는 써도 '사람 손으로 볼 필요 없다'는 판정에는 쓰지 않는다.

    주의: 자세가 있는 캐릭터(한 팔을 든 사람)는 진짜로 비대칭이라 여기서 False 가 된다. 그건 맞는
    결과다 — 그런 메시는 좌우 대칭 게이트에서도 어차피 걸린다."""
    for base in ("foot", "hand"):
        a, b = roles.get(f"{base}.L"), roles.get(f"{base}.R")
        if not (a and b):
            return False
        if abs(a["p"][2] - b["p"][2]) > height * tol:
            return False
        if abs(abs(a["p"][0]) - abs(b["p"][0])) > height * tol:
            return False
        if abs(a["p"][1] - b["p"][1]) > height * tol:
            return False
    return bool(roles.get("head"))
