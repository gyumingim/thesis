"""분할화면 대시보드 — CARLA 4레인 + 객체인식 bbox + 판단 로그 오버레이 (2026-08-28).

입력: viz_carla_multi.py 산출(ep{k}_{i}.png + logs.json)
처리: 합성데이터로 학습한 YOLO 검출기(percept refined arm)로 각 프레임 추론 →
      bbox·신뢰도 그리기 → 정책 행동(조향/가감속)·속도·보상·최근접 차량 로그 패널 →
      2x2 격자 합성 → PNG 필름스트립 + GIF.
사용: python tools/viz_dashboard.py --src C:/carla/multi --out figs/carla_dashboard
"""
import argparse
import glob
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/malgun.ttf"
DET_W = "C:/ue/percept/runs/refined/weights/best.pt"


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def draw_panel(img, dets, log, k, fs):
    """한 레인 패널: bbox + 로그 오버레이."""
    d = ImageDraw.Draw(img, "RGBA")
    for (x1, y1, x2, y2, conf) in dets:
        d.rectangle([x1, y1, x2, y2], outline=(0, 220, 120), width=2)
        lab = f"vehicle {conf:.2f}"
        w = d.textlength(lab, font=fs["s"])
        d.rectangle([x1, max(y1 - 15, 0), x1 + w + 6, max(y1 - 15, 0) + 15], fill=(0, 220, 120, 220))
        d.text((x1 + 3, max(y1 - 15, 0) + 1), lab, fill=(0, 40, 20), font=fs["s"])
    # 로그 패널 (좌하단)
    H = img.height
    d.rectangle([0, H - 84, 250, H], fill=(12, 14, 18, 210))
    st, th = log["act"]
    lines = [
        f"레인 {k+1} · t={log['i']:03d} · {log['outcome']}",
        f"조향 {st:+.2f}   가감속 {th:+.2f}",
        f"속도 {log['speed']*3.6:5.1f} km/h   보상 {log['rew']:+.2f}",
        f"인식 차량 {len(dets)}대 (시뮬 NPC {log['n_npc']})",
    ]
    for j, t in enumerate(lines):
        d.text((7, H - 80 + j * 18), t, fill=(235, 238, 245), font=fs["m"])
    # 조향 게이지
    cx, cy, w = 205, H - 12, 36
    d.rectangle([cx - w, cy - 4, cx + w, cy + 4], fill=(60, 66, 78, 255))
    d.rectangle([cx - 2, cy - 8, cx + 2, cy + 8], fill=(150, 156, 170, 255))
    px = cx + int(np.clip(st, -1, 1) * w)
    d.ellipse([px - 6, cy - 6, px + 6, cy + 6], fill=(90, 160, 255, 255))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="C:/carla/multi")
    ap.add_argument("--out", default="figs/carla_dashboard")
    ap.add_argument("--conf", type=float, default=0.42)
    ap.add_argument("--stride", type=int, default=2)
    a = ap.parse_args()

    logs = json.load(open(os.path.join(a.src, "logs.json")))["logs"]
    lanes = sorted(logs.keys(), key=lambda s: int(s[2:]))
    fs = {"s": font(12), "m": font(14), "t": font(22)}

    from ultralytics import YOLO
    model = YOLO(DET_W)

    frames_out = []
    idxs = sorted({l["i"] for l in logs[lanes[0]]})[::a.stride]
    for i in idxs:
        panels = []
        for k, lane in enumerate(lanes):
            f = os.path.join(a.src, f"{lane}_{i:04d}.png")
            if not os.path.exists(f):
                continue
            im = Image.open(f).convert("RGB")
            r = model.predict(np.asarray(im)[:, :, ::-1], conf=a.conf, verbose=False)[0]
            dets = []
            for b in r.boxes:            # 자기 차(화면 하단 중앙 대형 박스)는 제외
                x1, y1, x2, y2 = map(float, b.xyxy[0].tolist())
                area = (x2 - x1) * (y2 - y1) / (im.width * im.height)
                cx, cy = (x1 + x2) / 2 / im.width, (y1 + y2) / 2 / im.height
                if area > 0.22 and 0.3 < cx < 0.7 and cy > 0.45:
                    continue
                dets.append((x1, y1, x2, y2, float(b.conf[0])))
            lg = next((x for x in logs[lane] if x["i"] == i), logs[lane][-1])
            panels.append(draw_panel(im, dets, lg, k, fs))
        if len(panels) < 2:
            continue
        w, h = panels[0].size
        sheet = Image.new("RGB", (w * 2 + 6, h * 2 + 40), (245, 246, 248))
        for j, p in enumerate(panels[:4]):
            sheet.paste(p, ((j % 2) * (w + 6), 34 + (j // 2) * (h + 6)))
        d = ImageDraw.Draw(sheet)
        d.text((8, 6), "경량 시뮬 학습 정책 · CARLA 4개 교차로 동시 재현 · 합성데이터 학습 검출기 실시간 인식",
               fill=(20, 22, 28), font=fs["t"])
        frames_out.append(sheet)
        print("프레임", i, "패널", len(panels), flush=True)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    if not frames_out:
        print("출력 없음"); return
    frames_out[len(frames_out) // 2].save(a.out + ".png")
    small = [f.resize((f.width // 2, f.height // 2)) for f in frames_out]
    small[0].save(a.out + ".gif", save_all=True, append_images=small[1:], duration=130, loop=0)
    print("저장:", a.out + ".png,", a.out + f".gif ({len(small)}프레임)")


if __name__ == "__main__":
    main()
