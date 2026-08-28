"""주행선 프로브 — 학습이 진행되며 정책이 차로 경계에 더 붙는가.

§6.2 에서 확인한 것은 실패 **구성**의 이동(충돌 감소·이탈 증가)이었고, 그 원인으로
"판정 경계 밀착"을 가설로 두었다. 이 스크립트는 가설을 직접 잰다: MetaDrive 롤아웃
중 관측의 차로 여유폭 필드를 기록해 체크포인트 간 분포를 비교한다.

관측 규약(§4, docs/REVISION_AUDIT.md): idx 0·1 은 좌/우 여유폭, idx 8 은 차로 내
횡오프셋이며 셋 다 **우(+)** 규약으로 옳다(부호 사건의 영향 없음). 여유폭은 [0,1] 로
정규화돼 있으므로 min(idx0, idx1) 이 작을수록 경계에 가깝다.

경계 밀착 가설의 예측: 후반 체크포인트일수록 min-여유폭의 중앙값과 하위 10분위가 작다.

실행:
  python tools/lane_margin_probe.py --run-dir runs/Intersection__clean_custom__1__... \
      --ckpts t000300.pt final.pt --episodes 20
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, "bench")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bench"))

IDX_LEFT, IDX_RIGHT, IDX_LATOFF = 0, 1, 8


def probe(ckpt, episodes, seed, device):
    import torch
    from evaluate import load_agent, _act
    from md_env import MetaDriveGT

    agent, mean, std = load_agent(ckpt, device)
    env = MetaDriveGT(seed=seed, density=0.1, num_scenarios=episodes)
    margins, latoff, out = [], [], 0
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        while True:
            margins.append(min(float(obs[IDX_LEFT]), float(obs[IDX_RIGHT])))
            latoff.append(float(obs[IDX_LATOFF]) - 0.5)
            a = _act(agent, obs[None, :], mean, std, device)[0]
            obs, _r, tm, tr, info = env.step(a)
            if tm or tr:
                out += bool(info.get("out_of_road"))
                break
    env.close()
    return np.array(margins), np.array(latoff), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--ckpts", nargs="+", default=["t000300.pt", "final.pt"])
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed", type=int, default=500000)
    a = ap.parse_args()
    import torch
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("체크포인트별 차로 여유폭 (작을수록 경계에 붙음). 같은 시드·같은 시나리오.")
    print("  %-12s %8s %8s %8s %8s %6s" % ("ckpt", "중앙값", "10분위", "5분위", "|횡오프셋|", "이탈"))
    rows = []
    for c in a.ckpts:
        path = os.path.join(a.run_dir, "ckpt", c)
        if not os.path.exists(path):
            print("  %-12s 없음" % c)
            continue
        m, lo, out = probe(path, a.episodes, a.seed, device)
        rows.append((c, m, lo))
        print("  %-12s %8.4f %8.4f %8.4f %8.4f %6d" %
              (c, np.median(m), np.percentile(m, 10), np.percentile(m, 5),
               np.mean(np.abs(lo)), out))
    if len(rows) >= 2:
        from scipy import stats
        (c0, m0, _), (c1, m1, _) = rows[0], rows[-1]
        u, p = stats.mannwhitneyu(m0, m1, alternative="greater")
        print()
        print("  Mann-Whitney U (%s 여유폭 > %s): p=%.2e" % (c0, c1, p))
        print("  → p 가 작으면 후반 체크포인트가 경계에 더 붙는다는 뜻이다.")


if __name__ == "__main__":
    main()
