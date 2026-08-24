"""CLIP 프로브 AUC — 판별층 실사도 지표.

원리: CLIP 임베딩 위 로지스틱 판별기가 "실사 vs 합성"을 얼마나 쉽게 가르는가.
AUC 1.0 = 한눈에 구별(게임 티), 0.5 = 구별 불가(실사 달성). 소표본이므로
Leave-One-Out 교차검증으로 낙관 편향을 제거한다. 생성기 버전 간 추세 비교 전용
(동일 참조·동일 모델·동일 스크립트 버전 하에서만 유효).

사용: python ue/probe_auc.py --syn "C:/ue/out_cs2/isp/scene_7*.jpg" --ref "C:/ue/ref_real/*.jpg"
"""
import argparse
import glob

import numpy as np
import torch
from PIL import Image


def clip_features(paths, device):
    from transformers import CLIPModel, CLIPProcessor
    name = "openai/clip-vit-large-patch14"
    model = CLIPModel.from_pretrained(name).to(device).eval()
    proc = CLIPProcessor.from_pretrained(name)
    feats = []
    with torch.no_grad():
        for i in range(0, len(paths), 8):
            ims = [Image.open(p).convert("RGB") for p in paths[i:i + 8]]
            inp = proc(images=ims, return_tensors="pt").to(device)
            f = model.get_image_features(**inp)
            if not torch.is_tensor(f):          # 신버전 transformers 는 출력 객체를 반환
                f = getattr(f, "image_embeds", None) or getattr(f, "pooler_output")
            feats.append(torch.nn.functional.normalize(f, dim=-1).cpu())
    return torch.cat(feats).numpy()


def loo_auc(X, y):
    """Leave-One-Out 로지스틱 — sklearn 없이 직접 (의존성 최소화).
    간단 경사하강 로지스틱, 표본이 수십 장이라 충분하다."""
    n = len(y)
    scores = np.zeros(n)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        Xtr, ytr = X[m], y[m]
        w = np.zeros(X.shape[1]); b = 0.0
        for _ in range(300):
            z = Xtr @ w + b
            p = 1.0 / (1.0 + np.exp(-z))
            g = p - ytr
            w -= 0.5 * (Xtr.T @ g / len(ytr) + 1e-3 * w)
            b -= 0.5 * g.mean()
        scores[i] = X[i] @ w + b
    # AUC (순위 기반)
    pos, neg = scores[y == 1], scores[y == 0]
    auc = (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()
    return float(auc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syn", required=True)
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    syn = sorted(glob.glob(a.syn))
    ref = sorted(glob.glob(a.ref))
    assert syn and ref, "입력 없음"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    X = clip_features(syn + ref, device)
    y = np.array([1] * len(syn) + [0] * len(ref))
    auc = loo_auc(X, y)
    print(f"CLIP 프로브 AUC(LOO): {auc:.3f}  (syn n={len(syn)}, ref n={len(ref)})"
          f"  — 1.0=완전구별(게임티), 0.5=구별불가(실사)")


if __name__ == "__main__":
    main()
