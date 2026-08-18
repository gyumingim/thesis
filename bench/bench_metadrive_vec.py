"""MetaDrive AsyncVectorEnv SPS 측정 — 비교군에도 CPU 스레드를 모두 준다.

경량 시뮬만 병렬화하고 비교군을 단일 환경으로 두면 비교가 무효이므로,
비교군의 병렬 상한을 실측해 기준선으로 삼는다.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import gymnasium as gym
from md_env import MetaDriveGT


def make_one(seed, density):
    def _f():
        return MetaDriveGT(seed=seed, density=density)
    return _f


def bench(n_envs, steps, warmup, density):
    envs = gym.vector.AsyncVectorEnv([make_one(i, density) for i in range(n_envs)])
    envs.reset(seed=0)
    rng = np.random.default_rng(0)
    act = lambda: rng.uniform(-1, 1, size=(n_envs, 2)).astype(np.float32)
    for _ in range(warmup):
        envs.step(act())
    t0 = time.perf_counter()
    for _ in range(steps):
        envs.step(act())
    dt = time.perf_counter() - t0
    envs.close()
    return n_envs * steps / dt


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--warmup", type=int, default=40)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--density", type=float, default=0.1)
    ap.add_argument("--out", default="bench_results/metadrive_vec.json")
    a = ap.parse_args()

    rows = []
    for n in a.envs:
        vals = [bench(n, a.steps, a.warmup, a.density) for _ in range(a.repeats)]
        m, sd = float(np.mean(vals)), float(np.std(vals))
        rows.append(dict(n_envs=n, sps_mean=m, sps_std=sd, sps_runs=vals))
        print(f"n_envs={n:3d}  →  {m:9.1f} ± {sd:6.1f} SPS", flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(dict(density=a.density, rows=rows), f, indent=2)
    print(f"저장: {a.out}")
