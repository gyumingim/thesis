"""경량 교차로 시뮬 커널 — PyTorch(GPU) 구현.

kernel_numpy.IntersectionNumpy 와 **동일한 연산**을 수행한다.
상태를 GPU 텐서로 유지해 CPU-GPU 전송을 없앤다 (관측을 정책이 GPU에서 바로 받는다).
"""
import numpy as np
import torch

import spec


class IntersectionTorch:
    def __init__(self, n_envs, n_vehicles, seed=0, device="cuda"):
        self.E, self.V = n_envs, n_vehicles
        self.dev = torch.device(device)
        self.g = torch.Generator(device=self.dev).manual_seed(seed)
        self.ego = torch.zeros((self.E, 4), dtype=torch.float32, device=self.dev)
        self.npc = torch.zeros((self.E, self.V, 4), dtype=torch.float32, device=self.dev)
        self.t = torch.zeros(self.E, dtype=torch.int32, device=self.dev)
        self._eye = torch.eye(self.V, dtype=torch.bool, device=self.dev)
        self.reset_all()

    def _spawn(self, n):
        r = lambda *s: torch.rand(*s, generator=self.g, device=self.dev)
        arm = torch.randint(0, 4, (n,), generator=self.g, device=self.dev).float()
        along = -5.0 - r(n) * (spec.ARM_LENGTH - 5.0)
        lat = (torch.randint(0, 2, (n,), generator=self.g, device=self.dev).float() - 0.5) * spec.LANE_WIDTH
        head = arm * (torch.pi / 2)
        x = torch.cos(head) * along - torch.sin(head) * lat
        y = torch.sin(head) * along + torch.cos(head) * lat
        spd = 3.0 + r(n) * 9.0
        return torch.stack([x, y, head, spd], dim=-1)

    def reset_all(self):
        self.ego.copy_(self._spawn(self.E))
        self.npc.copy_(self._spawn(self.E * self.V).view(self.E, self.V, 4))
        self.t.zero_()

    def _reset_rows(self, mask):
        n = int(mask.sum())
        if n == 0:
            return
        self.ego[mask] = self._spawn(n)
        self.npc[mask] = self._spawn(n * self.V).view(n, self.V, 4)
        self.t[mask] = 0

    @staticmethod
    def _integrate(state, steer, accel, dt):
        x, y, h, v = state.unbind(-1)
        v = (v + accel * dt).clamp(0.0, spec.MAX_SPEED)
        h = h + v / spec.WHEELBASE * torch.tan(steer * spec.MAX_STEER) * dt
        return torch.stack([x + v * torch.cos(h) * dt, y + v * torch.sin(h) * dt, h, v], dim=-1)

    def step(self, action):
        steer, accel = action[:, 0], action[:, 1] * spec.MAX_ACCEL

        # IDM: NPC 간 최근접 간격 (decision step 당 1회)
        p = self.npc[..., :2]
        dn = torch.cdist(p, p)
        dn = dn.masked_fill(self._eye, float("inf"))
        gap = dn.min(dim=2).values
        des = 2.0 + self.npc[..., 3] * 1.5
        npc_accel = ((gap - des) * 0.5).clamp(-spec.MAX_ACCEL, spec.MAX_ACCEL)
        npc_steer = torch.zeros_like(npc_accel)

        for _ in range(spec.DECISION_REPEAT):
            self.ego = self._integrate(self.ego, steer, accel, spec.DT_PHYS)
            self.npc = self._integrate(self.npc, npc_steer, npc_accel, spec.DT_PHYS)

        d_ego = torch.linalg.norm(self.npc[..., :2] - self.ego[:, None, :2], dim=-1)   # (E,V)
        k = min(spec.NUM_OTHERS, self.V)
        nd, ni = torch.topk(d_ego, k, dim=1, largest=False)
        sel = torch.gather(self.npc, 1, ni[..., None].expand(-1, -1, 4))

        eh = self.ego[:, 2:3]
        ch, sh = torch.cos(-eh), torch.sin(-eh)
        dx = sel[..., 0] - self.ego[:, 0:1]
        dy = sel[..., 1] - self.ego[:, 1:2]
        rel = torch.stack([
            ch * dx - sh * dy,
            sh * dx + ch * dy,
            sel[..., 3] * torch.cos(sel[..., 2] - eh),
            sel[..., 3] * torch.sin(sel[..., 2] - eh),
        ], dim=-1) * (nd < spec.DETECT_RADIUS)[..., None]
        others = (rel / spec.DETECT_RADIUS).reshape(self.E, -1)
        if others.shape[1] < spec.NUM_OTHERS * 4:
            others = torch.nn.functional.pad(others, (0, spec.NUM_OTHERS * 4 - others.shape[1]))

        obs = torch.cat([
            (self.ego[:, 3:4] / spec.MAX_SPEED), torch.sin(eh), torch.cos(eh),
            self.ego[:, 1:2] / spec.ARM_LENGTH,
            self.ego[:, 0:1] / spec.ARM_LENGTH, self.ego[:, 1:2] / spec.ARM_LENGTH,
            torch.zeros_like(eh), torch.zeros_like(eh),
            others,
        ], dim=1)

        crashed = (d_ego < spec.COLLISION_RADIUS).any(dim=1)
        r = torch.linalg.norm(self.ego[:, :2], dim=1)
        out_road = r > spec.ARM_LENGTH * 1.5
        arrived = (r > spec.ARM_LENGTH * 0.9) & ~out_road
        self.t += 1
        done = crashed | out_road | arrived | (self.t >= spec.HORIZON)
        reward = 10.0 * arrived.float() - 5.0 * crashed.float() - 5.0 * out_road.float()
        self._reset_rows(done)
        return obs, reward, done, None
