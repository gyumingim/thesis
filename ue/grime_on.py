"""차량 오염 레이어 켜기 — 공유 부모 MIC 2종에 Dirt/Dust 스위치+Amt (조사 보고 방법1).
주의: CitySample 공유 에셋 변경. 복구는 grime_off.py."""
import unreal
MEL, EAL = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
def L(s): unreal.log("[gr] " + str(s))
for p in ("/Game/Vehicle/Material/MI/MI_Veh_CarPaint",
          "/Game/Vehicle/Material/MI/MI_Veh_CarPaintNoClear"):
    mi = EAL.load_asset(p)
    if mi is None: L("로드 실패 " + p); continue
    for sw in ("Dirt PI", "Dust PI", "DirtSplatter PI"):
        try:
            MEL.set_material_instance_static_switch_parameter_value(mi, sw, True)
            L("%s %s=True" % (mi.get_name(), sw))
        except Exception as e: L("%s %s 실패: %s" % (mi.get_name(), sw, e))
    for n, v in (("Dirt Amt PI", 0.75), ("Dirt Opacity PI", 0.85),
                 ("Dust Amt PI", 0.55), ("DirtSplatter Amt PI", 0.45)):
        ok = MEL.set_material_instance_scalar_parameter_value(mi, n, v)
        L("%s %s=%.2f -> %s" % (mi.get_name(), n, v, ok))
    ok = MEL.set_material_instance_vector_parameter_value(mi, "Dirt Color PI",
        unreal.LinearColor(0.11, 0.085, 0.06, 1.0))
    L("%s DirtColor -> %s" % (mi.get_name(), ok))
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi)
L("GRIME_ON_DONE")
