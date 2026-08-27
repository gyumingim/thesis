# 6세대 구현 레시피 (조사 노트, 2026-08-27)

## A-0. 결론 요약 — 번호판은 데칼이 아니라 '머티리얼 슬롯 스왑'이 정답

로컬 CitySample 에셋을 직접 조사한 결과(코드 실행 없이 파일 검사만), **CitySample 차량의 번호판은 별도 UV 영역 + 전용 머티리얼 슬롯으로 이미 분리되어 있다.** 데칼로 번호판을 붙일 필요가 없고, 붙이면 A-4의 함정들(DBuffer, fade, Lumen 반사 등)을 전부 떠안게 된다.

- `C:\Users\a3162\Documents\Unreal Projects\CitySample\Content\Vehicle\vehCar_vehicle02\Mesh\SM_vehCar_vehicle02.uasset` 의 strings 에서 머티리얼 슬롯명 **`veh_licensePlate`** (및 `veh_carPaint`) 확인 — scene_build_cs.py 가 스폰하는 SM_* 스태틱 메시에 존재.
- 각 차량 폴더의 `Material/M_veh_licensePlate.uasset` 은 MIC 이고, 부모는 공용 `MI_Veh_LicensePlate` → 그 부모가 `M_Veh_FullTexture`.
- `MI_Veh_LicensePlate` 의 텍스처 파라미터명 실측: **`Color Tex`**, `Normal Tex`, `Packed Tex` + 스칼라 `Normal Strength`, 벡터 `Color Tint`, 스태틱 스위치 `Is License Plate`. 참조 텍스처는 공용 `T_LicensePlate_C/_N/_AORM` (+ Police 변형).
- 따라서 레시피: **PIL 로 T_LicensePlate_C 레이아웃 위에 번호 텍스트를 그린 PNG → 텍스처 임포트 → `Color Tex` 만 갈아끼운 MIC → `veh_licensePlate` 슬롯에 지정.** 모든 차량이 같은 텍스처 레이아웃을 공유하므로 UV 를 한 번만 파악하면 된다(에디터에서 T_LicensePlate_C 를 한 번 TGA/PNG 로 export 해서 PIL 베이스로 사용).
- 간판(storefront)은 두 갈래: ① **플레인 메시**(`/Engine/BasicShapes/Plane`) + 텍스처 MIC — scene_build 가 이미 메시 스폰·-game 렌더 검증 완료라 가장 안전. ② Decal Actor — A-2 레시피. 참고로 scene_build 가 이미 쓰는 `/Game/Road/Kit_MeshDecals_A` 는 '메시 데칼'(지오메트리+데칼 머티리얼) 방식이라 디퍼드 데칼 함정이 없다 — 간판도 같은 방식(면에서 1~2cm 띄운 플레인)이 실전적으로 강건.

## A-1. 텍스트→텍스처 생성 — 3가지 경로와 권장안

**권장: PIL → PNG → 커맨드릿(scene_build) 단계에서 정식 텍스처 에셋 임포트.** 이유: 사용자의 확정 사실(메모리)대로 커맨드릿은 렌더는 못 해도 에셋 생성·레벨 저장은 되므로, 렌더 단계(-game)는 아무 변경 없이 유지된다.

```python
# scene_build_cs.py (커맨드릿) 안에서 — PIL 은 UE 파이썬에 pip 설치 가능(UnrealEditor-Cmd -run=pythonscript 로 pip 실행)
# 1) PIL 로 plate PNG 생성 (T_LicensePlate_C export 본을 베이스로 텍스트만 오버레이)
# 2) 임포트
task = unreal.AssetImportTask()
task.filename = 'C:/.../plate_042.png'
task.destination_path = '/Game/GenScenes/PlateTex'
task.automated = True; task.save = True; task.replace_existing = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
tex = unreal.load_asset('/Game/GenScenes/PlateTex/plate_042')
# 3) MIC 생성 (부모 = 차량별 M_veh_licensePlate 그대로 → 노멀/AORM 유지)
at = unreal.AssetToolsHelpers.get_asset_tools()
mic = at.create_asset('MI_plate_042', '/Game/GenScenes/PlateTex',
                      unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
unreal.MaterialEditingLibrary.set_material_instance_parent(mic, unreal.load_asset(
    '/Game/Vehicle/vehCar_vehicle03/Material/M_veh_licensePlate'))
unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mic, 'Color Tex', tex)
# 4) 스폰된 차량 컴포넌트에 슬롯 지정 (레벨에 저장됨)
idx = smc.get_material_index('veh_licensePlate')   # MeshComponent.get_material_index / get_material_slot_names
smc.set_material(idx, mic)
```

