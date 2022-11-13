"""Utils for automated part extraction."""
import csv
import json
import os
import xml.etree.ElementTree as ET

# THESE PATHS NEED TO BE EDITED TO MATCH YOUR LOCAL FOLDERS---------------------
PATH_TO_UNPACKED = "N:/Games/No Mans Sky/nms_modding_station/unpacked/"
PATH_TO_MOD_PROJECT = "N:/Games/No Mans Sky/nms_modding_station/projects/BaseTables/"
PATH_TO_REPO = "N:/Documents/dev/nms-base-builder/generator_tools"
#-------------------------------------------------------------------------------

OUTPUT_FOLDER = os.path.join(PATH_TO_REPO, "OBJ_export")


PATH_TO_PART_TABLE = os.path.join(os.path.realpath(os.path.dirname(__file__)), "DT_PartTable.csv")
PART_TABLE_DATA = {}
with open(PATH_TO_PART_TABLE) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    for row in csv_reader:
        PART_TABLE_DATA[row[0]] = {
            "NiceName": row[1],
            "Category": row[2],
            "SubCategory": row[3],
            "MBINBaseName": row[4],
            "MBINFilePath": row[5]
        }

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_with_color(in_string, color=None):
    if not color:
        print(in_string)
        return
    print("{}{}{}".format(color, in_string, bcolors.ENDC))



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
            elif buildable_id in PART_TABLE_DATA:
                if PART_TABLE_DATA[buildable_id]["MBINFilePath"]:
                    known_data[buildable_id] = PART_TABLE_DATA[buildable_id]["MBINFilePath"]
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
    styles = part[1]
    style_model = styles[0]
    model_Resource = style_model[1]
    file_name = model_Resource[0]
    attribute = file_name.attrib
    file_name_string = attribute["value"]
    return file_name_string

def get_all_existing_parts():
    this_path = os.path.join(os.path.realpath(os.path.dirname(__file__)))
    full_model_path = os.path.join(this_path, "..", "src/addons/no_mans_sky_base_builder/models")
    # full_model_path = "F:/Documents/dev/nms-base-builder/src/addons/no_mans_sky_base_builder/models"
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
    if part_id not in PART_TABLE_DATA:
        return "Uncategorized"
    return PART_TABLE_DATA[part_id].get("Category", "Uncategorized")

def get_subcategory_by_id(part_id):
    if part_id not in PART_TABLE_DATA:
        return "Uncategorized"
    return PART_TABLE_DATA[part_id].get("SubCategory", "Uncategorized")

def get_unknown_category_parts():
    known_parts, unknown_parts = list_missing_parts(
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"),
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"),
    )
    return [part for part in list(known_parts.keys())+list(unknown_parts.keys()) if get_category_by_id(part) == "Uncategorized"]

def get_unknown_subcategory_parts():
    known_parts, unknown_parts = list_missing_parts(
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"),
        os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"),
    )
    return [part for part in list(known_parts.keys())+list(unknown_parts.keys()) if get_subcategory_by_id(part) == "Uncategorized"]

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
