"""-game 마스크 샷 — shot_once.py 규약 승계 (slate post-tick + find_object 월드 + 지연).
번호판 슬롯=흰 unlit / 그 외 StaticMesh 전 슬롯=검정 unlit 스왑 후 촬영."""
import os
import time

import unreal

LEVEL = os.environ.get("SHOT_LEVEL", "/Game/GenScenes/gen_180")
OUTPNG = os.environ.get("SHOT_OUT", "C:/ue/plate/mask")
DELAY = float(os.environ.get("SHOT_DELAY", "25"))
S = {"t0": time.time(), "shot": False, "swapped": False}


def L(s):
    unreal.log("[mask] " + str(s))


def world():
    return unreal.find_object(None, LEVEL + "." + LEVEL.split("/")[-1])


def swap():
    w = world()
    wm = unreal.load_asset("/Game/GenScenes/MaskMat/M_mask_white")
    bm = unreal.load_asset("/Game/GenScenes/MaskMat/M_mask_black")
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
        comp = a.static_mesh_component
        mesh = comp.static_mesh
        if not mesh:
            continue
        slots = [str(m.material_slot_name) for m in mesh.static_materials]
        for i, sn in enumerate(slots):
            comp.set_material(i, wm if "licenseplate" in sn.lower() else bm)
        n += 1
    for cmd in ("ShowFlag.Bloom 0", "ShowFlag.Fog 0", "ShowFlag.MotionBlur 0",
                "ShowFlag.Decals 0", "r.TonemapperFilm 0"):
        unreal.SystemLibrary.execute_console_command(w, cmd)
    L("스왑 %d액터" % n)


def cb(dt):
    el = time.time() - S["t0"]
    if not S["swapped"] and el > DELAY - 5:
        S["swapped"] = True
        swap()
    if not S["shot"] and el > DELAY:
        S["shot"] = True
        unreal.SystemLibrary.execute_console_command(
            world(), "HighResShot 1280x720 filename=%s" % OUTPNG)
        L("mask shot @%.0fs" % el)
    if S["shot"] and el > DELAY + 8:
        L("quit"); unreal.SystemLibrary.execute_console_command(world(), "quit")


S["h"] = unreal.register_slate_post_tick_callback(cb)
L("등록 %s" % LEVEL)
