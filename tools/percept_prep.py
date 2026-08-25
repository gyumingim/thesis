"""percept v1 4-arm 데이터 준비 (2026-08-26).

4팔: raw(렌더 원본) / plain(ISP만) / refined(색정합+디퓨전+ISP) — 합성 3팔 동일 라벨,
   + real(Udacity 앞 1,000프레임 학습 상한 기준선).
평가: 전 팔 공통 Udacity 뒤 570프레임(시간 분리, 2Hz×6 서브샘플 = 3초 간격이라 누수 미미).
클래스: vehicle 단일(0). Udacity Car+Truck -> 0, Pedestrian 제외. 8px 미만 퇴화 박스 제거.
실험 문항: 디퓨전 정제가 실사 전이 성능을 올리는가 (도메인 갭은 상대비교로 통제, 논문 한계 명시).
"""
import csv
import glob
import json
import os
import random
import shutil

ROOT = "C:/ue/percept"
W, H = 1280, 720
UW, UH = 1920, 1200


def ue_label_lines(js):
    lines = []
    for v in js.get("vehicles", []):
        bb = v.get("bbox2d")
        if not bb:
            continue
        x1, y1, x2, y2 = bb
        x1, x2 = max(0, min(x1, x2)), min(W, max(x1, x2))
        y1, y2 = max(0, min(y1, y2)), min(H, max(y1, y2))
        if x2 - x1 < 8 or y2 - y1 < 8:
            continue
        lines.append(f"0 {(x1+x2)/2/W:.6f} {(y1+y2)/2/H:.6f} {(x2-x1)/W:.6f} {(y2-y1)/H:.6f}")
    return lines


def build_syn_arm(name, img_dir, ext):
    scenes = sorted(int(os.path.basename(f)[6:-5]) for f in glob.glob("C:/ue/out_cs2/scene_[2345][0-9][0-9].json"))
    random.Random(0).shuffle(scenes)
    split = {"val": set(scenes[:36])}
    n = 0
    for sub in ("train", "val"):
        os.makedirs(f"{ROOT}/{name}/images/{sub}", exist_ok=True)
        os.makedirs(f"{ROOT}/{name}/labels/{sub}", exist_ok=True)
    for s in scenes:
        src = f"{img_dir}/scene_{s}{ext}"
        if not os.path.exists(src):
            continue
        js = json.load(open(f"C:/ue/out_cs2/scene_{s}.json"))
        sub = "val" if s in split["val"] else "train"
        shutil.copy(src, f"{ROOT}/{name}/images/{sub}/scene_{s}{ext}")
        with open(f"{ROOT}/{name}/labels/{sub}/scene_{s}.txt", "w") as fp:
            fp.write("\n".join(ue_label_lines(js)))
        n += 1
    with open(f"{ROOT}/{name}.yaml", "w") as fp:
        fp.write(f"path: {ROOT}/{name}\ntrain: images/train\nval: images/val\n"
                 f"test: {ROOT}/udacity_eval/images\nnames:\n  0: vehicle\n")
    print(name, n, "장")


def build_udacity():
    rows = {}
    with open("C:/ue/real_labeled/udacity_crowdai/labels_subset.csv", newline="", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            if r["Label"].strip().lower() == "pedestrian":
                continue
            x1, y1, x2, y2 = (float(r["xmin"]), float(r["ymin"]), float(r["xmax"]), float(r["ymax"]))
            if x2 - x1 < 8 or y2 - y1 < 8:
                continue
            rows.setdefault(r["Frame"].strip(), []).append(
                f"0 {(x1+x2)/2/UW:.6f} {(y1+y2)/2/UH:.6f} {(x2-x1)/UW:.6f} {(y2-y1)/UH:.6f}")
    frames = sorted(f for f in rows if os.path.exists(f"C:/ue/real_labeled/udacity_crowdai/images/{f}"))
    train, ev = frames[:1000], frames[1000:]
    for part, fs in (("udacity_train", train), ("udacity_eval", ev)):
        os.makedirs(f"{ROOT}/{part}/images", exist_ok=True)
        os.makedirs(f"{ROOT}/{part}/labels", exist_ok=True)
        for f in fs:
            shutil.copy(f"C:/ue/real_labeled/udacity_crowdai/images/{f}", f"{ROOT}/{part}/images/{f}")
            with open(f"{ROOT}/{part}/labels/{f[:-4]}.txt", "w") as fp:
                fp.write("\n".join(rows[f]))
        print(part, len(fs), "프레임")
    # real 상한 기준선용 yaml (train=udacity_train, val 겸 test=udacity_eval)
    with open(f"{ROOT}/real.yaml", "w") as fp:
        fp.write(f"path: {ROOT}\ntrain: udacity_train/images\nval: udacity_eval/images\n"
                 f"names:\n  0: vehicle\n")


if __name__ == "__main__":
    build_udacity()
    build_syn_arm("raw", "C:/ue/out_cs2", ".png")
    build_syn_arm("plain", "C:/ue/out_prod/fin_plain", ".jpg")
    build_syn_arm("refined", "C:/ue/out_prod/fin_refined", ".jpg")
    print("PREP_DONE")
