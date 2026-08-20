"""체크포인트 교차 평가.

학습된 정책(agent 가중치 + 동결된 obs 정규화 통계)을 지정 시뮬에서 결정론적으로 평가한다.

- 정규화: 학습 시 NormalizeObservation 이 누적한 running mean/var 를 **동결 적용**
  (gymnasium 공식: (obs-mean)/sqrt(var+1e-8), 이후 clip ±10 — 래퍼 스택과 동일).
  이 통계 없이 평가하면 정책이 학습 때와 다른 입력 분포를 받아 전이 실패처럼 보인다.
- 행동: actor_mean (결정론), ClipAction 과 동일하게 [-1,1] 클립.
- 보상: 원시(env) 보상으로 보고 (NormalizeReward 는 학습 전용).

사용:
  evaluate.py --ckpt runs/<run>/ckpt/final.pt --target metadrive --episodes 30
  evaluate.py --run-dir runs/<run> --target metadrive   # ckpt 전부 순회
"""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import torch

import spec

OUTCOMES = ["none", "crash", "out_of_road", "arrive", "timeout"]


def load_agent(ckpt_path, device):
    import gymnasium as gym
    from ppo import Agent

    class _Spaces:  # Agent 가 shape 만 읽으므로 최소 mock
        single_observation_space = gym.spaces.Box(0, 1, (spec.OBS_DIM,), np.float32)
        single_action_space = gym.spaces.Box(-1, 1, (2,), np.float32)

    d = torch.load(ckpt_path, weights_only=False, map_location=device)
    agent = Agent(_Spaces()).to(device)
    agent.load_state_dict(d["model"])
    agent.eval()
    mean = d["obs_mean"].astype(np.float32)
    std = np.sqrt(d["obs_var"].astype(np.float32) + 1e-8)
    return agent, mean, std, d


def _act(agent, obs, mean, std, device):
    x = np.clip((obs - mean) / std, -10, 10).astype(np.float32)
    with torch.no_grad():
        a = agent.actor_mean(torch.from_numpy(x).to(device))
    return np.clip(a.cpu().numpy(), -1.0, 1.0)


def eval_custom(agent, mean, std, episodes, seed, device, n_vehicles=16):
    from env_numba import IntersectionEnv
    E = min(64, episodes)
    env = IntersectionEnv(E, n_vehicles, seed=seed)
    counts = np.zeros(5, int)
    rets, lens = [], []
    ret = np.zeros(E)
    length = np.zeros(E, int)
    obs = env.obs.copy()
    while counts.sum() < episodes:
        o, r, tm, tr, fl = env.step(_act(agent, obs, mean, std, device))
        ret += r
        length += 1
        for e in np.nonzero(tm | tr)[0]:
            if counts.sum() < episodes:
                counts[fl[e]] += 1
                rets.append(float(ret[e]))
                lens.append(int(length[e]))
            ret[e] = 0
            length[e] = 0
        obs = o.copy()
    return counts, rets, lens


def eval_metadrive(agent, mean, std, episodes, seed, device, density=0.1):
    from md_env import MetaDriveGT
    # 에피소드마다 다른 교통 시나리오 (reset seed = start_seed+ep 가 유효 범위이도록)
    env = MetaDriveGT(seed=seed, density=density, num_scenarios=episodes)
    counts = np.zeros(5, int)
    rets, lens = [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        ret, n = 0.0, 0
        while True:
            a = _act(agent, obs[None, :], mean, std, device)[0]
            obs, r, tm, tr, info = env.step(a)
            ret += float(r)
            n += 1
            if tm or tr:
                if info.get("arrive_dest"):
                    counts[3] += 1
                elif info.get("crash"):
                    counts[1] += 1
                elif info.get("out_of_road"):
                    counts[2] += 1
                else:
                    counts[4] += 1
                break
        rets.append(ret)
        lens.append(n)
    env.close()
    return counts, rets, lens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt")
    ap.add_argument("--run-dir")
    ap.add_argument("--target", choices=["custom", "metadrive"], required=True)
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1000)   # 학습 시드와 분리
    ap.add_argument("--out")
    a = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpts = [a.ckpt] if a.ckpt else sorted(glob.glob(f"{a.run_dir}/ckpt/*.pt"))
    rows = []
    for cp in ckpts:
        agent, mean, std, meta = load_agent(cp, device)
        fn = eval_custom if a.target == "custom" else eval_metadrive
        counts, rets, lens = fn(agent, mean, std, a.episodes, a.seed, device)
        n = counts.sum()
        row = dict(ckpt=os.path.basename(cp), elapsed_s=meta["elapsed_s"],
                   global_step=int(meta["global_step"]), target=a.target, episodes=int(n),
                   success_rate=float(counts[3] / n), crash_rate=float(counts[1] / n),
                   out_of_road_rate=float(counts[2] / n), timeout_rate=float(counts[4] / n),
                   mean_return=float(np.mean(rets)), mean_length=float(np.mean(lens)))
        rows.append(row)
        print(f"{os.path.basename(cp):>14} t={meta['elapsed_s']:6.0f}s steps={meta['global_step']:>10,} "
              f"| 성공 {row['success_rate']:.2f} 충돌 {row['crash_rate']:.2f} "
              f"이탈 {row['out_of_road_rate']:.2f} | R {row['mean_return']:.1f}", flush=True)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(rows, f, indent=2)


if __name__ == "__main__":
    main()
