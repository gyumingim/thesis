"""렌더 후 ISP(카메라 센서) 후처리 — 게임 티 제거의 포렌식 1순위 계층.

근거 (2026-08-24 조사, 출처는 STATUS/커밋 로그): CG 판별의 최강 단서는 센서 노이즈와
압축 흔적의 부재 (Sensor Pattern Noise 계열, Lyu&Farid). UE 필름그레인은 톤매퍼 그레인이라
실카메라 통계와 다르므로, 렌더 PNG 에 Poisson-Gaussian 노이즈 + JPEG 재압축을 후단 적용한다.

사용: python ue/isp_post.py "C:/ue/out_cs2/scene_*.png" [출력디렉터리]
  출력: <출력디렉터리>/<원본이름>.jpg (기본: 원본 옆 isp/ 하위)
  라벨 JSON 은 기하 불변이므로 그대로 유효하다.
"""
import glob
import os
import sys

import numpy as np
from PIL import Image


def isp(im, rng):
    """Poisson(샷) + Gaussian(리드) 노이즈, 미세 색온도 흔들림, 감마 왜곡."""
    a = np.asarray(im, dtype=np.float32) / 255.0

    # 미세 화이트밸런스 오차 (실카메라 AWB 불완전)
    wb = 1.0 + rng.uniform(-0.02, 0.02, size=3).astype(np.float32)
    a = np.clip(a * wb, 0.0, 1.0)

    # 샷 노이즈: 광자 수 ~ Poisson. 풀웰 스케일을 조명에 따라 랜덤화
    full_well = rng.uniform(500.0, 1500.0)
    a = rng.poisson(a * full_well).astype(np.float32) / full_well

    # 리드 노이즈 (가우시안, 어두운 곳에서 상대적으로 두드러짐)
    a += rng.normal(0.0, rng.uniform(0.006, 0.014), size=a.shape).astype(np.float32)

    # 톤 미세 왜곡 (감마 ±3%)
    a = np.clip(a, 0.0, 1.0) ** rng.uniform(0.97, 1.03)

    return Image.fromarray((np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))


def main():
    pattern = sys.argv[1]
    files = sorted(glob.glob(pattern))
    if not files:
        print("입력 없음:", pattern)
        return
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(files[0]), "isp")
    os.makedirs(out_dir, exist_ok=True)
    for f in files:
        rng = np.random.default_rng(abs(hash(os.path.basename(f))) % (2**32))
        im = isp(Image.open(f).convert("RGB"), rng)
        out = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + ".jpg")
        # JPEG 재압축 — 실사진의 압축 흔적 통계를 부여 (q 85~92 랜덤)
        im.save(out, "JPEG", quality=int(rng.integers(85, 93)), optimize=True)
        print("isp:", os.path.basename(out))


if __name__ == "__main__":
    main()
