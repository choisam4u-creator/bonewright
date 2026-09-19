"""메시 **속을 따라 잰 거리**로 '같은 살덩이인가'를 판정한다(토큰 0).

자동 가중치(Bone Heat)는 결국 **직선 거리**로 판단한다. 그래서 속이 빈 메시(해골 갈비뼈)에서는
팔 본이 텅 빈 가슴을 가로질러 갈비뼈를 가져가고, 옷이 겹친 메시에서는 안쪽 살이 바깥 본에 끌려간다.

고치려고 광선을 한 번 쏴 "껍질을 뚫고 나가면 남이다"로 봤더니 **보통 게임 메시에서 크게 틀렸다**:
mannequiny 처럼 팔·다리가 조각조각 떨어진 메시는 이웃 조각으로 가는 길이 전부 껍질을 뚫는다
→ 관절마다 섞임이 사라져 리타겟 늘어남이 4.71 → 7.88배로 나빠졌다.

그래서 광선을 버리고 **복셀 측지 거리**로 바꿨다(Maya 의 Geodesic Voxel Binding 과 같은 착상).

  · 메시 속을 복셀로 채우면, **조각 사이의 머리카락 같은 틈은 복셀 하나 크기에 묻혀 메워진다.**
    (mannequiny 관절 틈은 키의 1~2% → 복셀보다 작다)
  · 반대로 **해골의 텅 빈 가슴은 키의 15% 라 그대로 구멍으로 남는다.**

즉 복셀 해상도 자체가 "무시해도 되는 틈"과 "진짜 빈 속"을 갈라 준다 — 규칙을 따로 둘 필요가 없다.

판정은 비율로 한다: 살 속만 따라간 거리(측지)가 **아무 데나 질러간 거리**(빈 격자에서 잰 같은 방식의
거리)보다 훨씬 길면, 그 본에 가려면 살을 벗어나 돌아가야 한다는 뜻이다 → 남의 살이다.
둘 다 같은 6방향 확장으로 재므로 축척·방향 편향이 상쇄된다.
"""


def _grid_dims(size, grid, pad=2):
    h = max(size) / max(8, grid)
    n = [int(size[i] / h) + 1 + 2 * pad for i in range(3)]
    return h, n


class VoxGeo:
    """메시 하나를 복셀로 채워 두고, 본마다 '속을 따라 잰 거리 밭'을 필요할 때 만든다"""

    def __init__(self, obj, grid=40, max_voxels=1_200_000):
        import numpy as np
        from _medial import _fill
        bb = [tuple(c) for c in obj.bound_box]
        mn = [min(c[i] for c in bb) for i in range(3)]
        mx = [max(c[i] for c in bb) for i in range(3)]
        size = [mx[i] - mn[i] for i in range(3)]
        self.ok = False
        if min(size) <= 0:
            return
        h, n = _grid_dims(size, grid)
        if n[0] * n[1] * n[2] > max_voxels:
            return
        pad = 2
        org = [mn[i] - pad * h for i in range(3)]
        occ = _fill(obj, mn, mx, h, n[0], n[1], n[2], org[0], org[1], org[2])
        if sum(occ) < 64:
            return
        a = np.frombuffer(bytes(occ), dtype=np.uint8).reshape(n[0], n[1], n[2]).astype(bool)
        # 한 칸 부풀려 조각 사이 실틈을 메운다(복셀 두 칸까지). 진짜 빈 속은 그보다 훨씬 크다
        self.occ = self._dilate(a)
        self.np = np; self.h = h; self.n = n; self.org = org
        self.fields = {}
        self.ok = True

    @staticmethod
    def _dilate(a):
        b = a.copy()
        b[1:] |= a[:-1]; b[:-1] |= a[1:]
        b[:, 1:] |= a[:, :-1]; b[:, :-1] |= a[:, 1:]
        b[:, :, 1:] |= a[:, :, :-1]; b[:, :, :-1] |= a[:, :, 1:]
        return b

    def idx(self, co):
        i = int((co[0] - self.org[0]) / self.h)
        j = int((co[1] - self.org[1]) / self.h)
        k = int((co[2] - self.org[2]) / self.h)
        if 0 <= i < self.n[0] and 0 <= j < self.n[1] and 0 <= k < self.n[2]:
            return i, j, k
        return None

    def _bfs(self, seed, through):
        """6방향으로 한 겹씩 넓혀 가며 몇 겹 만에 닿는지 센다(못 닿으면 -1)"""
        np = self.np
        d = np.full(self.occ.shape, -1, np.int16)
        cur = seed & through
        if not cur.any():
            return d
        d[cur] = 0
        step = 0
        cap = sum(self.n)
        while step < cap:
            step += 1
            nx = np.zeros_like(cur)
            nx[1:] |= cur[:-1]; nx[:-1] |= cur[1:]
            nx[:, 1:] |= cur[:, :-1]; nx[:, :-1] |= cur[:, 1:]
            nx[:, :, 1:] |= cur[:, :, :-1]; nx[:, :, :-1] |= cur[:, :, 1:]
            nx &= through & (d < 0)
            if not nx.any():
                break
            d[nx] = step
            cur = nx
        return d

    def field(self, name, a=None, b=None):
        """본 하나의 (살 속 거리, 막힘 없는 거리). 처음 물을 때 만들어 두고 다시 쓴다"""
        f = self.fields.get(name)
        if f is not None or a is None:
            return f
        np = self.np
        seed = np.zeros(self.occ.shape, bool)
        L = max(abs(b[i] - a[i]) for i in range(3))
        steps = max(2, int(L / (self.h * 0.5)) + 1)
        for s in range(steps + 1):
            t = s / steps
            p = self.idx([a[i] + (b[i] - a[i]) * t for i in range(3)])
            if p:
                seed[p] = True
        if not (seed & self.occ).any():          # 본이 살 밖이면 살 안으로 한 겹 번지게 한다
            seed = self._dilate(self._dilate(seed))
        geo = self._bfs(seed, self.occ)
        free = self._bfs(seed, np.ones_like(self.occ))
        self.fields[name] = (geo, free)
        return self.fields[name]

    def detour(self, co, name):
        """정점에서 그 본까지, **살 속으로 돌아간 거리 ÷ 질러간 거리**. 알 수 없으면 None"""
        f = self.fields.get(name)
        if f is None:
            return None
        geo, free = f
        p = self.idx(co)
        if p is None:
            return None
        i, j, k = p
        best = None
        for di in (0, -1, 1):
            for dj in (0, -1, 1):
                for dk in (0, -1, 1):
                    a, b, c = i + di, j + dj, k + dk
                    if not (0 <= a < self.n[0] and 0 <= b < self.n[1] and 0 <= c < self.n[2]):
                        continue
                    g = int(geo[a, b, c])
                    if g < 0:
                        continue
                    fr = max(1, int(free[a, b, c]))
                    r = g / fr
                    if best is None or r < best:
                        best = r
        if best is None:
            return float("inf")      # 살 속으로는 아예 못 간다 → 확실한 남
        return best
