"""테슬라식 서라운드 대시보드 — 카메라 8채널 인지 + BEV 복원 + 정답 대조 (2026-08-28).

카메라만 사용: 각 카메라에서 검출한 차량 bbox 의 하단 중앙을 지면평면(카메라 높이 기지)에
역투영해 자차 기준 (전방, 좌) 좌표를 복원하고, 8채널 결과를 자차 좌표계로 합쳐 BEV 를 만든다.
라이다·레이더·GT 미사용. 정답(gt_bev)은 화면에서 대조용으로만 표시한다.

사용: python tools/tesla_dashboard.py --src C:/carla/tesla --out figs/tesla_view
"""
import argparse
import glob
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DET_W = "C:/ue/percept/runs/refined/weights/best.pt"
FONT = "C:/Windows/Fonts/malgun.ttf"
LAYOUT = [["pillar_left", "front_wide", "pillar_right"],
          ["rear_left", "rear", "rear_right"]]


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def ground_unproject(u, v, cal):
    """이미지 하단점 → 지면평면 교점 → 자차 기준 (전방 x, 좌 y) m.
    percept v0 의 지면평면 기준선과 동일 원리 (카메라 높이·자세 기지)."""
    x_c = (u - cal["cx"]) / cal["fx"]          # 우측 방향 성분
    y_c = (v - cal["cy"]) / cal["fy"]          # 아래 방향 성분
    if y_c <= 1e-3:                            # 지평선 위 → 복원 불가
        return None
    depth = cal["z"] / y_c                     # 카메라 광축 기준 전방 거리
    if depth <= 0.5 or depth > 80:
        return None
    fwd_cam, right_cam = depth, depth * x_c
    th = math.radians(cal["yaw"])              # 카메라 → 차량 좌표 회전
    fwd = fwd_cam * math.cos(th) - right_cam * math.sin(th) + cal["x"]
    right = fwd_cam * math.sin(th) + right_cam * math.cos(th) + cal["y"]
    return (fwd, -right)                       # 좌(+) 좌표계


