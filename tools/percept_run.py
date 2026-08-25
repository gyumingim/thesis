"""percept v1 4-arm 학습+평가 — YOLOv8n, 각 팔 60ep, 공통 Udacity 532프레임 mAP."""
import json

from ultralytics import YOLO

ARMS = ["raw", "plain", "refined", "real"]
ROOT = "C:/ue/percept"
out = {}
for arm in ARMS:
    data = f"{ROOT}/real.yaml" if arm == "real" else f"{ROOT}/{arm}.yaml"
    model = YOLO("yolov8n.pt")
    model.train(data=data, epochs=60, imgsz=960, batch=16, seed=0, deterministic=True,
                project=f"{ROOT}/runs", name=arm, exist_ok=True, verbose=False, patience=0)
    best = YOLO(f"{ROOT}/runs/{arm}/weights/best.pt")
    split = "val" if arm == "real" else "test"
    m = best.val(data=data, split=split, imgsz=960, verbose=False,
                 project=f"{ROOT}/runs", name=f"eval_{arm}", exist_ok=True)
    out[arm] = {"map50": round(float(m.box.map50), 4), "map5095": round(float(m.box.map), 4),
                "precision": round(float(m.box.mp), 4), "recall": round(float(m.box.mr), 4)}
    print("ARM_DONE", arm, out[arm], flush=True)
json.dump(out, open(f"{ROOT}/results_v1.json", "w"), indent=1)
print("PERCEPT_DONE", out)
