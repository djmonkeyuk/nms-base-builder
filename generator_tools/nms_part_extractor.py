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

4. For any unknown paths, find and place relavant mbin paths into the "known_paths.json" file. Unfortunately this is quite a manual process.
5. Keep running the above function until all paths fall in the "known" variable.
6. Using the known list, run the following function in Blender to automate the OBJ export.
7. With all OBJs exported, place them in their correct folder in the tool, and update the asset browser with the relevant info.

"""
import os
import xml.etree.ElementTree as ET

import yaml
from genericpath import exists

PATH_TO_UNPACKED = "F:/Games/No Mans Sky/nms_modding_station/unpacked/"
PATH_TO_MOD_PROJECT = "F:/Games/No Mans Sky/nms_modding_station/projects/BaseTables/"
PATH_TO_REPO = "F:/Documents/dev/nms-base-builder/generator_tools"

KNOWN_PATHS_PATH = os.path.join(
    PATH_TO_REPO,
    "known_paths.yaml"
)
with open(KNOWN_PATHS_PATH, "r") as stream:
    KNOWN_PATHS = yaml.safe_load(stream)

OUTPUT_FOLDER = os.path.join(
    PATH_TO_REPO,
    "OBJ_export"
)


def list_missing_parts(parts_table_exml, product_table_exml):
    all_buildable_ids = get_buildable_ids_from_product_table(product_table_exml)

    parts_tree = ET.parse(parts_table_exml)
    parts_root = parts_tree.getroot()
    parts = parts_root[0]
    parts_data = {}
    for part in parts:
        parts_data[get_id_from_part(part)] = get_model_path_from_part(part)

    all_parts = get_all_existing_parts()
    known_data = {}
    unknown_data = {}
    for buildable_id in all_buildable_ids:
        if buildable_id not in all_parts:
            if buildable_id in parts_data:
                known_data[buildable_id] = parts_data[buildable_id]
            elif buildable_id in KNOWN_PATHS:
                if KNOWN_PATHS[buildable_id]["path"]:
                    known_data[buildable_id] = KNOWN_PATHS[buildable_id]["path"]
                else:
                    unknown_data[buildable_id] = ""
            else:
                unknown_data[buildable_id] = ""

    return known_data, unknown_data

def get_id_from_part(part):
    for child in part:
        attribute = child.attrib
        if attribute["name"] == "ID":
            return attribute["value"].strip("_")

def get_model_path_from_part(part):
    part_id = get_id_from_part(part)
    styles = part[1]
    style_model = styles[0]
    model_Resource = style_model[1]
    file_name = model_Resource[0]
    attribute = file_name.attrib
    file_name_string = attribute["value"]
    return file_name_string

def get_all_existing_parts():
    full_model_path = "F:/Documents/dev/nms-base-builder/src/addons/no_mans_sky_base_builder/models"
    categories = os.listdir(full_model_path)
    all_files = set()
    for category in categories:
        files = os.listdir(os.path.join(full_model_path, category))
        for file in files:
            all_files.add(os.path.splitext(file)[0])
    return all_files

def get_buildable_ids_from_product_table(exml):
    category_index = 14
    buildable_value = "BuildingPart"
    products_tree = ET.parse(exml)
    products_root = products_tree.getroot()
    products = products_root[0]
    ids = set()
    for product in products:
        if (product[category_index][0].attrib["value"] == buildable_value):
            ids.add(product[0].attrib["value"])
    return ids

def get_category_by_id(part_id):
    if part_id not in KNOWN_PATHS:
        return "Uncategorized"
    return KNOWN_PATHS[part_id].get("category", "Uncategorized")

def get_unknown_category_parts():
    known_parts, unknown_parts = list_missing_parts(
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"),
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"),
    )
    return [part for part in list(known_parts.keys())+list(unknown_parts.keys()) if get_category_by_id(part) == "Uncategorized"]

if __name__ == "__main__":

    def process_blender():
        import bpy
        def get_top_level_lods():
            objects = []
            for obj in bpy.data.objects:
                if obj.parent:
                    if obj.parent.name.endswith(".SCENE"):
                        if "LOD" in obj.name:
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
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')
            obj.select_set(True)

        known_parts, unknown_parts = list_missing_parts(
            os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"),
            os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"),
        )

        for idname, path in known_parts.items():
            # Import the mbin
            bpy.ops.nmsdk.import_scene(
                path=os.path.join(PATH_TO_UNPACKED, path)
            )
            # Select the lowest LOD.
            lowest_lod_object = get_lowest_lod()
            select_object_and_below(lowest_lod_object)
            # Export LOD to new obj file.
            category = os.path.join(OUTPUT_FOLDER, get_category_by_id(idname))
            if not os.path.exists(category):
                os.mkdir(category)
            out_file = os.path.join(category, idname+".obj")
            bpy.ops.export_scene.obj(filepath=out_file, use_selection=True, use_materials=False)


    def print_report():
        known_parts, unknown_parts = list_missing_parts(
            os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"),
            os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"),
        )
        print("""
        There are a total of {0} missing parts from the plugin.
        There are {1} parts ready to process.
        There are {2} unknown part paths. Edit the known_paths.yaml to fix this.
        There are {3} parts with an unknown category. Edit the known_paths.yaml to fix this.
        """.format(
            len(known_parts) + len(unknown_parts),
            len(known_parts),
            len(unknown_parts),
            len(get_unknown_category_parts())
        ))

    # Print Report.
    print_report()
    # Process in Blender
    # process_blender()
