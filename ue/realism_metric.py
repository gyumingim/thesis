"""합성 이미지 세트의 실사-유사도(realism) 수치 추적 — CMMD + KID.

왜 FID 가 아닌가 (근거):
  FID 는 특징 분포를 가우시안으로 가정하고 공분산 행렬(2048x2048)을 추정하므로
  표본 수천 장 미만에서는 편향이 크고 값이 불안정하다 (Chong&Forsyth 2020, Bińkowski 2018).
  본 파이프라인은 씬당 수십 장 수준의 소표본이므로:
  - CMMD (Jayasumana et al., CVPR 2024 "Rethinking FID"): CLIP 이미지 임베딩 +
    RBF 커널 MMD. 분포 가정이 없고 소표본에서도 일관된 추정치를 준다.
    Google 공식 구현(google-research/cmmd)의 상수(σ=10, scale=1000, 임베딩 단위정규화)를
    따르되, 원본의 V-통계량(대각 포함) 대신 소표본 친화적인 **불편추정량(U-통계량)** 사용.
  - KID (Bińkowski et al., ICLR 2018): inception 특징 + 3차 다항 커널의 불편 MMD².
    불편추정량이므로 FID 와 달리 표본수 편향이 없음. subset_size=min(표본수, 20).

특징추출기 우선순위 (실행 시 사용한 것을 출력에 명시):
  CMMD: transformers 의 openai/clip-vit-large-patch14 (공식 cmmd 는 -336 변형이지만
        224 변형으로 통일; 절대값 비교는 동일 추출기끼리만 유효)
        → 없으면 torchvision inception_v3 로 대체(출력에 명시; CMMD 논문 정의와 다름)
  KID : torchvision inception_v3 (ImageNet1K 가중치; torch-fidelity 의 TF 포팅 가중치와
        미세하게 다르므로 타 논문 수치와 직접 비교 금지)
        → 없으면 CLIP 특징으로 대체(출력에 명시)
  둘 다 없으면: --allow-debug-extractor 지정 시에만 고정시드 랜덤투영(파이프라인 검증
        전용, 실사도 측정값으로 무효) 사용. 미지정 시 필요 패키지를 안내하고 종료.

소표본 주의사항:
  - 불편추정량 MMD² 는 두 분포가 같으면 기대값 0 이지만 표본에서는 음수가 나올 수 있다
    (정상 동작이며 0 근처라는 뜻). 절대값을 취하지 말고 그대로 기록할 것.
  - n<10 이면 KID 표준편차가 평균과 같은 자릿수로 커진다. 추세 비교는 동일 n 로만.
  - CMMD 절대값은 추출기/해상도/전처리에 민감. 실험 간 비교는 이 스크립트 버전 고정 후.

사용: python ue/realism_metric.py --syn "C:/ue/out_cs2/isp/scene_7*.jpg" \
                                  --ref "C:/ue/ref_real/*.jpg"
옵션: --device cpu|cuda  --batch 8  --kid-subsets 100  --seed 0  --allow-debug-extractor
"""
import argparse
import glob
import json
import sys

import numpy as np
import torch
from PIL import Image

# Windows 콘솔 cp949 대비
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- 특징추출기

def _load_pils(paths):
    """경로 목록 -> RGB PIL 목록. 손상 파일은 건너뛰고 경고."""
    out = []
    for p in paths:
        try:
            out.append(Image.open(p).convert("RGB"))
        except Exception as e:  # noqa: BLE001 - 단순 스킵
            print(f"[경고] 열기 실패, 제외: {p} ({e})", file=sys.stderr)
    return out


def make_clip_extractor(device):
    """transformers CLIP ViT-L/14 임베딩기. 실패 시 None."""
    try:
        from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection
    except ImportError:
        return None, None
    name = "openai/clip-vit-large-patch14"
    proc = CLIPImageProcessor.from_pretrained(name)
    model = CLIPVisionModelWithProjection.from_pretrained(name).to(device).eval()

    @torch.inference_mode()
    def extract(pils, batch):
        embs = []
        for i in range(0, len(pils), batch):
            inp = proc(images=pils[i : i + batch], return_tensors="pt").to(device)
            embs.append(model(**inp).image_embeds.float().cpu())
        return torch.cat(embs).numpy()

    return extract, f"CLIP {name} (transformers, image_embeds 768d)"


