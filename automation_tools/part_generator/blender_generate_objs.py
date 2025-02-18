"""This Python script is used to automate the process of getting the part list up to date.

Requirements
    NMSDK
    Blender

How to use this file:
1. Unpack the latest No Mans Sky pak files (Using NMS Modding Station).
2. Convert BASEBUILDINGPARTSTABLE and NMS_REALITY_GCPRODUCTTABLE mbins to their exmls.
3. Run the following command to get two lists - one of known filepaths and one with unknown file paths to any missing parts in the plugin.

        known, unknown = list_missing_parts(
            "F:/Games/No Mans Sky/nms_modding_station/projects/BaseTables/METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML",
            "F:/Games/No Mans Sky/nms_modding_station/projects/BaseTables/METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML",
        )

4. For any unknown p
aths, find and place relavant mbin paths into the "DT_PartTable.csv" file. Unfortunately this is quite a manual process.
5. Keep running the above function until all paths fall in the "known" variable.
6. Using the known list, run the following function in Blender to automate the OBJ export.
7. With all OBJs exported, place them in their correct folder in the tool, and update the asset browser with the relevant info.

"""

import os
import shutil
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from automation_utils import PATH_TO_UNPACKED, get_category_by_id, list_missing_parts

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "OBJ_export")


def process_blender():
    import bpy

    def get_top_level_lods():
        objects = []
        for obj in bpy.data.objects:
            if obj.parent:
                if "LOD" in obj.name:
                    objects.append(obj)
        return objects

    def get_scene_object():
        for obj in bpy.data.objects:
            if obj.name.lower().endswith(".scene"):
                return obj

    def get_lowest_lod():
        lods = get_top_level_lods()
        if lods:
            return lods[-1]
        return get_scene_object()

    def select_object_and_below(obj):
        obj.select_set(True)
        for child in obj.children:
            select_object_and_below(child)
        bpy.context.view_layer.objects.active = obj

    def get_lod_sections():
        lod_items = get_top_level_lods()
        sections = set()
        for item in lod_items:
            sections.add(item.name[:-1])
        return sections

    def get_lod_items_by_sections(lod_section):
        all_lod_items = get_top_level_lods()
        items = []
        for item in all_lod_items:
            if item.name.startswith(lod_section):
                items.append(item)
        return items

    def get_lowest_lods():
        lod_sections = get_lod_sections()
        lods = []
        for lod_section in lod_sections:
            sections_lods = get_lod_items_by_sections(lod_section)
            lods.append(sections_lods[-1])
        return lods

    known_parts, unknown_parts = list_missing_parts()
    for idname, path in known_parts.items():
        path = os.path.join(PATH_TO_UNPACKED, path)
        if not os.path.exists(path):
            raise RuntimeError(f"File does not exist, please check {path}")
    for idname, path in known_parts.items():
        print(f"Processing {idname}")
        path_to_file = os.path.join(PATH_TO_UNPACKED, path)
        print(f"FILE :: {path_to_file}")
        if not os.path.exists(path_to_file):
            print("File does not exist. Skipping.")
        # Import the mbin
        bpy.ops.nmsdk.import_scene(path=str(path_to_file))
        # Select the lowest LOD items.
        lowest_lods = get_lowest_lods()
        # If no lods exist, just select the whole scene.
        if not lowest_lods:
            lowest_lods = [get_scene_object()]
        bpy.ops.object.select_all(action="DESELECT")
        for item in lowest_lods:
            select_object_and_below(item)
        # Combine selection into one.
        bpy.ops.object.join()
        # Export LOD to new obj file.
        category = os.path.join(OUTPUT_FOLDER, get_category_by_id(idname))
        if not os.path.exists(category):
            os.mkdir(category)
        out_file = os.path.join(category, idname + ".fbx")
        bpy.ops.export_scene.fbx(
            filepath=out_file, object_types={"MESH"}, use_selection=True
        )


process_blender()
