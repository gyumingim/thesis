"""MetaDrive 기준선 SPS 측정 (단일 환경).

SPS = env-step / wall-second. 워밍업 후 측정하며, 종료 시 reset 비용도 포함한다
(실제 학습이 지불하는 비용이므로 제외하지 않는다).

구성 비교로 광선 캐스팅의 실제 비용을 분리한다.
"""
import argparse, json, os, time
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadrive.envs.metadrive_env import MetaDriveEnv
from md_env import GTStateObservation


def make_env(num_lasers, num_others, use_gt_obs, density, seed=0):
    cfg = dict(
        use_render=False, image_observation=False,
        map="X", traffic_density=density, horizon=1000,
        num_scenarios=1, start_seed=seed, log_level=50,
        vehicle_config=dict(lidar=dict(num_lasers=num_lasers, distance=50, num_others=num_others)),
    )
    if use_gt_obs:
        cfg["agent_observation"] = GTStateObservation
    return MetaDriveEnv(cfg)


def bench_single(num_lasers, num_others, use_gt_obs, density, steps, warmup):
    env = make_env(num_lasers, num_others, use_gt_obs, density)
    obs, _ = env.reset(seed=0)
    rng = np.random.default_rng(0)
    act = lambda: rng.uniform(-1, 1, size=2).astype(np.float32)

    for _ in range(warmup):
        _, _, term, trunc, _ = env.step(act())
        if term or trunc:
            env.reset()

    t0 = time.perf_counter()
    for _ in range(steps):
        _, _, term, trunc, _ = env.step(act())
        if term or trunc:
            env.reset()
    dt = time.perf_counter() - t0
    env.close()
    return steps / dt, obs.shape[0]


CONFIGS = [
    # (라벨, num_lasers, num_others, GT관측클래스 사용)
    ("GT only (광선 0)",      0,   8, True),
    ("GT + 광선 1",           1,   8, False),
    ("GT + 광선 240",       240,   8, False),
    ("광선 240만 (GT 0)",   240,   0, False),
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--warmup", type=int, default=300)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--density", type=float, default=0.4)
    ap.add_argument("--out", default="bench_results/metadrive_single.json")
    a = ap.parse_args()

    rows = []
    for label, nl, no, gt in CONFIGS:
        vals, dim = [], None
        for _ in range(a.repeats):
            s, dim = bench_single(nl, no, gt, a.density, a.steps, a.warmup)
            vals.append(s)
        m, sd = float(np.mean(vals)), float(np.std(vals))
        rows.append(dict(label=label, num_lasers=nl, num_others=no, gt_obs=gt,
                         obs_dim=dim, sps_mean=m, sps_std=sd, sps_runs=vals))
        print(f"{label:20s} obs={dim:3d}  →  {m:8.1f} ± {sd:5.1f} SPS", flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(dict(density=a.density, steps=a.steps, repeats=a.repeats, rows=rows), f, indent=2)
    print(f"\n저장: {a.out}")
