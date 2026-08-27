"""번호판 슬롯만 마젠타 MIC 로 런타임 스왑 후 촬영 (shot_once 규약) — 원본 샷과 차분해 마스크."""
import os
import time

import unreal

LEVEL = os.environ.get("SHOT_LEVEL", "/Game/GenScenes/gen_180")
OUTPNG = os.environ.get("SHOT_OUT", "C:/ue/plate/mag")
DELAY = float(os.environ.get("SHOT_DELAY", "25"))
S = {"t0": time.time(), "shot": False, "swapped": False}


def world():
    return unreal.find_object(None, LEVEL + "." + LEVEL.split("/")[-1])


def swap():
    mic = unreal.load_asset("/Game/GenScenes/PlateTex/MIC_plate_magenta")
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.StaticMeshActor):
        comp = a.static_mesh_component
        mesh = comp.static_mesh
        if not mesh:
            continue
        for i, m in enumerate(mesh.static_materials):
            if "licenseplate" in str(m.material_slot_name).lower():
                comp.set_material(i, mic); n += 1
    unreal.log("[mag] 스왑 %d 슬롯" % n)


def cb(dt):
    el = time.time() - S["t0"]
    if not S["swapped"] and el > 5:
        S["swapped"] = True; swap()
    if not S["shot"] and el > DELAY:
        S["shot"] = True
        unreal.SystemLibrary.execute_console_command(
            world(), "HighResShot 1280x720 filename=%s" % OUTPNG)
    if S["shot"] and el > DELAY + 8:
        unreal.SystemLibrary.execute_console_command(world(), "quit")


S["h"] = unreal.register_slate_post_tick_callback(cb)
unreal.log("[mag] 등록 %s" % LEVEL)
