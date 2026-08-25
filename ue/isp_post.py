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


def match_histogram(a, ref_paths, rng, strength=0.5):
    """실사 참조의 채널별 누적분포에 부분 정합 — 색 통계 격차(sim2real 외관 갭의 정의 요소)를
    직접 줄인다. strength<1 로 원본 톤을 절반 보존해 과보정(회화화)을 막는다."""
    ref = np.asarray(Image.open(rng.choice(ref_paths)).convert("RGB"), dtype=np.float32) / 255.0
    out = a.copy()
    for c in range(3):
        src_sorted = np.sort(a[..., c].ravel())
        ref_q = np.quantile(ref[..., c], np.linspace(0, 1, 257))
        idx = np.searchsorted(src_sorted, a[..., c].ravel()).clip(0, len(src_sorted) - 1)
        ranks = idx / max(1, len(src_sorted) - 1)
        matched = np.interp(ranks, np.linspace(0, 1, 257), ref_q).reshape(a[..., c].shape)
        out[..., c] = (1 - strength) * a[..., c] + strength * matched
    return out.astype(np.float32)


def isp(im, rng, ref_paths=None, hist_only=False):
    """Poisson(샷)+Gaussian(리드) 노이즈, WB 오차, 감마 왜곡, (선택) 실사 색정합.
    hist_only=True 면 색정합만 (디퓨전 전처리용 — 노이즈는 디퓨전 뒤 마지막에)."""
    a = np.asarray(im, dtype=np.float32) / 255.0
    if ref_paths:
        a = match_histogram(a, ref_paths, rng, strength=rng.uniform(0.35, 0.6))
    if hist_only:
        return Image.fromarray((np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))

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
    ref_paths = sorted(glob.glob(sys.argv[3])) if len(sys.argv) > 3 else None   # 3번째 인자 = 실사 글롭
    hist_only = "--hist-only" in sys.argv
    os.makedirs(out_dir, exist_ok=True)
    for f in files:
        rng = np.random.default_rng(abs(hash(os.path.basename(f))) % (2**32))
        im = isp(Image.open(f).convert("RGB"), rng, ref_paths, hist_only)
        out = os.path.join(out_dir, os.path.splitext(os.path.basename(f))[0] + ".jpg")
        # JPEG 재압축 — 실사진의 압축 흔적 통계를 부여 (q 85~92 랜덤)
        im.save(out, "JPEG", quality=95 if hist_only else int(rng.integers(85, 93)), optimize=True)
        print("isp:", os.path.basename(out))


if __name__ == "__main__":
    main()
