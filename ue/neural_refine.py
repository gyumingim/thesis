"""신경망 재렌더링 — UE 렌더를 디퓨전 img2img 로 실사화 (기하·bbox 보존).

레시피 근거 (2026-08-25 조사, 출처는 커밋 로그): RealVisXL V5.0(SDXL 실사 파인튠) +
xinsir ControlNet-Depth, strength 0.35~0.5 + CN 0.5~0.7 조합이 기하 보존과 실사화의
검증된 균형점 (Efficient Domain Augmentation: 구조 가이드 없는 편집은 의미 유효율 ~48%,
가이드 조합은 52~99%). 1280x720 은 SDXL 해상도권이라 리사이즈 없이 처리 = bbox 1:1.

사용:
  python ue/neural_refine.py --src "C:/ue/out_cs2/scene_141.png" --out C:/ue/out_nr \
      --strength 0.4 --cn 0.6
  (--sweep 를 주면 strength {0.3,0.4,0.5} 3판을 _s30/_s40/_s50 접미로 생성)
"""
import argparse
import glob
import os

import numpy as np
import torch
from PIL import Image

PROMPT = ("a real photograph taken from a dashcam, real-world street scene, "
          "photorealistic, natural lighting, detailed asphalt texture, DSLR photo, "
          "high dynamic range, a few pedestrians walking on the sidewalk, "
          "storefront signs, urban street life")
NEGATIVE = ("cartoon, anime, illustration, painting, 3d render, cgi, video game, "
            "unreal engine, low quality, blurry, deformed car, warped geometry, "
            "extra vehicles, people on the road, person in front of car, "
            "watermark, bad anatomy, deformed")


def build_pipe():
    from diffusers import (AutoencoderKL, ControlNetModel,
                           DPMSolverMultistepScheduler,
                           StableDiffusionXLControlNetImg2ImgPipeline)
    controlnet = ControlNetModel.from_pretrained(
        "xinsir/controlnet-depth-sdxl-1.0", torch_dtype=torch.float16)
    vae = AutoencoderKL.from_pretrained(
        "madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
        "SG161222/RealVisXL_V5.0", controlnet=controlnet, vae=vae,
        torch_dtype=torch.float16, variant="fp16").to("cuda")
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, use_karras_sigmas=True)
    try:
        pipe.vae.enable_tiling()          # diffusers 0.40: 파이프라인 메서드가 아니라 VAE 메서드
    except Exception:
        pass
    return pipe


def build_depth():
    from transformers import pipeline as hf_pipeline
    return hf_pipeline("depth-estimation",
                       model="depth-anything/Depth-Anything-V2-Small-hf", device=0)


def depth_map(est, img):
    d = np.array(est(img)["depth"], dtype=np.float32)
    d = (d - d.min()) / (np.ptp(d) + 1e-6) * 255
    return Image.fromarray(d.astype(np.uint8)).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="원본 렌더 글롭 (1280x720)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--strength", type=float, default=0.4)
    ap.add_argument("--cn", type=float, default=0.6)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--sweep", action="store_true", help="strength 0.3/0.4/0.5 3판")
    a = ap.parse_args()
    files = sorted(glob.glob(a.src))
    assert files, "입력 없음"
    os.makedirs(a.out, exist_ok=True)
    pipe = build_pipe()
    est = build_depth()
    strengths = (0.3, 0.4, 0.5) if a.sweep else (a.strength,)
    for f in files:
        src = Image.open(f).convert("RGB")
        ctrl = depth_map(est, src)
        base = os.path.splitext(os.path.basename(f))[0]
        for st in strengths:
            out = pipe(prompt=PROMPT, negative_prompt=NEGATIVE,
                       image=src, control_image=ctrl,
                       strength=st, controlnet_conditioning_scale=a.cn,
                       num_inference_steps=a.steps, guidance_scale=6.0,
                       generator=torch.Generator("cuda").manual_seed(a.seed),
                       ).images[0]
            suffix = f"_s{int(st * 100)}" if a.sweep else ""
            out.save(os.path.join(a.out, f"{base}{suffix}.jpg"), quality=92)
            print("refined:", base, f"strength={st}", flush=True)


if __name__ == "__main__":
    main()
