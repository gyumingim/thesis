"""경량 교차로 시뮬 커널 — NumPy 벡터화 구현.

MetaDrive와 동일한 과제·행동·관측·종료조건을 흉내내되, 렌더링·씬그래프·강체물리를 제거한다.
E개 환경을 배치로 동시에 굴린다. 상태는 전부 (E, ...) 배열이다.

한 스텝의 연산 구성 (세 구현이 모두 동일하게 수행해야 하는 것):
  1. 자전거 모델 적분 (ego + NPC), DECISION_REPEAT 회 서브스텝
  2. 전체 쌍거리 계산 (E, V+1, V+1)  ← IDM 과 충돌판정이 공유
  3. NPC 종방향 IDM 가감속
  4. ego 기준 최근접 NUM_OTHERS 대 선택 → GT 관측 조립
  5. 종료 판정(충돌/이탈/도달/최대스텝) 및 자동 리셋
"""
import numpy as np
import spec


class IntersectionNumpy:
    def __init__(self, n_envs, n_vehicles, seed=0):
        self.E, self.V = n_envs, n_vehicles
        self.rng = np.random.default_rng(seed)
        self.ego = np.zeros((self.E, 4), dtype=np.float32)   # x, y, heading, speed
        self.npc = np.zeros((self.E, self.V, 4), dtype=np.float32)
        self.t = np.zeros(self.E, dtype=np.int32)
        self.reset_all()

    # ---- 절차적 교차로 배치: 4갈래 진입로에 차량을 뿌린다 ----
    def _spawn(self, n):
        arm = self.rng.integers(0, 4, size=n)                 # 진입 방향
        along = self.rng.uniform(-spec.ARM_LENGTH, -5.0, size=n)
        lat = (self.rng.integers(0, 2, size=n) - 0.5) * spec.LANE_WIDTH
        head = arm * (np.pi / 2)
        x = np.cos(head) * along - np.sin(head) * lat
        y = np.sin(head) * along + np.cos(head) * lat
        spd = self.rng.uniform(3.0, 12.0, size=n)
        return np.stack([x, y, head, spd], axis=-1).astype(np.float32)

    def reset_all(self):
        self.ego[:] = self._spawn(self.E)
        self.npc[:] = self._spawn(self.E * self.V).reshape(self.E, self.V, 4)
        self.t[:] = 0

    def _reset_rows(self, mask):
        n = int(mask.sum())
        if n == 0:
            return
        self.ego[mask] = self._spawn(n)
        self.npc[mask] = self._spawn(n * self.V).reshape(n, self.V, 4)
        self.t[mask] = 0

    # ---- 자전거 모델 ----
    @staticmethod
    def _integrate(state, steer, accel, dt):
        x, y, h, v = state[..., 0], state[..., 1], state[..., 2], state[..., 3]
        v = np.clip(v + accel * dt, 0.0, spec.MAX_SPEED)
        h = h + v / spec.WHEELBASE * np.tan(steer * spec.MAX_STEER) * dt
        x = x + v * np.cos(h) * dt
        y = y + v * np.sin(h) * dt
        return np.stack([x, y, h, v], axis=-1)

    def step(self, action):
        """action: (E, 2) = steering, throttle_brake ∈ [-1, 1]"""
        steer = action[:, 0]
        accel = action[:, 1] * spec.MAX_ACCEL

        # IDM 은 decision step 당 1회 (MetaDrive 의 정책 실행 주기와 동일).
        # 물리만 DECISION_REPEAT 회 서브스텝한다.
        npc_accel = self._idm_accel()
        npc_steer = np.zeros((self.E, self.V), np.float32)
        for _ in range(spec.DECISION_REPEAT):
            self.ego = self._integrate(self.ego, steer, accel, spec.DT_PHYS)
            self.npc = self._integrate(self.npc, npc_steer, npc_accel, spec.DT_PHYS)

        # 적분 후 쌍거리를 한 번만 구해 관측과 종료판정이 공유한다.
        _, dist = self._pairwise()
        obs = self._observe(dist)
        crashed, out_road, arrived = self._terminations(dist)
        self.t += 1
        timeout = self.t >= spec.HORIZON
        done = crashed | out_road | arrived | timeout

        reward = np.where(arrived, 10.0, 0.0) - np.where(crashed, 5.0, 0.0) \
                 - np.where(out_road, 5.0, 0.0)
        self._reset_rows(done)
        return obs, reward.astype(np.float32), done, None

    # ---- 전체 쌍거리: IDM 과 충돌판정이 공유한다 ----
    def _pairwise(self):
        allv = np.concatenate([self.ego[:, None, :], self.npc], axis=1)   # (E, V+1, 4)
        d = allv[:, :, None, :2] - allv[:, None, :, :2]                   # (E, V+1, V+1, 2)
        return allv, np.sqrt((d ** 2).sum(-1))

    def _idm_accel(self):
        """앞차와의 간격에 따른 단순 종방향 가감속."""
        allv, dist = self._pairwise()
        d = dist[:, 1:, 1:].copy()                       # NPC 간 거리
        idx = np.arange(self.V)
        d[:, idx, idx] = np.inf
        gap = d.min(axis=2)                              # (E, V) 최근접 이웃 거리
        v = self.npc[..., 3]
        desired_gap = 2.0 + v * 1.5
        return np.clip((gap - desired_gap) * 0.5, -spec.MAX_ACCEL, spec.MAX_ACCEL).astype(np.float32)

    def _observe(self, dist):
        d_ego = dist[:, 0, 1:]                                            # (E, V) ego↔NPC
        k = min(spec.NUM_OTHERS, self.V)
        near = np.argpartition(d_ego, kth=k - 1, axis=1)[:, :k]           # 최근접 k대
        rows = np.arange(self.E)[:, None]
        sel = self.npc[rows, near]                                        # (E, k, 4)

        ch, sh = np.cos(-self.ego[:, 2:3]), np.sin(-self.ego[:, 2:3])
        dx = sel[..., 0] - self.ego[:, 0:1]
        dy = sel[..., 1] - self.ego[:, 1:2]
        rx = ch * dx - sh * dy
        ry = sh * dx + ch * dy
        rvx = sel[..., 3] * np.cos(sel[..., 2] - self.ego[:, 2:3])
        rvy = sel[..., 3] * np.sin(sel[..., 2] - self.ego[:, 2:3])
        # 감지 반경 밖은 0으로 (MetaDrive 의 zero-padding 과 동일한 취급)
        vis = (d_ego[rows, near] < spec.DETECT_RADIUS).astype(np.float32)
        others = np.stack([rx, ry, rvx, rvy], -1) * vis[..., None]
        others = others.reshape(self.E, -1) / spec.DETECT_RADIUS

        ego_feat = np.stack([self.ego[:, 3] / spec.MAX_SPEED,
                             np.sin(self.ego[:, 2]), np.cos(self.ego[:, 2]),
                             self.ego[:, 1] / spec.ARM_LENGTH], -1)
        navi = np.stack([self.ego[:, 0] / spec.ARM_LENGTH, self.ego[:, 1] / spec.ARM_LENGTH,
                         np.zeros(self.E, np.float32), np.zeros(self.E, np.float32)], -1)
        if others.shape[1] < spec.NUM_OTHERS * 4:
            pad = np.zeros((self.E, spec.NUM_OTHERS * 4 - others.shape[1]), np.float32)
            others = np.concatenate([others, pad], 1)
        return np.concatenate([ego_feat, navi, others], 1).astype(np.float32)

    def _terminations(self, dist):
        crashed = (dist[:, 0, 1:] < spec.COLLISION_RADIUS).any(axis=1)
        r = np.sqrt(self.ego[:, 0] ** 2 + self.ego[:, 1] ** 2)
        out_road = r > spec.ARM_LENGTH * 1.5
        arrived = (r > spec.ARM_LENGTH * 0.9) & ~out_road
        return crashed, out_road, arrived
