"""마스크 패스용 unlit 머티리얼 2종 생성 (커맨드릿 1회)."""
import unreal

def mk(name, rgb):
    path = "/Game/GenScenes/MaskMat"
    if unreal.EditorAssetLibrary.does_asset_exist(f"{path}/{name}"):
        unreal.log_warning(f"[mask] {name} 존재"); return
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    m = tools.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    c = unreal.MaterialEditingLibrary.create_material_expression(
        m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property("constant", unreal.LinearColor(*rgb, 1.0))
    unreal.MaterialEditingLibrary.connect_material_property(
        c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    unreal.log_warning(f"[mask] {name} 생성")

mk("M_mask_white", (1.0, 1.0, 1.0))
mk("M_mask_black", (0.0, 0.0, 0.0))
