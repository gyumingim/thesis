"""6세대 1단계: controlnet-union(ProMax) depth+seg 동시 조건 A/B (2026-08-27).

가설: depth 단독은 평평한 인도에서 무정보 -> seg 가 클래스 정체성을 명시하면
sKVD 최약점 인도(0.61)가 개선된다. 레시피 근거 docs/GEN6_RECIPE.md (v0.40 소스 검증).
3판 생성: union_d(모드[1] 단독 — 전용 depth CN 과의 교체 영향 분리), union_ds(depth+seg).
seg 는 SegFormer(cityscapes) 의사분할 -> 클래스별 고채도 랜덤색(union 은 SAM 랜덤색 학습).
"""
import argparse
import glob
import os

import numpy as np
import torch
from PIL import Image

from neural_refine import PRESETS, build_depth, depth_map

PROMPT, NEGATIVE = PRESETS["default"]
PALETTE = {}  # trainId -> 고채도 색 (max-separated)
_rng = np.random.default_rng(7)
for cid in range(19):
    h = _rng.permutation(19)[cid] / 19
    import colorsys
    PALETTE[cid] = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.95, 0.95))


def build_union_pipe():
    from diffusers import (AutoencoderKL, ControlNetUnionModel,
                           DPMSolverMultistepScheduler,
                           StableDiffusionXLControlNetUnionImg2ImgPipeline)
    cn = ControlNetUnionModel.from_pretrained(
        "brad-twinkl/controlnet-union-sdxl-1.0-promax", torch_dtype=torch.float16)
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe = StableDiffusionXLControlNetUnionImg2ImgPipeline.from_pretrained(
        "SG161222/RealVisXL_V5.0", controlnet=cn, vae=vae,
        torch_dtype=torch.float16, variant="fp16").to("cuda")
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, use_karras_sigmas=True)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    return pipe


def build_seg(dev="cuda"):
    from transformers import (SegformerForSemanticSegmentation,
                              SegformerImageProcessor)
    proc = SegformerImageProcessor.from_pretrained(
        "nvidia/segformer-b0-finetuned-cityscapes-1024-1024")
    seg = SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/segformer-b0-finetuned-cityscapes-1024-1024").to(dev).eval()
    return proc, seg


@torch.no_grad()
def seg_map(proc, seg, img):
    """SAM 스타일: 클래스 단색이 아니라 연결요소(인스턴스 근사)별 랜덤 고채소색 —
    union 의 학습 분포(MobileSAM 마스크)에 정합 (1차 A/B 기각 원인 교정, 2026-08-27)."""
    from scipy import ndimage
    import colorsys
    inp = proc(images=img, return_tensors="pt").to("cuda")
    lab = torch.nn.functional.interpolate(
        seg(**inp).logits, size=img.size[::-1], mode="bilinear").argmax(1)[0].cpu().numpy()
    out = np.zeros((*lab.shape, 3), dtype=np.uint8)
    rng = np.random.default_rng(11)
    for cid in np.unique(lab):
        comp, n = ndimage.label(lab == cid)
        for k in range(1, n + 1):
            m = comp == k
            if m.sum() < 400:
                continue
            col = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(rng.uniform(), 0.9, 0.95))
            out[m] = col
    return Image.fromarray(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strength", type=float, default=0.3)
    ap.add_argument("--cn", type=float, default=0.6)
    ap.add_argument("--cn-seg", type=float, default=0.4)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1234)
    a = ap.parse_args()
    files = sorted(glob.glob(a.src))
    assert files
    pipe = build_union_pipe()
    est = build_depth()
    sproc, smod = build_seg()
    for mode, sub in (("d", "union_d"), ("ds", "union_ds")):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    for f in files:
        src = Image.open(f).convert("RGB")
        dep = depth_map(est, src)
        sg = seg_map(sproc, smod, src)
        base = os.path.splitext(os.path.basename(f))[0]
        for mode, sub in (("d", "union_d"), ("ds", "union_ds")):
            imgs = [dep] if mode == "d" else [dep, sg]
            modes = [1] if mode == "d" else [1, 5]
            scales = [a.cn] if mode == "d" else [a.cn, a.cn_seg]
            out = pipe(prompt=PROMPT, negative_prompt=NEGATIVE, image=src,
                       control_image=imgs, control_mode=modes,
                       strength=a.strength, controlnet_conditioning_scale=scales,
                       num_inference_steps=a.steps, guidance_scale=6.0,
                       generator=torch.Generator("cuda").manual_seed(a.seed)).images[0]
            out.save(os.path.join(a.out, sub, f"{base}.jpg"), quality=92)
            print("union:", base, mode, flush=True)
    print("UNION_AB_DONE")


if __name__ == "__main__":
    main()
