"""sKVD 풍(EPE 2105.04619 제안 지표의 실용 구현) — 시맨틱 정합 패치 분포 거리.

전역 KID/KDD 는 "장면 전체 인상"만 재서 클래스별 결함(도로 질감만 가짜, 하늘만 가짜)을
못 가른다. EPE 의 sKVD 는 같은 시맨틱 클래스의 패치끼리만 비교해 구조 보존과 사실성을
동시에 측정 — 분야 사실상 표준. 원논문은 G-buffer 기반 정합이지만 우리는 렌더/실사 양쪽을
SegFormer(cityscapes)로 분할해 클래스-순수 패치를 표집하는 근사판(문헌 관행 준수 범위).

출력: 클래스별 KID(폴리노미얼 커널 MMD, unbiased) + 가중 평균. 낮을수록 실사 분포에 근접.
사용: python ue/skvd_metric.py --fake "C:/ue/out_nr/v51/*.jpg" --real "C:/ue/ref_real/*.jpg"
"""
import argparse
import glob

import numpy as np
import torch
from PIL import Image

# cityscapes trainId 기준 관심 클래스 (SegFormer-b0-cityscapes 출력 인덱스)
CLASSES = {0: "road", 1: "sidewalk", 2: "building", 8: "vegetation",
           10: "sky", 13: "car"}
PATCH, PURITY, MAXP = 96, 0.85, 160     # 패치 크기 / 클래스 순도 / 이미지·클래스당 최대 패치


def build_models(dev):
    from transformers import (SegformerForSemanticSegmentation,
                              SegformerImageProcessor)
    proc = SegformerImageProcessor.from_pretrained(
        "nvidia/segformer-b0-finetuned-cityscapes-1024-1024")
    seg = SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/segformer-b0-finetuned-cityscapes-1024-1024").to(dev).eval()
    vgg = torch.hub.load("pytorch/vision", "vgg16", weights="IMAGENET1K_V1")
    feat = vgg.features.to(dev).eval()   # conv 특징 (EPE 계열이 쓰는 VGG 지각 특징)
    return proc, seg, feat


@torch.no_grad()
def class_patches(files, proc, seg, feat, dev):
    """클래스별 VGG 특징 뱅크 {trainId: [N,D]}"""
    bank = {c: [] for c in CLASSES}
    for f in files:
        img = Image.open(f).convert("RGB")
        inp = proc(images=img, return_tensors="pt").to(dev)
        logits = seg(**inp).logits
        lab = torch.nn.functional.interpolate(
            logits, size=img.size[::-1], mode="bilinear").argmax(1)[0].cpu().numpy()
        arr = np.asarray(img, dtype=np.float32) / 255.0
        H, W = lab.shape
        rng = np.random.default_rng(abs(hash(f)) % 2**32)
        for cid in CLASSES:
            ys, xs = np.where(lab == cid)
            if len(ys) < PATCH * PATCH:
                continue
            crops = []
            for _ in range(MAXP * 4):                 # 순도 필터 감안 과표집
                if len(crops) >= MAXP:
                    break
                i = rng.integers(len(ys))
                y, x = ys[i], xs[i]
                y0 = np.clip(y - PATCH // 2, 0, H - PATCH)
                x0 = np.clip(x - PATCH // 2, 0, W - PATCH)
                if (lab[y0:y0 + PATCH, x0:x0 + PATCH] == cid).mean() < PURITY:
                    continue
                crops.append(arr[y0:y0 + PATCH, x0:x0 + PATCH])
            if not crops:
                continue
            t = torch.from_numpy(np.stack(crops)).permute(0, 3, 1, 2).to(dev)
            t = (t - torch.tensor([.485, .456, .406], device=dev).view(1, 3, 1, 1)) \
                / torch.tensor([.229, .224, .225], device=dev).view(1, 3, 1, 1)
            fe = feat(t).mean(dim=(2, 3))             # [N, 512] GAP
            bank[cid].append(fe.cpu())
    return {c: torch.cat(v).numpy() for c, v in bank.items() if v}


def kid(x, y, subs=8, subsize=100):
    """unbiased polynomial-kernel MMD^2 (KID 정의), 서브샘플 평균"""
    rng = np.random.default_rng(0)
    d = x.shape[1]
    vals = []
    for _ in range(subs):
        a = x[rng.choice(len(x), min(subsize, len(x)), replace=False)]
        b = y[rng.choice(len(y), min(subsize, len(y)), replace=False)]
        kxx = (a @ a.T / d + 1) ** 3
        kyy = (b @ b.T / d + 1) ** 3
        kxy = (a @ b.T / d + 1) ** 3
        m, n = len(a), len(b)
        vals.append((kxx.sum() - np.trace(kxx)) / (m * (m - 1))
                    + (kyy.sum() - np.trace(kyy)) / (n * (n - 1))
                    - 2 * kxy.mean())
    return float(np.mean(vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake", required=True)
    ap.add_argument("--real", required=True)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc, seg, feat = build_models(dev)
    fb = class_patches(sorted(glob.glob(a.fake)), proc, seg, feat, dev)
    rb = class_patches(sorted(glob.glob(a.real)), proc, seg, feat, dev)
    total_w, acc = 0, 0.0
    for cid, name in CLASSES.items():
        if cid not in fb or cid not in rb or min(len(fb[cid]), len(rb[cid])) < 20:
            print(f"{name:11s}: 표본 부족 — 스킵")
            continue
        v = kid(fb[cid], rb[cid])
        w = min(len(fb[cid]), len(rb[cid]))
        acc += v * w; total_w += w
        print(f"{name:11s}: sKVD {v:.4f}  (패치 {len(fb[cid])}/{len(rb[cid])})")
    if total_w:
        print(f"{'WEIGHTED':11s}: sKVD {acc / total_w:.4f}")


if __name__ == "__main__":
    main()
