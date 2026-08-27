"""번호판 원본 복원 합성 (2026-08-28).

디퓨전이 뭉갠 번호판을 흰-패스 마스크(gain>500)로 찾아 fin_plain(=원본+ISP, 노이즈
통계 동일)의 해당 픽셀을 fin_refined 에 되붙인다. 출력 fin_refined_v2 (v1 보존).
"""
import glob
import os

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = "C:/ue/out_prod/fin_refined_v2"
os.makedirs(OUT, exist_ok=True)
stats = []
for f in sorted(glob.glob("C:/ue/out_cs2/scene_[2345][0-9][0-9].png")):
    i = os.path.basename(f)[6:-4]
    wp = f"C:/ue/out_wp/white_{i}.png"
    fr = f"C:/ue/out_prod/fin_refined/scene_{i}.jpg"
    fp = f"C:/ue/out_prod/fin_plain/scene_{i}.jpg"
    if not (os.path.exists(wp) and os.path.exists(fr) and os.path.exists(fp)):
        continue
    a = np.asarray(Image.open(f).convert("RGB"), dtype=np.int32).sum(2)
    b = np.asarray(Image.open(wp).convert("RGB"), dtype=np.int32).sum(2)
    raw = (b - a) > 550
    # 반사 오검 제거(scene_311 고스트 사고): 번호판 = 소형·납작·조밀 성분만
    lab, ncomp = ndimage.label(raw)
    mask = np.zeros_like(raw)
    for k in range(1, ncomp + 1):
        ys, xs = np.nonzero(lab == k)
        h, w = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
        area = len(ys)
        if 20 <= area <= 2600 and w <= 190 and h <= 70 and area / (h * w) >= 0.45 and w / h >= 1.2:
            mask[lab == k] = True
    if mask.sum() < 20:                       # 번호판 안 보이는 장면
        Image.open(fr).save(f"{OUT}/scene_{i}.jpg", quality=95)
        stats.append(0); continue
    mask = ndimage.binary_dilation(mask, iterations=3).astype(np.float32)
    mask = ndimage.gaussian_filter(mask, 1.5)[..., None]      # 페더
    R = np.asarray(Image.open(fr).convert("RGB"), dtype=np.float32)
    P = np.asarray(Image.open(fp).convert("RGB"), dtype=np.float32)
    outim = (R * (1 - mask) + P * mask).clip(0, 255).astype(np.uint8)
    Image.fromarray(outim).save(f"{OUT}/scene_{i}.jpg", quality=95)
    stats.append(int((mask > 0.5).sum()))
n_hit = sum(1 for s in stats if s > 0)
print(f"합성 {len(stats)}장 | 번호판 검출 {n_hit}장 | 평균 픽셀 {np.mean([s for s in stats if s]):.0f}")
print("최대 마스크 장면:", sorted(range(len(stats)), key=lambda k: -stats[k])[:5])
