"""실사 few-shot 파인튜닝 실험 (로드맵 프로토콜, 2026-08-27 사용자 일괄 승인).

문항: 합성(정제) 사전학습이 소량 실사 파인튜닝에서도 이득을 유지하는가.
군: {refined 사전학습 -> 실사 N장 FT} vs {COCO(yolov8n.pt) -> 실사 N장}(대조) × N=25/50/100 × 3시드.
FT 데이터: udacity_train 앞쪽(시간순 최초)에서 N장 — 평가셋(뒤쪽 532)과 최대 시간 분리.
평가: 4-arm 과 동일한 udacity_eval 532프레임 mAP50.
"""
import glob
import json
import os
import shutil

from ultralytics import YOLO

ROOT = "C:/ue/percept"
SIZES = [25, 50, 100]
SEEDS = [0, 1, 2]


def make_subset(n):
    d = f"{ROOT}/ft_{n}"
    if os.path.exists(f"{d}.yaml"):
        return
    frames = sorted(os.path.basename(f) for f in glob.glob(f"{ROOT}/udacity_train/images/*.jpg"))[:n]
    os.makedirs(f"{d}/images", exist_ok=True)
    os.makedirs(f"{d}/labels", exist_ok=True)
    for f in frames:
        shutil.copy(f"{ROOT}/udacity_train/images/{f}", f"{d}/images/{f}")
        shutil.copy(f"{ROOT}/udacity_train/labels/{f[:-4]}.txt", f"{d}/labels/{f[:-4]}.txt")
    with open(f"{d}.yaml", "w") as fp:
        fp.write(f"path: {ROOT}\ntrain: ft_{n}/images\nval: udacity_eval/images\nnames:\n  0: vehicle\n")


if __name__ == "__main__":
    out = {}
    for n in SIZES:
        make_subset(n)
    for base_name, base in [("syn_refined", f"{ROOT}/runs/refined/weights/best.pt"),
                            ("coco", "yolov8n.pt")]:
        for n in SIZES:
            for seed in SEEDS:
                tag = f"ft_{base_name}_{n}_s{seed}"
                model = YOLO(base)
                model.train(data=f"{ROOT}/ft_{n}.yaml", epochs=80, patience=20, imgsz=960,
                            batch=8, seed=seed, deterministic=True, lr0=0.002,
                            project=f"{ROOT}/runs_ft", name=tag, exist_ok=True, verbose=False)
                best = YOLO(f"{ROOT}/runs_ft/{tag}/weights/best.pt")
                m = best.val(data=f"{ROOT}/ft_{n}.yaml", split="val", imgsz=960, verbose=False,
                             project=f"{ROOT}/runs_ft", name=f"eval_{tag}", exist_ok=True)
                out[tag] = {"map50": round(float(m.box.map50), 4), "map5095": round(float(m.box.map), 4)}
                print("FT_DONE", tag, out[tag], flush=True)
    json.dump(out, open(f"{ROOT}/results_ft.json", "w"), indent=1)
    print("FT_ALL_DONE")
