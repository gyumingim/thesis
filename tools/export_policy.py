"""PPO 체크포인트(.pt) → carla_drive.py 가 읽는 npz 로 내보내기.

carla_drive.Policy 는 torch 없이 actor_mean 만 numpy 로 재현하므로,
가중치를 전치(nn.Linear 는 (out,in), 추론은 x@W)해 저장하고 관측 정규화
통계(obs_mean, obs_std=sqrt(var)+eps)를 함께 담는다. eps 는 gymnasium
NormalizeObservation 기본값 1e-8 과 일치시킨다.
"""
import argparse

import numpy as np
import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt")
    ap.add_argument("out")
    a = ap.parse_args()

    d = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    sd = d["model"] if isinstance(d, dict) and "model" in d else d
    z = {}
    for i, k in enumerate((0, 2, 4)):          # Sequential 의 Linear 인덱스
        z[f"w{i}"] = sd[f"actor_mean.{k}.weight"].numpy().T.astype(np.float32)
        z[f"b{i}"] = sd[f"actor_mean.{k}.bias"].numpy().astype(np.float32)
    if d.get("obs_mean") is None:
        raise SystemExit("체크포인트에 obs_rms 가 없다 — 정규화 통계 없이는 전이 불가")
    z["obs_mean"] = np.asarray(d["obs_mean"], dtype=np.float32)
    z["obs_std"] = (np.sqrt(np.asarray(d["obs_var"], dtype=np.float32)) + 1e-8).astype(np.float32)
    np.savez(a.out, **z)
    print(a.out, {k: v.shape for k, v in z.items()},
          "steps=%s" % d.get("global_step"))


if __name__ == "__main__":
    main()