def make_inception_extractor(device):
    """torchvision inception_v3 pool 특징(2048d). 실패 시 None."""
    try:
        from torchvision.models import Inception_V3_Weights, inception_v3
    except ImportError:
        return None, None
    w = Inception_V3_Weights.IMAGENET1K_V1
    model = inception_v3(weights=w).to(device).eval()
    model.fc = torch.nn.Identity()  # 최종 pool 특징만
    pre = w.transforms()

    @torch.inference_mode()
    def extract(pils, batch):
        embs = []
        for i in range(0, len(pils), batch):
            x = torch.stack([pre(im) for im in pils[i : i + batch]]).to(device)
            embs.append(model(x).float().cpu())
        return torch.cat(embs).numpy()

    return extract, "Inception-v3 (torchvision IMAGENET1K_V1, pool 2048d)"


def make_debug_extractor(_device):
    """검증 전용 폴백: 64x64 리사이즈 픽셀의 고정시드 랜덤투영 512d.
    의미 있는 실사도 측정이 아님 — 파이프라인/수식 스모크 테스트 용도로만."""
    g = torch.Generator().manual_seed(0)  # 고정시드: 실행 간 재현성
    proj = torch.randn(64 * 64 * 3, 512, generator=g) / (64 * 64 * 3) ** 0.5

    def extract(pils, batch):  # noqa: ARG001 - 배치 불필요(경량)
        xs = []
        for im in pils:
            a = np.asarray(im.resize((64, 64), Image.BICUBIC), dtype=np.float32) / 255.0
            xs.append(a.reshape(-1))
        return (torch.from_numpy(np.stack(xs)) @ proj).numpy()

    return extract, "debug-randproj 512d (검증 전용 — 실사도 값으로 무효!)"


# ---------------------------------------------------------------- MMD 수식

def _rbf_gram(a, b, gamma):
    """RBF 커널 그람행렬 exp(-γ‖a_i-b_j‖²)."""
    aa = (a * a).sum(1)[:, None]
    bb = (b * b).sum(1)[None, :]
    return np.exp(-gamma * np.maximum(aa + bb - 2.0 * a @ b.T, 0.0))


def mmd2_unbiased(k_xx, k_yy, k_xy):
    """MMD² 불편추정량(U-통계량, Gretton 2012 Eq.3): 대각(자기쌍) 제외.
    소표본에서 음수 가능(분포가 가깝다는 뜻) — 절대값 취하지 말 것."""
    m, n = k_xx.shape[0], k_yy.shape[0]
    t_xx = (k_xx.sum() - np.trace(k_xx)) / (m * (m - 1))
    t_yy = (k_yy.sum() - np.trace(k_yy)) / (n * (n - 1))
    return float(t_xx + t_yy - 2.0 * k_xy.mean())


def cmmd(x, y):
    """CMMD: 단위정규화 임베딩 + RBF(σ=10) MMD² × 1000.
    상수는 google-research/cmmd distance.py 와 동일. 단, 원본은 대각 포함
    V-통계량이고 여기서는 불편추정량(대각 제외) — 소표본 지시사항에 따름."""
    x = x / np.linalg.norm(x, axis=1, keepdims=True)
    y = y / np.linalg.norm(y, axis=1, keepdims=True)
    gamma = 1.0 / (2.0 * 10.0**2)
    return 1000.0 * mmd2_unbiased(
        _rbf_gram(x, x, gamma), _rbf_gram(y, y, gamma), _rbf_gram(x, y, gamma)
    )


def _poly3(a, b):
    """KID 다항 커널 (Bińkowski Eq.: (x·y/d + 1)³) — torchmetrics 와 동일."""
    d = a.shape[1]
    return (a @ b.T / d + 1.0) ** 3


def kid(x, y, n_subsets, rng):
    """KID: subset_size=min(n_x, n_y, 20) 씩 복원 없이 뽑아 불편 MMD² 를
    n_subsets 회 평균 (Bińkowski 2018; torchmetrics KernelInceptionDistance 방식).
    torchmetrics 가 설치돼 있으면 그 쪽 poly_mmd 로 교차검증 가능하나,
    의존성 최소화를 위해 동일 수식을 직접 구현."""
    m = min(len(x), len(y), 20)
    vals = []
    for _ in range(n_subsets):
        xs = x[rng.choice(len(x), m, replace=False)]
        ys = y[rng.choice(len(y), m, replace=False)]
        vals.append(mmd2_unbiased(_poly3(xs, xs), _poly3(ys, ys), _poly3(xs, ys)))
    return float(np.mean(vals)), float(np.std(vals)), m


