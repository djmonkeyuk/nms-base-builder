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

4. For any unknown paths, find and place relavant mbin paths into the "DT_PartTable.csv" file. Unfortunately this is quite a manual process.
5. Keep running the above function until all paths fall in the "known" variable.
6. Using the known list, run the following function in Blender to automate the OBJ export.
7. With all OBJs exported, place them in their correct folder in the tool, and update the asset browser with the relevant info.

"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from automation_utils import (PATH_TO_MOD_PROJECT, PATH_TO_UNPACKED,
                              get_category_by_id, list_missing_parts)

OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "OBJ_export")

def process_blender():
    import bpy

    def get_top_level_lods():
        objects = []
        for obj in bpy.data.objects:
            if obj.parent:
                if obj.parent.name.endswith(".SCENE"):
                    if ("LOD" in obj.name) and (obj.NMSNode_props.node_types == "Mesh"):
                        objects.append(obj)
        return objects

    def get_scene_object():
        for obj in bpy.data.objects:
            if obj.name.endswith(".SCENE"):
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
            print(item)
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

    known_parts, unknown_parts = list_missing_parts(
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"),
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"),
    )

    for idname, path in known_parts.items():
        # Import the mbin
        bpy.ops.nmsdk.import_scene(
            path=os.path.join(PATH_TO_UNPACKED, path)
        )
        # Select the lowest LOD items.
        lowest_lods = get_lowest_lods()
        # If no lods exist, just select the whole scene.
        if not lowest_lods:
            lowest_lods = [get_scene_object()]
        bpy.ops.object.select_all(action='DESELECT')
        for item in lowest_lods:
            select_object_and_below(item)
        # Export LOD to new obj file.
        category = os.path.join(OUTPUT_FOLDER, get_category_by_id(idname))
        if not os.path.exists(category):
            os.mkdir(category)
        out_file = os.path.join(category, idname+".obj")
        bpy.ops.export_scene.obj(filepath=out_file, use_selection=True, use_materials=False)


process_blender()
