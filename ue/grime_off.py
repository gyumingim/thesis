"""오염 레이어 복구 — 스위치 off + Amt 0 (근사 복구: 원 기본값은 바이너리라 미독)."""
import unreal
MEL, EAL = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
def L(s): unreal.log("[gr] " + str(s))
for p in ("/Game/Vehicle/Material/MI/MI_Veh_CarPaint",
          "/Game/Vehicle/Material/MI/MI_Veh_CarPaintNoClear"):
    mi = EAL.load_asset(p)
    if mi is None: continue
    for sw in ("Dirt PI", "Dust PI", "DirtSplatter PI"):
        try: MEL.set_material_instance_static_switch_parameter_value(mi, sw, False)
        except Exception: pass
    for n in ("Dirt Amt PI", "Dirt Opacity PI", "Dust Amt PI", "DirtSplatter Amt PI"):
        MEL.set_material_instance_scalar_parameter_value(mi, n, 0.0)
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi)
L("GRIME_OFF_DONE")
