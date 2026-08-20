"""세 구현이 동일한 연산을 하는지 검증.

동일한 초기 상태에서 동일한 행동을 1스텝 넣고 obs/reward/done 을 비교한다.
자동 리셋은 구현별 RNG 가 달라 발산하므로, 매 시행마다 상태를 다시 맞춘다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch

import spec
from kernel_numpy import IntersectionNumpy
from kernel_numba import IntersectionNumba
from kernel_torch import IntersectionTorch

E, V, TRIALS = 64, 16, 10
rng = np.random.default_rng(0)

sn = IntersectionNumpy(E, V, seed=0)
sb = IntersectionNumba(E, V, seed=1)
st = IntersectionTorch(E, V, seed=2, device="cuda")

max_obs = max_rew = 0.0
done_mismatch = 0

for trial in range(TRIALS):
    ego = rng.uniform(-spec.ARM_LENGTH, spec.ARM_LENGTH, (E, 4)).astype(np.float32)
    ego[:, 2] = rng.uniform(-np.pi, np.pi, E)
    ego[:, 3] = rng.uniform(0, spec.MAX_SPEED, E)
    npc = rng.uniform(-spec.ARM_LENGTH, spec.ARM_LENGTH, (E, V, 4)).astype(np.float32)
    npc[..., 2] = rng.uniform(-np.pi, np.pi, (E, V))
    npc[..., 3] = rng.uniform(0, spec.MAX_SPEED, (E, V))
    t = rng.integers(0, 100, E).astype(np.int32)
    act = rng.uniform(-1, 1, (E, 2)).astype(np.float32)

    sn.ego[:] = ego; sn.npc[:] = npc; sn.t[:] = t
    sb.ego[:] = ego; sb.npc[:] = npc; sb.t[:] = t
    st.ego.copy_(torch.from_numpy(ego).cuda())
    st.npc.copy_(torch.from_numpy(npc).cuda())
    st.t.copy_(torch.from_numpy(t).cuda())

    on, rn, dn, _ = sn.step(act)
    ob, rb, db, _ = sb.step(act)
    ot, rt, dt_, _ = st.step(torch.from_numpy(act).cuda())
    ot = ot.cpu().numpy(); rt = rt.cpu().numpy(); dt_ = dt_.cpu().numpy()

    max_obs = max(max_obs, float(np.abs(on - ob).max()), float(np.abs(on - ot).max()))
    max_rew = max(max_rew, float(np.abs(rn - rb).max()), float(np.abs(rn - rt).max()))
    done_mismatch += int((dn != db).sum() + (dn != dt_).sum())

print(f"시행 {TRIALS}회, E={E} V={V}")
print(f"obs    최대차이 : {max_obs:.3e}")
print(f"reward 최대차이 : {max_rew:.3e}")
print(f"done   불일치   : {done_mismatch}")
TOL = 2e-4     # float32 누적오차 + GPU/CPU 초월함수 구현 차이 허용치
ok = max_obs < TOL and max_rew < 1e-5 and done_mismatch == 0
print("판정:", "✅ 세 구현 동치" if ok else "❌ 불일치 — SPS 비교 불가")
sys.exit(0 if ok else 1)
