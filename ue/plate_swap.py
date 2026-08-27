"""번호판 실텍스트 스왑 — 커맨드릿 전용 (렌더 무관, 레시피 docs/GEN6_RECIPE.md A-0/A-1).

절차: (0) T_LicensePlate_C 를 PNG 로 export (UV 레이아웃 베이스) ->
(1) PIL 로 번호 텍스트 오버레이 PNG N장 -> (2) 텍스처 임포트 ->
(3) MIC(부모=MI_Veh_LicensePlate, 'Color Tex' 교체) -> (4) GenScenes 레벨 순회하며
차량 StaticMeshActor 의 veh_licensePlate 슬롯에 결정론(시드=장면번호) 지정 -> 저장.
사용: UnrealEditor-Cmd <proj> -run=pythonscript -script="...plate_swap.py probe|apply from to"
"""
import sys

import unreal

BASE_TEX = "/Game/Vehicle/Texture/LicensePlate/T_LicensePlate_C"
PARENT_MI = "/Game/Vehicle/Material/MI/MI_Veh_LicensePlate"  # probe 실측 공용 부모
OUT_DIR = "C:/ue/plate"
N_TEX = 24


def log(*a):
    unreal.log_warning("[plate] " + " ".join(str(x) for x in a))


def probe():
    """자산 실경로·슬롯명 확인 (레시피의 경로 추정 검증)."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for name, klass in (("T_LicensePlate", unreal.Texture2D),
                        ("LicensePlate", unreal.MaterialInterface)):
        found = [str(a.package_name) for a in reg.get_assets_by_class(
                     unreal.TopLevelAssetPath("/Script/Engine", klass.__name__), True)
                 if name.lower() in str(a.package_name).lower()][:8]
        log(klass.__name__, found)
    mesh = unreal.load_asset("/Game/Vehicle/vehCar_vehicle02/Mesh/SM_vehCar_vehicle02")
    if mesh:
        log("슬롯:", [str(m.material_slot_name) for m in mesh.static_materials])
    mi = unreal.load_asset("/Game/Vehicle/vehCar_vehicle02/Material/M_veh_licensePlate")
    if mi:
        log("부모:", mi.get_editor_property("parent"))


def make_pngs(base_png):
    from PIL import Image, ImageDraw, ImageFont
    import random
    rnd = random.Random(3)
    base = Image.open(base_png).convert("RGB") if base_png else Image.new("RGB", (512, 256), (235, 235, 230))
    import os
    os.makedirs(f"{OUT_DIR}/png", exist_ok=True)
    for i in range(N_TEX):
        im = base.copy()
        dr = ImageDraw.Draw(im)
        txt = f"{rnd.randint(1,9)}{chr(rnd.randint(65,90))}{chr(rnd.randint(65,90))} {rnd.randint(1000,9999)}"
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", im.height // 3)
        except OSError:
            font = ImageFont.load_default()
        bb = dr.textbbox((0, 0), txt, font=font)
        dr.text(((im.width - bb[2]) / 2, (im.height - bb[3]) / 2), txt, font=font, fill=(25, 25, 35))
        im.save(f"{OUT_DIR}/png/plate_{i:02d}.png")
    log("PNG", N_TEX, "생성")


def export_base():
    tex = unreal.load_asset(BASE_TEX)
    if not tex:
        log("기본 텍스처 미발견 — probe 로 실경로 확인 필요"); return None
    task = unreal.AssetExportTask()
    task.object = tex
    task.filename = f"{OUT_DIR}/base.png"
    task.automated = True
    task.exporter = unreal.TextureExporterPNG()
    ok = unreal.Exporter.run_asset_export_task(task)
    log("export", ok)
    return f"{OUT_DIR}/base.png" if ok else None


def import_and_mic():
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mics = []
    for i in range(N_TEX):
        t = unreal.AssetImportTask()
        t.filename = f"{OUT_DIR}/png/plate_{i:02d}.png"
        t.destination_path = "/Game/GenScenes/PlateTex"
        t.automated = True; t.save = True; t.replace_existing = True
        tools.import_asset_tasks([t])
        tex = unreal.load_asset(f"/Game/GenScenes/PlateTex/plate_{i:02d}")
        parent = unreal.load_asset(PARENT_MI)
        mic = tools.create_asset(f"MIC_plate_{i:02d}", "/Game/GenScenes/PlateTex",
                                 unreal.MaterialInstanceConstant,
                                 unreal.MaterialInstanceConstantFactoryNew())
        mic.set_editor_property("parent", parent)
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
            mic, "Color Tex", tex)
        unreal.EditorAssetLibrary.save_loaded_asset(mic)
        mics.append(mic)
    log("MIC", len(mics))
    return mics


def apply(frm, to):
    import os
    if not os.path.exists(f"{OUT_DIR}/png/plate_00.png"):
        # UE 파이썬엔 PIL 이 없다 — PNG 는 시스템 파이썬에서 미리 생성 (아래 실행 순서 참조)
        log("PNG 미생성 — 시스템 파이썬으로 make_pngs 를 먼저 실행하라"); return
    mics = import_and_mic()
    import random
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for idx in range(frm, to + 1):
        path = f"/Game/GenScenes/gen_{idx}"
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            continue
        les.load_level(path)
        rnd = random.Random(idx)
        n = 0
        for a in actors_ss.get_all_level_actors():
            if not isinstance(a, unreal.StaticMeshActor):
                continue
            comp = a.static_mesh_component
            mesh = comp.static_mesh
            if not mesh or "veh" not in str(mesh.get_name()).lower():
                continue
            slots = [str(m.material_slot_name) for m in mesh.static_materials]
            for si, sn in enumerate(slots):
                if "licenseplate" in sn.lower():
                    comp.set_material(si, rnd.choice(mics))
                    n += 1
        les.save_current_level()
        log(f"gen_{idx}: 차량 {n}대 번호판 적용")
    log("PLATE_APPLY_DONE")


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else ["probe"]
    if args[0] == "probe":
        probe()
    elif args[0] == "magenta":     # 마스크 패스: 전 번호판을 마젠타 MIC 로 (원복은 apply 재실행)
        import random
        mic = unreal.load_asset("/Game/GenScenes/PlateTex/MIC_plate_magenta")
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        actors_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for idx in range(int(args[1]), int(args[2]) + 1):
            path = f"/Game/GenScenes/gen_{idx}"
            if not unreal.EditorAssetLibrary.does_asset_exist(path):
                continue
            les.load_level(path)
            n = 0
            for a in actors_ss.get_all_level_actors():
                if not isinstance(a, unreal.StaticMeshActor):
                    continue
                comp = a.static_mesh_component
                mesh = comp.static_mesh
                if not mesh:
                    continue
                for si, m in enumerate(mesh.static_materials):
                    if "licenseplate" in str(m.material_slot_name).lower():
                        comp.set_material(si, mic); n += 1
            les.save_current_level()
            log(f"gen_{idx}: 마젠타 {n}")
        log("MAGENTA_DONE")
    elif args[0] in ("white", "revert"):   # 마스크 패스용 일괄 교체/원복
        wm = unreal.load_asset("/Game/GenScenes/MaskMat/M_mask_white")
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        actors_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for idx in range(int(args[1]), int(args[2]) + 1):
            path = f"/Game/GenScenes/gen_{idx}"
            if not unreal.EditorAssetLibrary.does_asset_exist(path):
                continue
            les.load_level(path)
            n = 0
            for a in actors_ss.get_all_level_actors():
                if not isinstance(a, unreal.StaticMeshActor):
                    continue
                comp = a.static_mesh_component
                mesh = comp.static_mesh
                if not mesh:
                    continue
                for si, m in enumerate(mesh.static_materials):
                    if "licenseplate" in str(m.material_slot_name).lower():
                        comp.set_material(si, wm if args[0] == "white" else m.material_interface)
                        n += 1
            les.save_current_level()
            log(f"gen_{idx}: {args[0]} {n}")
        log(f"{args[0].upper()}_DONE")
    else:
        apply(int(args[1]), int(args[2]))
