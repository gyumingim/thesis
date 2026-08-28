"""학습된 정책의 MetaDrive 주행을 탑다운으로 렌더 — 논문 정성 그림용 (2026-08-28).

evaluate.py 와 동일한 관측 정규화·결정론 행동(actor_mean)을 쓴다. 에피소드를 돌며
탑다운 프레임을 모아 필름스트립 PNG 와 GIF 를 만든다.
사용:
  python bench/render_policy.py --ckpt runs/.../ckpt/final.pt --out figs/drive_md \
      --episodes 3 --seed 500000 --tag "MetaDrive 네이티브"
"""
import argparse
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import _act, load_agent  # noqa: E402
from md_env import MetaDriveGT  # noqa: E402


def run(ckpt, out, episodes, seed, every, tag):
    dev = "cpu"
    agent, mean, std, _ = load_agent(ckpt, dev)
    env = MetaDriveGT(seed=seed, density=0.1, num_scenarios=max(episodes, 1))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    strips = []
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + ep)
        frames, done, steps, outcome = [], False, 0, "timeout"
        while not done and steps < 1000:
            a = _act(agent, obs[None], mean, std, dev)[0]
            obs, r, term, trunc, info = env.step(a)
            done = term or trunc
            if steps % every == 0:
                try:
                    f = env._env.render(mode="topdown", window=False,
                                        screen_size=(400, 400), scaling=4,
                                        camera_position=None)
                    if f is not None:
                        frames.append(np.asarray(f))
                except Exception as e:      # 렌더 불가 환경 방어
                    print("render 실패:", e); return
            steps += 1
        for k in ("arrive_dest", "crash", "out_of_road"):
            if info.get(k):
                outcome = {"arrive_dest": "성공", "crash": "충돌", "out_of_road": "이탈"}[k]
                break
        print(f"ep{ep}: {outcome} ({steps}스텝, 프레임 {len(frames)})", flush=True)
        strips.append((outcome, frames))
    save(strips, out, tag)
    env.close()


def save(strips, out, tag):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    picks = 6
    rows = []
    for outcome, frames in strips:
        if not frames:
            continue
        idx = np.linspace(0, len(frames) - 1, picks).astype(int)
        row = []
        for i in idx:
            im = Image.fromarray(frames[i]).convert("RGB")
            side = min(im.size)                      # 중앙 정사각 크롭 (가로 왜곡 방지)
            l, t = (im.width - side) // 2, (im.height - side) // 2
            row.append(im.crop((l, t, l + side, t + side)).resize((240, 240)))
        canvas = Image.new("RGB", (240 * picks + 5 * (picks - 1), 240), (255, 255, 255))
        for j, im in enumerate(row):
            canvas.paste(im, (j * 245, 0))
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, 0, canvas.width - 1, canvas.height - 1],
                    outline=(30, 140, 60) if outcome == "성공" else (200, 40, 40), width=4)
        d.rectangle([4, 4, 250, 26], fill=(255, 255, 255))
        d.text((8, 6), f"{tag} — {outcome}", fill=(20, 20, 20), font=font)
        rows.append(canvas)
    if not rows:
        print("저장할 프레임 없음"); return
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height + 8 for r in rows)), (255, 255, 255))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height + 8
    sheet.save(out + ".png")
    print("저장:", out + ".png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--seed", type=int, default=500000)
    ap.add_argument("--every", type=int, default=15)
    ap.add_argument("--tag", default="정책")
    a = ap.parse_args()
    run(a.ckpt, a.out, a.episodes, a.seed, a.every, a.tag)