**런타임(-game py) 대안** — 커맨드릿 임포트가 싫을 때: [`unreal.RenderingLibrary.import_file_as_texture2d(world, filename)`](https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/Rendering/ImportFileasTexture2D) (KismetRenderingLibrary, BlueprintCallable → -game 파이썬에서 호출 가능, 디스크 PNG/JPG 를 transient Texture2D 로 로드) + `mid = smc.create_dynamic_material_instance(idx)` → `mid.set_texture_parameter_value('Color Tex', tex)`. world 는 확정 사실대로 `unreal.find_object(None, '/Game/맵.맵이름')` 경유.

**Canvas Render Target 경로(비권장)**: `unreal.RenderingLibrary.begin_draw_canvas_to_render_target()` → `canvas.k2_draw_text(폰트,...)` → `end_draw_canvas_to_render_target()`. 폰트 에셋 필요 + RT 는 레벨 저장이 안 되는 transient 라 두 단계 파이프라인과 안 맞는다. 참고: [Render Text to Texture using Canvas Render 2d (포럼)](https://forums.unrealengine.com/t/render-text-to-texture-using-canvas-render-2d/48300), [Creating Textures Using Blueprints and Render Targets (공식)](https://dev.epicgames.com/documentation/en-us/unreal-engine/creating-textures-using-blueprints-and-render-targets?application_version=4.27) — 후자는 DrawMaterialToRenderTarget 이 런타임/컨스트럭션 제약이 있음을 명시.

**함정(로컬 실측)**: `T_LicensePlate_C.uasset` strings 에 `VirtualTextureStreaming` 태그가 존재 — 플레이트 샘플러가 VT 일 가능성. 이 경우 일반 Texture2D 를 파라미터로 꽂으면 샘플러 타입 불일치로 무시/경고가 난다. 대책: 임포트한 텍스처에 `tex.set_editor_property('virtual_texture_streaming', True)` 를 맞춰 주거나, 커맨드릿에서 `unreal.load_asset('/Game/Vehicle/Texture/LicensePlate/T_LicensePlate_C').get_editor_property('virtual_texture_streaming')` 로 실값을 먼저 확인.

## A-2. Decal 스폰·부착·크기 API (간판용)

**커맨드릿(레벨 저장) 경로 — 권장**: scene_build 가 액터를 스폰하는 방식 그대로.
```python
d = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DecalActor, loc, rot)
dc = d.get_component_by_class(unreal.DecalComponent)   # (DecalActor.decal 프로퍼티도 있음)
dc.set_decal_material(sign_mi)          # 또는 dc.set_editor_property('decal_material', mi)
dc.set_editor_property('decal_size', unreal.Vector(10, 128, 256))  # X=투영 깊이, Y/Z=면 크기
dc.set_fade_screen_size(0.0)            # ★ 기본 0.01 — 화면에서 작아지면 사라짐. 반드시 0
dc.set_editor_property('sort_order', 10)
```
- **방향 규약**: 데칼은 **로컬 X 축 방향으로 투영**된다(투영 거리 = decal_size.X 범위). 벽(간판면)에 X 가 꽂히도록 회전을 준다. 예: +Y 를 바라보는 벽이면 yaw=90. 출처: [DecalComponent Python API](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/DecalComponent?application_version=5.4) (decal_size = "Decal size in local space"), [공식 Decal 콘텐츠 예제](https://docs.unrealengine.com/4.26/en-US/Resources/ContentExamples/Decals/1_1) (X 스케일이 투영 거리).
- **런타임(-game py) 경로**: `unreal.GameplayStatics.spawn_decal_at_location(world, mi, size, loc, rot, life_span=0)` / [`spawn_decal_attached(mi, size, attach_to_component, attach_point_name, location, rotation, location_type, life_span)`](https://dev.epicgames.com/documentation/en-us/unreal-engine/BlueprintAPI/Rendering/Decal/SpawnDecalAttached) — 소켓/컴포넌트에 부착되는 DecalComponent 를 반환. BlueprintCallable 이라 -game 파이썬에서 호출 가능. `life_span=0` = 영구.
- **데칼 머티리얼**: Domain=`DeferredDecal`, Blend=`Translucent` 인 마스터가 필요. CitySample 에 텍스처 파라미터가 있는 디퍼드 데칼 마스터가 마땅치 않으면 커맨드릿에서 생성:
```python
mat = at.create_asset('M_SignDecal', '/Game/GenScenes', unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
node = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -384, 0)
node.set_editor_property('parameter_name', 'Tex')
unreal.MaterialEditingLibrary.connect_material_property(node, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
unreal.MaterialEditingLibrary.recompile_material(mat)
```
- **간판의 최강 대안**: 디퍼드 데칼 대신 **벽에서 1~2cm 띄운 플레인 SM + 일반(or Unlit) 머티리얼** — CitySample 건물 트림도 같은 '메시 데칼' 방식(`Content/Building/**/decal/SM_*_decal.uasset` 다수 확인). GBuffer 에 일반 지오메트리로 들어가므로 A-4 함정 전무.

## A-3. CitySample 번호판 위치 찾기 — 실용법

1. **슬롯 기반(권장)**: 번호판 텍스트 교체 자체는 위치를 알 필요가 없다 — `veh_licensePlate` 슬롯 스왑으로 끝(전/후면 플레이트가 같은 슬롯·같은 텍스처를 공유).
2. **위치 좌표가 필요할 때**(예: 데칼을 굳이 쓰거나 crop 검증용):
   - 소켓 조회: `[str(s) for s in smc.get_all_socket_names()]` 에서 plate/license 포함 이름 검색 — CitySample 차량 SM 에 플레이트 소켓이 있다는 문서 근거는 없으므로 기대치 낮게.
   - **머티리얼 섹션 바운드 실측**: 커맨드릿에서 `unreal.EditorStaticMeshLibrary`(또는 StaticMesh 의 section 정보) 로 `veh_licensePlate` 슬롯이 쓰인 섹션의 버텍스 위치를 읽어 국소 바운드를 얻는 방법이 가장 정확. 간단 근사는 액터 바운드: 후면 플레이트 ≈ (바운드 -X 끝, y=0, z≈지상 50~80cm).
   - 비교 사례: CARLA 도 차량 플레이트를 29x12cm 플레인 + `M_LicensePlate_Master` 별도 슬롯으로 처리 — 동일 패턴 ([CARLA vehicle authoring 문서](https://carla.readthedocs.io/en/latest/tuto_content_authoring_vehicles/)).
3. **주의**: `VEH_EXCLUDE` 에 이미 vehicle02 가 빠져 있고 트레일러류도 제외 — 남은 풀(vehicle03/05/06/07/12/13, truck04/08/11, bus10)은 전부 `M_veh_licensePlate` 를 보유함을 파일 목록으로 확인.

## A-4. 데칼 함정 목록 (오프스크린 -game 렌더 기준)

- **fade_screen_size 컬링**: 기본 0.01 — 원거리/저해상도 렌더에서 데칼이 소리 없이 사라짐. 스폰 직후 `set_fade_screen_size(0)` 필수.
- **Receives Decals**: 받는 메시 컴포넌트의 `bReceivesDecals`(기본 True)가 꺼져 있으면 안 그려짐. CitySample 일부 최적화 메시가 꺼놨을 수 있으니 대상 컴포넌트에서 `get_editor_property('receives_decals')` 확인.
- **DBuffer 의존**: UE5 데칼은 DBuffer 경로(depth prepass 필요). 프로젝트 세팅 `r.DBuffer=1`(기본 on). CitySample 은 Nanite/Lumen 을 쓰므로 prepass 는 이미 있음 — 기본값 건드리지만 않으면 안전 ([공식 Decal Materials 문서](https://dev.epicgames.com/documentation/unreal-engine/decal-materials-in-unreal-engine)).
- **Lumen/RT 반사에 데칼 미표시**: 화면 밖 표면의 데칼은 Lumen 반사에 안 비침 ([포럼 리포트](https://forums.unrealengine.com/t/decals-not-being-reflected-in-lumen-raytracing/1575334)). 간판이 유리에 비치는 컷이 아니면 무해.
- **`r.Lumen.AsyncCompute` 순서 버그**: CustomDepth/CustomStencil 을 읽는 데칼 머티리얼이 잘못 그려지는 공식 이슈 [UE-227727](https://issues.unrealengine.com/issue/UE-227727) — 해당 조합을 쓰면 `r.Lumen.AsyncCompute 0`.
- **반투명 표면 위 불가**: 디퍼드 데칼은 유리 등 translucent 위에 안 붙는다.
- **seg 패스 오염**: GT seg 렌더 시 데칼이 클래스 색을 덮어쓴다 — seg 샷 직전에 콘솔 `ShowFlag.Decals 0`.
- **HighResShot 타이밍**: 텍스처 스트리밍 수렴 전 샷을 찍으면 데칼/플레이트 텍스처가 블러리 — 기존 25s 수렴 대기 로직 재사용이면 충분. VT 라면 `r.VT.` 계열 워밍업도 같은 대기로 커버됨.

## B-1/2. diffusers 0.40 + Union(ProMax) — 정확한 시그니처와 호환 확정

**존재·호환 확정**: `StableDiffusionXLControlNetUnionImg2ImgPipeline` 은 [v0.40.0 태그 소스](https://github.com/huggingface/diffusers/blob/v0.40.0/src/diffusers/pipelines/controlnet/pipeline_controlnet_union_sd_xl_img2img.py)에 존재(공식 문서의 소스 링크가 v0.40.0). 최초 도입은 [PR #10131](https://github.com/huggingface/diffusers/pull/10131), 다중 union 모델은 [PR #10747](https://github.com/huggingface/diffusers/pull/10747). 문서: [ControlNetUnion 파이프라인](https://huggingface.co/docs/diffusers/api/pipelines/controlnet_union).

**로드** — ProMax 는 xinsir 원본 리포에서 직접 로드가 안 된다(가중치가 `diffusion_pytorch_model_promax.safetensors` 라는 비표준 이름). 공식 문서 예제가 쓰는 diffusers 포맷 미러를 쓴다(둘 다 HF API 200 확인):
```python
from diffusers import ControlNetUnionModel, StableDiffusionXLControlNetUnionImg2ImgPipeline, AutoencoderKL
controlnet = ControlNetUnionModel.from_pretrained(
    'brad-twinkl/controlnet-union-sdxl-1.0-promax', torch_dtype=torch.float16)  # 또는 OzzyGT/controlnet-union-promax-sdxl-1.0
# depth+seg 만 쓸 거면 무인증 원본도 가능: 'xinsir/controlnet-union-sdxl-1.0' (num_control_type=6)
pipe = StableDiffusionXLControlNetUnionImg2ImgPipeline.from_pretrained(
    'SG161222/RealVisXL_V5.0', controlnet=controlnet, vae=vae, torch_dtype=torch.float16)
```
ProMax `config_promax.json` 은 `num_control_type: 8` 실측(HF raw). 컨트롤 타입 인덱스([ControlNetPlus 공식](https://github.com/xinsir6/ControlNetPlus)): **0=openpose, 1=depth, 2=thick line(scribble/hed/softedge), 3=thin line(canny/lineart/mlsd), 4=normal, 5=segment**, ProMax 추가로 6=tile, 7=repaint(inpaint) — 공식 문서 예제의 `control_mode=[6]`(tile img2img)·`[7]`(inpaint)과 일치.

**호출 — depth+seg 동시 (v0.40.0 소스로 검증한 사실)**:
```python
out = pipe(prompt=PROMPT, negative_prompt=NEG,
           image=src,                                  # img2img 원본
           control_image=[depth_img, seg_img],         # 리스트, 순서가 control_mode 와 대응
           control_mode=[1, 5],                        # depth, segment
           strength=0.3,
           controlnet_conditioning_scale=[0.6, 0.4],   # ★조건별 개별 스케일 지원 (아래 근거)
           num_inference_steps=..., generator=...)
```
- `control_mode: int | list[int]` — "Should reflect the order of conditions in control_image" (공식 docstring).
- 검증(소스 라인): float 스케일은 `[scale]*len(control_mode)` 로 브로드캐스트(파이프라인 L1324-1326), 스텝마다 `cond_scale = [c*s for c,s in zip(...)]` 로 **조건별 리스트가 모델 forward 까지 전달**(L1589). 모델 쪽([controlnet_union.py](https://github.com/huggingface/diffusers/blob/v0.40.0/src/diffusers/models/controlnets/controlnet_union.py)) forward 는 `controlnet_cond: list[Tensor]`, `control_type_idx: list[int]` 를 받아 조건별로 `condition * scale` 적용(L689-698) — 단일 union 모델 + 다중 조건 + 조건별 가중 모두 공식 지원.
- `control_mode` 는 `torch.zeros(num_control_type).scatter_(0, tensor(control_mode), 1)` 원-핫으로 변환(L1352) — xinsir 원본 스크립트의 `union_control_type=torch.Tensor([0,1,0,0,0,1])` 과 등가.
- 검증기는 `max(control_mode) < num_control_type` 만 체크(L788) — depth(1)+seg(5)는 6-타입 원본 union 으로도 됨.
- 함정: `enable_model_cpu_offload` 는 이 파이프라인 문서 예제에서 비권장 주석. VRAM 은 기존 depth CN(fp16 ~2.5GB)과 동급이라 RTX 4060 Laptop 8GB 에서 기존 파이프라인이 돌았다면 그대로 돈다.

## B-3. seg 조건 입력 포맷 — ADE20K 팔레트가 아니라 SAM 스타일

**핵심 발견**: xinsir union 의 segment 조건은 ADE20K 시맨틱 팔레트로 학습되지 않았다.
- 저자 공식 테스트 스크립트 [controlnet_union_test_segment.py](https://github.com/xinsir6/ControlNetPlus/blob/main/controlnet_union_test_segment.py)(raw 로 직접 확인)는 `controlnet_aux.SamDetector.from_pretrained('dhkim2810/MobileSAM')` 로 조건 이미지를 만든다 — **MobileSAM 의 랜덤 색 영역 마스크**.
- [sd-webui-controlnet 토론 #2989](https://github.com/Mikubill/sd-webui-controlnet/discussions/2989)에서도 "`ofade20k` preprocessor does not seem to work" + "union 은 mobile sam random split 을 썼다"는 분석이 일치.

**우리 파이프라인 함의**:
- **Cityscapes/ADE20K 팔레트 GT seg 를 그대로 넣어도 동작은 한다**(모델 입장에선 '색으로 구분된 영역 경계'가 정보의 본체) — 단, 색의 시맨틱 의미는 모델이 모른다. 클래스 의미는 프롬프트가 계속 담당.
- 최적 포맷은 **영역별로 채도 높고 상호 거리가 먼 색** — SAM 출력과 분포가 비슷할수록 좋다. UE GT seg 를 만들 때 클래스(또는 인스턴스)별 색을 max-separated 팔레트로 배정하면 그게 곧 SAM 스타일. Cityscapes 표준 팔레트는 어두운 저채도 색이 많아(도로 128,64,128 등) 한 단계 불리 — **CN 조건용 색과 논문 GT 라벨 팔레트를 분리**하고 매핑 테이블만 유지하는 것을 권장.
- seg 조건은 1024 버킷 해상도로 리사이즈해 넣는다(저자 스크립트 동일). 리사이즈는 반드시 NEAREST.

## B-4. UE 에서 GT seg 추출 — unlit 스왑(주안) vs Custom Stencil(대안)

**주안: 클래스별 unlit 머티리얼 스왑 재렌더** — scene_build 가 액터를 직접 스폰해 클래스를 이미 알고 있으므로 최소 변경. 실전 레시피:
1. 커맨드릿에서 Unlit 마스터 1개 생성(`shading_model=MSM_UNLIT`, VectorParameter→Emissive) + 클래스별 MIC.
2. **같은 -game 프로세스에서 2-샷**: 기존 slate post-tick 콜백에서 ① `HighResShot`(RGB) → ② 파이썬으로 전 액터 전 슬롯 `set_material()` 스왑 + 콘솔 플래그 → 수 틱 대기 → ③ `HighResShot`(seg). 같은 카메라·같은 프로세스라 픽셀 정렬이 보장되고 부팅 35s 를 두 번 안 낸다.
3. seg 샷 직전 콘솔(필수 세트): `ShowFlag.Fog 0`, `ShowFlag.VolumetricFog 0`, `ShowFlag.Decals 0`, `ShowFlag.AntiAliasing 0`(TAA 경계 번짐 방지), `ShowFlag.MotionBlur 0`, `ShowFlag.Bloom 0`, `ShowFlag.DepthOfField 0`, `ShowFlag.Atmosphere 0`(하늘→검정=배경 클래스), `r.ScreenPercentage 100`.
4. **함정 — 톤매퍼·노출**: unlit 이어도 톤맵/노출이 출력색을 뒤튼다. `ShowFlag.EyeAdaptation 0` + `ShowFlag.ToneCurve 0`(또는 `r.TonemapperFilm 0`)을 걸고, 그래도 남는 편차는 **캘리브레이션 1회**(팔레트 색판 렌더 → 입력색↔출력색 LUT) 후 nearest-color 스냅으로 해소. CN 조건용으로만 쓰면 색 편차는 무해하고, 학습 GT 라벨로 겸용할 때만 스냅이 필요.
5. 유리·반투명 슬롯은 unlit 스왑 시 뒤가 비치는 문제 — 차량 유리 슬롯도 불투명 unlit 으로 덮는 게 라벨상 안전.

**대안: Custom Stencil** — 커맨드릿에서 `comp.set_editor_property('render_custom_depth', True)` + `custom_depth_stencil_value=클래스ID`(레벨에 저장됨), `DefaultEngine.ini` 에 `r.CustomDepth=3`, 캡처는 SceneTexture:CustomStencil 을 읽는 PP 머티리얼(Blendable Location=Replacing the Tonemapper 로 톤맵 우회)을 PP 볼륨에 넣고 seg 샷에서만 활성화. 머티리얼 부기 장부가 없어지고 ID 가 정수로 정확하지만, PP 머티리얼 오서링이 추가되고 위 UE-227727 (`r.Lumen.AsyncCompute 0`) 이슈를 피해야 한다. 선례: [TimmHess/UnrealImageCapture](https://github.com/TimmHess/UnrealImageCapture), [roah-work/unreal-synthetic-data-capture](https://github.com/roah-work/unreal-synthetic-data-capture)(HighResShot+CustomStencil 버퍼 덤프), [MathWorks UE 시맨틱 라벨링 가이드](https://www.mathworks.com/help/driving/ug/apply-labels-to-unreal-scene-elements-for-semantic-segmentation-and-object-detection.html) — 전부 stencil 방식. 머티리얼 스왑 방식의 선례는 EasySynth 플러그인.

## C. 최소 변경 diff — c:\Users\a3162\thesis\ue\neural_refine.py

현재 코드(L47-56, L103-105): `ControlNetModel('xinsir/controlnet-depth-sdxl-1.0')` + `StableDiffusionXLControlNetImg2ImgPipeline(RealVisXL_V5.0)` + `pipe(image=src, control_image=ctrl, strength=st, controlnet_conditioning_scale=a.cn)`.

변경은 4줄 축:
```python
# build_pipe()
from diffusers import (AutoencoderKL, ControlNetUnionModel,
                       StableDiffusionXLControlNetUnionImg2ImgPipeline)
controlnet = ControlNetUnionModel.from_pretrained(
    'brad-twinkl/controlnet-union-sdxl-1.0-promax', torch_dtype=torch.float16)
pipe = StableDiffusionXLControlNetUnionImg2ImgPipeline.from_pretrained(
    'SG161222/RealVisXL_V5.0', controlnet=controlnet, vae=vae, torch_dtype=torch.float16)
# 호출부
out = pipe(prompt=PROMPT, negative_prompt=NEGATIVE, image=src,
           control_image=[depth_img, seg_img], control_mode=[1, 5],
           strength=st, controlnet_conditioning_scale=[a.cn, a.cn_seg], ...)
```
주의: 전용 depth 모델(xinsir/controlnet-depth-sdxl-1.0)→union 교체는 depth 단독 품질도 미세하게 달라질 수 있다 — 기존 산출물과 섞이지 않게(코드-데이터 일관성 함정과 동일 논리) 먼저 `control_mode=[1]` 단독으로 기존 depth CN 대비 A/B 를 한 판 뜨고 seg 를 추가할 것.

## 권고

1. 번호판: 데칼 대신 veh_licensePlate 슬롯 스왑으로 구현 — 커맨드릿(scene_build_cs.py)에서 PIL PNG 임포트 + MIC('Color Tex' 파라미터) 생성 + set_material 후 레벨 저장, -game 렌더 단계는 무변경. 시작 전 에디터에서 T_LicensePlate_C 를 1회 export 해 UV 레이아웃 확보, virtual_texture_streaming 실값 확인.
2. 간판: 디퍼드 데칼보다 벽에서 1~2cm 띄운 플레인 SM + 텍스처 MIC(CitySample 메시 데칼과 동일 패턴)를 1순위로. 데칼을 쓰면 fade_screen_size=0, receives_decals 확인, seg 샷에서 ShowFlag.Decals 0 을 반드시 지킬 것.
3. diffusers: v0.40.0 에 StableDiffusionXLControlNetUnionImg2ImgPipeline 존재 확정. ProMax 는 brad-twinkl/controlnet-union-sdxl-1.0-promax(또는 OzzyGT 미러)로 로드, 호출은 control_image=[depth,seg] + control_mode=[1,5] + 조건별 controlnet_conditioning_scale 리스트. 먼저 control_mode=[1] 단독으로 기존 전용 depth CN 과 A/B 후 seg 추가.
4. seg 조건 포맷: ADE20K 팔레트 불요 — union 은 MobileSAM 랜덤 색 마스크로 학습됨. UE GT seg 는 클래스별 고채도 max-separated 색으로 만들고(CN 조건용), 논문 GT 라벨 팔레트와는 매핑 테이블로 분리. 리사이즈는 NEAREST.
5. UE GT seg: 같은 -game 프로세스에서 RGB 샷 → 전 슬롯 unlit MIC 스왑 + ShowFlag/톤맵 차단 콘솔 세트 → seg 샷의 2-샷 구조로 구현(부팅 비용 1회, 픽셀 정렬 보장). 색 정확도가 필요해지면 캘리브레이션 색판 1회 렌더 → LUT 스냅. 차후 정밀화가 필요하면 Custom Stencil + Replacing-the-Tonemapper PP 로 승격(r.CustomDepth=3, r.Lumen.AsyncCompute 0 유의).