# ---------------------------------------------------------------- 메인

def main():
    ap = argparse.ArgumentParser(description="CMMD/KID 실사-유사도 측정 (소표본용)")
    ap.add_argument("--syn", required=True, help='합성 이미지 글롭, 예: "C:/ue/out_cs2/isp/scene_7*.jpg"')
    ap.add_argument("--ref", required=True, help='실사 기준 이미지 글롭, 예: "C:/ue/ref_real/*.jpg"')
    ap.add_argument("--device", default="cpu", help="cpu|cuda (기본 cpu)")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--kid-subsets", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0, help="KID 부분표본 추출 시드")
    ap.add_argument("--allow-debug-extractor", action="store_true",
                    help="CLIP/torchvision 모두 없을 때 검증용 랜덤투영 특징 허용(측정값 무효)")
    args = ap.parse_args()

    syn_paths = sorted(glob.glob(args.syn, recursive=True))
    ref_paths = sorted(glob.glob(args.ref, recursive=True))
    if len(syn_paths) < 2 or len(ref_paths) < 2:
        sys.exit(f"[오류] 각 세트에 최소 2장 필요 (불편 MMD 정의): syn={len(syn_paths)}, ref={len(ref_paths)}")

    device = torch.device(args.device)
    clip_ex, clip_name = make_clip_extractor(device)
    inc_ex, inc_name = make_inception_extractor(device)

    # CMMD 는 CLIP 우선, KID 는 inception 우선. 없는 쪽은 있는 쪽으로 대체(출력 명시).
    cmmd_ex, cmmd_name = (clip_ex, clip_name) if clip_ex else (inc_ex, (inc_name or "") + " [CLIP 부재 대체]")
    kid_ex, kid_name = (inc_ex, inc_name) if inc_ex else (clip_ex, (clip_name or "") + " [inception 부재 대체]")
    if cmmd_ex is None:  # 둘 다 없음
        if not args.allow_debug_extractor:
            sys.exit(
                "[오류] 특징추출기 없음. 필요 패키지: transformers (CMMD용 CLIP) 및/또는 "
                "torchvision (KID용 inception).\n"
                "  파이프라인 검증만 하려면 --allow-debug-extractor 를 추가하세요 (측정값 무효)."
            )
        dbg_ex, dbg_name = make_debug_extractor(device)
        cmmd_ex = kid_ex = dbg_ex
        cmmd_name = kid_name = dbg_name
        print("[경고] 디버그 추출기 사용 중 — 아래 값은 실사도 측정값이 아님!", file=sys.stderr)

    syn_pils, ref_pils = _load_pils(syn_paths), _load_pils(ref_paths)

    # 동일 추출기면 1회만 계산 (대체 시 이름표만 다르고 함수는 같을 수 있음)
    feats = {}
    for ex in (cmmd_ex, kid_ex):
        if id(ex) not in feats:
            feats[id(ex)] = (ex(syn_pils, args.batch), ex(ref_pils, args.batch))

    cmmd_val = cmmd(*feats[id(cmmd_ex)])
    kid_mean, kid_std, subset = kid(
        *feats[id(kid_ex)], args.kid_subsets, np.random.default_rng(args.seed)
    )

    result = {
        "n_syn": len(syn_pils),
        "n_ref": len(ref_pils),
        "cmmd": round(cmmd_val, 6),
        "cmmd_extractor": cmmd_name,
        "kid_mean": round(kid_mean, 8),
        "kid_std": round(kid_std, 8),
        "kid_subset_size": subset,
        "kid_subsets": args.kid_subsets,
        "kid_extractor": kid_name,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if min(len(syn_pils), len(ref_pils)) < 10:
        print("[주의] n<10 소표본: KID 분산 큼, CMMD/KID 음수 가능(0 근처 의미). "
              "추세 비교는 동일 n·동일 추출기로만.", file=sys.stderr)


if __name__ == "__main__":
    main()
