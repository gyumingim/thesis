"""-game 마스크 샷: 번호판 슬롯=흰 unlit, 그 외 전부 검정 unlit 스왑 후 촬영.
SHOT_OUT 환경변수는 shot_once.py 와 동일 규약. RGB 샷과 픽셀 정렬 보장(동일 카메라)."""
import os
import unreal

W_MAT = unreal.load_asset("/Game/GenScenes/MaskMat/M_mask_white")
B_MAT = unreal.load_asset("/Game/GenScenes/MaskMat/M_mask_black")
out = os.environ.get("SHOT_OUT", "C:/ue/mask_out")

world = None
for w in unreal.find_all_objects(unreal.World):
    if w.get_name() != "None" and "/Game/GenScenes" in w.get_path_name():
        world = w; break
if world is None:
    worlds = [w for w in unreal.find_all_objects(unreal.World) if w.get_name() != "None"]
    world = worlds[0] if worlds else None

for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
    comp = a.static_mesh_component
    mesh = comp.static_mesh
    if not mesh:
        continue
    slots = [str(m.material_slot_name) for m in mesh.static_materials]
    for i, sn in enumerate(slots):
        comp.set_material(i, W_MAT if "licenseplate" in sn.lower() else B_MAT)

for cmd in ("ShowFlag.Bloom 0", "ShowFlag.Fog 0", "ShowFlag.AmbientOcclusion 0",
            "r.TonemapperFilm 0", "ShowFlag.MotionBlur 0", "ShowFlag.Decals 0"):
    unreal.SystemLibrary.execute_console_command(world, cmd)
unreal.SystemLibrary.execute_console_command(world, f"HighResShot filename={out}")
