"""
UE 5.8 headless data-gen stage 1: capture_check.py
Run: UnrealEditor-Cmd.exe <proj> -run=pythonscript -script="capture_check.py"
Read-only: /Game/Scenes 하위 레벨 목록 + C:\ue\out\scene_i.json 존재 여부만 출력.
Uses EditorAssetLibrary (list_assets/find_asset_data) — 5.8에서도 유효.
"""
import unreal
import os

LEVEL_DIR = "/Game/Scenes"
OUTPUT_DIR = r"C:\ue\out"


def list_scene_levels():
    asset_paths = unreal.EditorAssetLibrary.list_assets(LEVEL_DIR, recursive=True, include_folder=False)
    levels = []
    for p in sorted(asset_paths):
        data = unreal.EditorAssetLibrary.find_asset_data(p)
        if data is None or not data.is_valid():
            continue
        # asset_class (FName)는 deprecated -> asset_class_path (5.1+) 사용
        class_name = str(data.asset_class_path.asset_name) if data.asset_class_path else ""
        if class_name == "World":
            levels.append(p)
    return levels


def json_path_for(level_path):
    name = level_path.rsplit("/", 1)[-1]  # scene_{i}
    return os.path.join(OUTPUT_DIR, "%s.json" % name)


def main():
    levels = list_scene_levels()
    unreal.log("[capture_check] %s 하위 레벨 %d개 발견" % (LEVEL_DIR, len(levels)))

    ok_count = 0
    for idx, level_path in enumerate(levels):
        jpath = json_path_for(level_path)
        has_json = os.path.isfile(jpath)
        status = "OK" if has_json else "MISSING_JSON"
        if has_json:
            ok_count += 1
        unreal.log("[capture_check] (%03d) level=%s json=%s status=%s" % (idx, level_path, jpath, status))

    unreal.log("[capture_check] 확인 완료: 레벨 %d개, json 짝 확인 %d개" % (len(levels), ok_count))


if __name__ == "__main__":
    main()
