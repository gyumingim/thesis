"""경량 교차로 시뮬 커널 — Numba 구현.

kernel_numpy.IntersectionNumpy 와 **동일한 연산**을 수행한다. 차이는 실행 방식뿐이다.
Numba 는 fancy indexing 지원이 약하므로 명시적 루프로 쓰고, 환경 축을 prange 로 병렬화한다.
"""
import numpy as np
from numba import njit, prange

import spec

_DT_P = spec.DT_PHYS
_REP = spec.DECISION_REPEAT
_WB = spec.WHEELBASE
_MS = spec.MAX_STEER
_MA = spec.MAX_ACCEL
_MV = spec.MAX_SPEED
_CR = spec.COLLISION_RADIUS
_DR = spec.DETECT_RADIUS
_NO = spec.NUM_OTHERS
_ARM = spec.ARM_LENGTH
_HOR = spec.HORIZON


@njit(parallel=True, cache=True)
def _step(ego, npc, t, action, obs, reward, done):
    E = ego.shape[0]
    V = npc.shape[1]
    for e in prange(E):
        # --- 1. NPC IDM 종방향 가속도 (decision step 당 1회) ---
        accel = np.empty(V, dtype=np.float32)
        for i in range(V):
            gap = 1e18
            for j in range(V):
                if i == j:
                    continue
                dx = npc[e, i, 0] - npc[e, j, 0]
                dy = npc[e, i, 1] - npc[e, j, 1]
                d = np.sqrt(dx * dx + dy * dy)
                if d < gap:
                    gap = d
            des = 2.0 + npc[e, i, 3] * 1.5
            a = (gap - des) * 0.5
            if a > _MA:
                a = _MA
            elif a < -_MA:
                a = -_MA
            accel[i] = a

        # --- 2. 자전거 모델 적분 (물리 서브스텝) ---
        st = action[e, 0]
        eac = action[e, 1] * _MA
        for _ in range(_REP):
            v = ego[e, 3] + eac * _DT_P
            if v < 0.0:
                v = 0.0
            elif v > _MV:
                v = _MV
            h = ego[e, 2] + v / _WB * np.tan(st * _MS) * _DT_P
            ego[e, 0] += v * np.cos(h) * _DT_P
            ego[e, 1] += v * np.sin(h) * _DT_P
            ego[e, 2] = h
            ego[e, 3] = v
            for i in range(V):
                vi = npc[e, i, 3] + accel[i] * _DT_P
                if vi < 0.0:
                    vi = 0.0
                elif vi > _MV:
                    vi = _MV
                hi = npc[e, i, 2]
                npc[e, i, 0] += vi * np.cos(hi) * _DT_P
                npc[e, i, 1] += vi * np.sin(hi) * _DT_P
                npc[e, i, 3] = vi

        # --- 3. ego↔NPC 거리, 최근접 k 선택 ---
        k = _NO if _NO < V else V
        d_ego = np.empty(V, dtype=np.float32)
        for i in range(V):
            dx = npc[e, i, 0] - ego[e, 0]
            dy = npc[e, i, 1] - ego[e, 1]
            d_ego[i] = np.sqrt(dx * dx + dy * dy)

        used = np.zeros(V, dtype=np.uint8)
        eh = ego[e, 2]
        ch = np.cos(-eh)
        sh = np.sin(-eh)
        for s in range(k):
            best = -1
            bd = 1e18
            for i in range(V):
                if used[i] == 0 and d_ego[i] < bd:
                    bd = d_ego[i]
                    best = i
            used[best] = 1
            base = spec.EGO_DIM + spec.NAVI_DIM + s * 4
            if bd < _DR:
                dx = npc[e, best, 0] - ego[e, 0]
                dy = npc[e, best, 1] - ego[e, 1]
                obs[e, base + 0] = (ch * dx - sh * dy) / _DR
                obs[e, base + 1] = (sh * dx + ch * dy) / _DR
                obs[e, base + 2] = npc[e, best, 3] * np.cos(npc[e, best, 2] - eh) / _DR
                obs[e, base + 3] = npc[e, best, 3] * np.sin(npc[e, best, 2] - eh) / _DR
            else:
                obs[e, base + 0] = 0.0
                obs[e, base + 1] = 0.0
                obs[e, base + 2] = 0.0
                obs[e, base + 3] = 0.0
        for s in range(k, _NO):
            base = spec.EGO_DIM + spec.NAVI_DIM + s * 4
            for q in range(4):
                obs[e, base + q] = 0.0

        # --- 4. ego 특징 + 내비 ---
        obs[e, 0] = ego[e, 3] / _MV
        obs[e, 1] = np.sin(eh)
        obs[e, 2] = np.cos(eh)
        obs[e, 3] = ego[e, 1] / _ARM
        obs[e, 4] = ego[e, 0] / _ARM
        obs[e, 5] = ego[e, 1] / _ARM
        obs[e, 6] = 0.0
        obs[e, 7] = 0.0

        # --- 5. 종료 판정 ---
        crashed = False
        for i in range(V):
            if d_ego[i] < _CR:
                crashed = True
                break
        r = np.sqrt(ego[e, 0] * ego[e, 0] + ego[e, 1] * ego[e, 1])
        out_road = r > _ARM * 1.5
        arrived = (r > _ARM * 0.9) and (not out_road)
        t[e] += 1
        timeout = t[e] >= _HOR

        rw = 0.0
        if arrived:
            rw += 10.0
        if crashed:
            rw -= 5.0
        if out_road:
            rw -= 5.0
        reward[e] = rw
        done[e] = crashed or out_road or arrived or timeout


class IntersectionNumba:
    def __init__(self, n_envs, n_vehicles, seed=0):
        from kernel_numpy import IntersectionNumpy
        self._np = IntersectionNumpy(n_envs, n_vehicles, seed)   # 스폰 로직 공유
        self.E, self.V = n_envs, n_vehicles
        self.ego = self._np.ego
        self.npc = self._np.npc
        self.t = self._np.t
        self.obs = np.zeros((self.E, spec.OBS_DIM), dtype=np.float32)
        self.reward = np.zeros(self.E, dtype=np.float32)
        self.done = np.zeros(self.E, dtype=np.bool_)

    def step(self, action):
        _step(self.ego, self.npc, self.t, action, self.obs, self.reward, self.done)
        self._np._reset_rows(self.done)      # 리셋은 NumPy 쪽 로직 재사용
        return self.obs, self.reward, self.done, None
