"""정책 롤아웃을 JSON 으로 추출 — CARLA/UE 재현 시각화 입력 (2026-08-28).

경량 시뮬(env_numba)을 정책으로 굴리며 ego·NPC 의 (x, y, yaw, v) 궤적을 기록한다.
좌표는 시뮬 월드(m), yaw 는 라디안(+x 기준 CCW). 성공(도착) 에피소드를 우선 저장한다.

사용:
  python bench/export_rollout.py --ckpt "runs/.../ckpt/final.pt" --out C:/carla/rollout.json \
      --episodes 3 --want-success
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env_numba as EN  # noqa: E402
import spec  # noqa: E402

FLAG_NAME = {0: "진행", 1: "충돌", 2: "이탈", 3: "성공", 4: "시간초과"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--out", default="C:/carla/rollout.json")
    ap.add_argument("--envs", type=int, default=64, help="병렬 실행 수(그중 좋은 것 채택)")
    ap.add_argument("--episodes", type=int, default=3, help="저장할 에피소드 수")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--vehicles", type=int, default=3)
    ap.add_argument("--seed", type=int, default=500000)
    ap.add_argument("--want-success", action="store_true", help="성공 에피소드만 저장")
    a = ap.parse_args()

    ck = sorted(glob.glob(a.ckpt))[-1] if a.ckpt and glob.glob(a.ckpt) else ""
    if ck:
        from evaluate import _act, load_agent
        agent, mean, std, _ = load_agent(ck, "cpu")
        policy = lambda o: _act(agent, o, mean, std, "cpu")   # noqa: E731
    else:
        policy = lambda o: np.random.uniform(-1, 1, (len(o), 2)).astype(np.float32)  # noqa: E731

    env = EN.IntersectionEnv(a.envs, a.vehicles, seed=a.seed)
    obs = env.reset()
    live = [[] for _ in range(a.envs)]     # 진행 중 프레임 버퍼
    done_eps = []
    for t in range(a.steps):
        act = policy(obs)
        obs, rew, *_ = env.step(act)
        for e in range(a.envs):
            npc = env.npc[e]
            keep = np.abs(npc[:, 0]) + np.abs(npc[:, 1]) > 1e-3
            live[e].append(dict(
                ego=[float(env.ego[e, 0]), float(env.ego[e, 1]), float(env.ego[e, 2]), float(env.ego[e, 3])],
                npc=[[float(v[0]), float(v[1]), float(v[2]), float(v[3])] for v in npc[keep]],
                act=[float(act[e, 0]), float(act[e, 1])],      # [조향, 가감속] ∈ [-1,1]
                rew=float(rew[e]), t=int(env.t[e]), n_npc=int(keep.sum())))
            f = int(env.flags[e])
            if f != 0:
                if len(live[e]) > 20 and (not a.want_success or f == 3):
                    done_eps.append(dict(outcome=FLAG_NAME[f], frames=live[e]))
                live[e] = []
        if len(done_eps) >= a.episodes:
            break
    done_eps = sorted(done_eps, key=lambda d: -len(d["frames"]))[:a.episodes]
    meta = dict(dt=float(getattr(spec, "DT", 0.1)),
                ckpt=os.path.basename(ck) if ck else "random",
                lane_width=float(spec.LANE_WIDTH), arm_length=float(spec.ARM_LENGTH),
                center=[70.0, 8.75], episodes=[d["outcome"] for d in done_eps])
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(dict(meta=meta, episodes=done_eps), open(a.out, "w"))
    print("저장:", a.out, "| 에피소드", [f"{d['outcome']}({len(d['frames'])}프레임)" for d in done_eps])


if __name__ == "__main__":
    main()