def draw_bev(size, dets, gts, fs, span=45.0):
    """자차 중심 BEV: 카메라 복원(파랑) vs 정답(노랑)."""
    W = H = size
    im = Image.new("RGB", (W, H), (18, 20, 26))
    d = ImageDraw.Draw(im)
    def to_px(fx, ly):
        return (W / 2 - ly * (W / (2 * span)), H / 2 - fx * (H / (2 * span)))
    for r in (10, 20, 30, 40):
        rr = r * (W / (2 * span))
        d.ellipse([W / 2 - rr, H / 2 - rr, W / 2 + rr, H / 2 + rr], outline=(48, 54, 66))
        d.text((W / 2 + 3, H / 2 - rr - 12), f"{r}m", fill=(90, 98, 112), font=fs["s"])
    d.line([W / 2, 0, W / 2, H], fill=(40, 46, 58)); d.line([0, H / 2, W, H / 2], fill=(40, 46, 58))
    for (fx, ly) in gts:
        x, y = to_px(fx, ly)
        d.rectangle([x - 6, y - 9, x + 6, y + 9], outline=(255, 205, 40), width=2)
    for (fx, ly, cam) in dets:
        x, y = to_px(fx, ly)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(90, 170, 255))
    d.polygon([(W / 2, H / 2 - 11), (W / 2 - 7, H / 2 + 9), (W / 2 + 7, H / 2 + 9)], fill=(235, 240, 250))
    d.text((6, 6), "BEV (카메라 8채널 복원)", fill=(200, 210, 225), font=fs["m"])
    d.text((6, H - 34), "● 카메라 인지", fill=(90, 170, 255), font=fs["s"])
    d.text((6, H - 18), "▢ 정답(GT)", fill=(255, 205, 40), font=fs["s"])
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="C:/carla/tesla")
    ap.add_argument("--out", default="figs/tesla_view")
    ap.add_argument("--conf", type=float, default=0.40)
    a = ap.parse_args()
    calib = json.load(open(os.path.join(a.src, "calib.json")))["rig"]
    logs = json.load(open(os.path.join(a.src, "logs.json")))["logs"]
    fs = {"s": font(11), "m": font(13), "t": font(20)}
    from ultralytics import YOLO
    model = YOLO(DET_W)

    frames_out, err_all = [], []
    for lg in logs:
        i = lg["i"]
        panels, bev_dets = {}, []
        for name, cal in calib.items():
            f = os.path.join(a.src, f"{name}_{i:04d}.png")
            if not os.path.exists(f):
                continue
            im = Image.open(f).convert("RGB")
            r = model.predict(np.asarray(im)[:, :, ::-1], conf=a.conf, verbose=False)[0]
            dr = ImageDraw.Draw(im)
            for b in r.boxes:
                x1, y1, x2, y2 = map(float, b.xyxy[0].tolist())
                area = (x2 - x1) * (y2 - y1) / (im.width * im.height)
                if area > 0.35:
                    continue                       # 자차 보닛 등 초대형 박스 제외
                dr.rectangle([x1, y1, x2, y2], outline=(90, 200, 255), width=2)
                p = ground_unproject((x1 + x2) / 2, y2, cal)
                if p:
                    bev_dets.append((p[0], p[1], name))
                    dr.text((x1 + 2, max(y1 - 13, 0)), f"{p[0]:.0f}m", fill=(90, 200, 255), font=fs["s"])
            dr.rectangle([0, im.height - 17, 96, im.height], fill=(10, 12, 16))
            dr.text((4, im.height - 16), name, fill=(190, 200, 215), font=fs["s"])
            panels[name] = im
        if not panels:
            continue
        pw, ph = next(iter(panels.values())).size
        bev_size = ph * 2 + 6
        bev = draw_bev(bev_size, bev_dets, lg["gt_bev"], fs)
        W = pw * 3 + 12 + bev_size
        sheet = Image.new("RGB", (W, ph * 2 + 46), (245, 246, 248))
        for rix, rowl in enumerate(LAYOUT):
            for cix, nm in enumerate(rowl):
                if nm in panels:
                    sheet.paste(panels[nm], (cix * (pw + 6), 40 + rix * (ph + 6)))
        sheet.paste(bev, (pw * 3 + 12, 40))
        d = ImageDraw.Draw(sheet)
        st_, th_ = lg["act"]
        d.text((8, 8), f"카메라 전용 인지 (라이다·레이더 없음) · 8채널 리그 · t={i:03d} · "
                       f"조향 {st_:+.2f} 가감속 {th_:+.2f} · 속도 {lg['ego'][3]*3.6:.0f} km/h",
               fill=(20, 22, 28), font=fs["t"])
        frames_out.append(sheet)
        # 복원 오차: 각 GT 에 최근접 복원점
        for g in lg["gt_bev"]:
            if bev_dets:
                dmin = min(math.hypot(g[0] - p[0], g[1] - p[1]) for p in bev_dets)
                err_all.append(dmin)
        print("프레임", i, "카메라검출", len(bev_dets), "GT", len(lg["gt_bev"]), flush=True)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    frames_out[len(frames_out) // 2].save(a.out + ".png")
    small = [f.resize((f.width // 2, f.height // 2)) for f in frames_out]
    small[0].save(a.out + ".gif", save_all=True, append_images=small[1:], duration=200, loop=0)
    if err_all:
        e = np.array(err_all)
        print(f"BEV 복원 오차(최근접 매칭, n={len(e)}): 중앙값 {np.median(e):.1f}m, "
              f"p25 {np.percentile(e,25):.1f}m, p75 {np.percentile(e,75):.1f}m")
    print("저장:", a.out + ".png /", a.out + f".gif ({len(small)}프레임)")


if __name__ == "__main__":
    main()
