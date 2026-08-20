"""경량 시뮬 처리량 스윕 — NumPy / Numba / PyTorch(GPU).

SPS = (환경 수 x 스텝 수) / 벽시계 시간.
각 구성마다 워밍업(Numba JIT, CUDA 커널 캐시)을 먼저 수행한 뒤,
고정된 시간 예산 동안 스텝을 돌려 자동으로 스텝 수를 맞춘다.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import spec


def _run(make, act_fn, sync, budget, warmup_steps):
    sim = make()
    a = act_fn(sim)
    for _ in range(warmup_steps):
        sim.step(a)
    sync()
    n, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < budget:
        for _ in range(10):
            sim.step(a)
        n += 10
    sync()
    dt = time.perf_counter() - t0
    return n, dt


def bench(impl, E, V, budget, warmup_steps):
    if impl == "numpy":
        from kernel_numpy import IntersectionNumpy
        mk = lambda: IntersectionNumpy(E, V, seed=0)
        act = lambda s: np.random.default_rng(0).uniform(-1, 1, (E, 2)).astype(np.float32)
        sync = lambda: None
    elif impl == "numba":
        from kernel_numba import IntersectionNumba
        mk = lambda: IntersectionNumba(E, V, seed=0)
        act = lambda s: np.random.default_rng(0).uniform(-1, 1, (E, 2)).astype(np.float32)
        sync = lambda: None
    elif impl == "torch":
        import torch
        from kernel_torch import IntersectionTorch
        mk = lambda: IntersectionTorch(E, V, seed=0, device="cuda")
        act = lambda s: (torch.rand(E, 2, device="cuda") * 2 - 1)
        sync = torch.cuda.synchronize
    else:
        raise ValueError(impl)
    n, dt = _run(mk, act, sync, budget, warmup_steps)
    return E * n / dt, n, dt


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--impls", nargs="+", default=["numpy", "numba", "torch"])
    ap.add_argument("--envs", type=int, nargs="+", default=[1, 64, 256, 1024, 4096])
    ap.add_argument("--vehicles", type=int, nargs="+", default=[4, 16, 64])
    ap.add_argument("--budget", type=float, default=1.5, help="구성당 측정 시간(초)")
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--out", default="bench_results/sweep.json")
    a = ap.parse_args()

    rows = []
    for V in a.vehicles:
        print(f"\n=== 차량 수 V={V} ===")
        print(f"{'E':>6} | " + " | ".join(f"{i:>14}" for i in a.impls))
        for E in a.envs:
            cells = []
            for impl in a.impls:
                try:
                    sps, n, dt = bench(impl, E, V, a.budget, a.warmup)
                    rows.append(dict(impl=impl, n_envs=E, n_vehicles=V, sps=sps, steps=n, secs=dt))
                    cells.append(f"{sps:14,.0f}")
                except Exception as e:
                    rows.append(dict(impl=impl, n_envs=E, n_vehicles=V, sps=None, error=str(e)[:120]))
                    cells.append(f"{'ERR':>14}")
            print(f"{E:>6} | " + " | ".join(cells), flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(dict(budget=a.budget, rows=rows), f, indent=2)
    print(f"\n저장: {a.out}")
