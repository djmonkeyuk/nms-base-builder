"""Utils for automated part extraction."""

import csv
import json
import os
import xml.etree.ElementTree as ET

# THESE PATHS NEED TO BE EDITED TO MATCH YOUR LOCAL FOLDERS---------------------
PATH_TO_UNPACKED = "N:/Games/No Mans Sky/hgpaktool/EXTRACTED/"
PATH_TO_REPO = "N:/Documents/dev/nms-base-builder/automation_tools"

# Base Paths.
LEGACYBASEBUILDINGTABLE = "metadata/reality/tables/legacybasebuildingtable.MXML"
BASEBUILDINGPARTSTABLE = "metadata/reality/tables/basebuildingpartstable.MXML"
BASEBUILDINGTABLE = "metadata/reality/tables/basebuildingobjectstable.MXML"

# Product Tables
PRODUCTTABLE = "metadata/reality/tables/nms_reality_gcproducttable.MXML"
U3PRODUCTTABLE = "metadata/reality/tables/nms_u3reality_gcproducttable.MXML"
MODULARTABLE = "metadata/reality/tables/nms_modularcustomisationproducts.MXML"
BASEPARTPRODUCTSTABLE = "metadata/reality/tables/nms_basepartproducts.MXML"


# Full Base Paths
LEGACYBASEBUILDINGTABLE_PATH = os.path.join(PATH_TO_UNPACKED, LEGACYBASEBUILDINGTABLE)
BASEBUILDINGPARTS_TABLE_PATH = os.path.join(PATH_TO_UNPACKED, BASEBUILDINGPARTSTABLE)
BASEBUILDINGTABLE_PATH = os.path.join(PATH_TO_UNPACKED, BASEBUILDINGTABLE)

# Full Product Paths
PRODUCTTABLE_PATH = os.path.join(PATH_TO_UNPACKED, PRODUCTTABLE)
U3PRODUCTTABLE_PATH = os.path.join(PATH_TO_UNPACKED, U3PRODUCTTABLE)
MODULARTABLE_PATH = os.path.join(PATH_TO_UNPACKED, MODULARTABLE)
BASEPARTPRODUCTSTABLE_PATH = os.path.join(PATH_TO_UNPACKED, BASEPARTPRODUCTSTABLE)


print("Paths")
print(f'BASEBUILDINGPARTS : "{BASEBUILDINGPARTS_TABLE_PATH}"')
print(f'PRODUCT TABLE     "{PRODUCTTABLE_PATH}": ')
print(f'BASEBUILDINGTABLE : "{BASEBUILDINGTABLE_PATH}"')

# -------------------------------------------------------------------------------

IGNORE_LIST = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), "part_generator", "ignore_list.txt"
)

ignore_items = []
with open(IGNORE_LIST, "r") as stream:
    ignore_items = stream.read().split("\n")


PATH_TO_PART_TABLE = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), "part_generator", "DT_PartTable.csv"
)
PART_TABLE_DATA = {}
with open(PATH_TO_PART_TABLE) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=",")
    for row in csv_reader:
        PART_TABLE_DATA[row[0]] = {
            "NiceName": row[1],
            "Category": row[2],
            "SubCategory": row[3],
            "MBINBaseName": row[4],
            "MBINFilePath": row[5],
        }


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_with_color(in_string, color=None):
    if not color:
        print(in_string)
        return
    print("{}{}{}".format(color, in_string, bcolors.ENDC))


def list_missing_icons():
    return get_buildable_ids_and_icons()


def list_missing_parts():
    all_buildable_ids = get_buildable_ids_from_product_table_new()
    parts_tree = ET.parse(BASEBUILDINGPARTS_TABLE_PATH)
    parts_root = parts_tree.getroot()
    parts = parts_root[0]
    parts_data = {}
    for part in parts:
        part_id = get_id_from_part(part)
        parts_data[part_id] = get_model_path_from_part(part)

    all_parts = get_all_existing_parts()
    known_data = {}
    unknown_data = {}
    for buildable_id in all_buildable_ids:
        if buildable_id in ignore_items:
            continue
        if buildable_id not in all_parts:
            if buildable_id in parts_data:
                known_data[buildable_id] = parts_data[buildable_id].replace(
                    ".geometry.mbin.pc", ".scene.mbin"
                )
            elif buildable_id in PART_TABLE_DATA:
                if PART_TABLE_DATA[buildable_id]["MBINFilePath"]:
                    known_data[buildable_id] = PART_TABLE_DATA[buildable_id][
                        "MBINFilePath"
                    ].replace(".geometry.mbin.pc", ".scene.mbin")
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
    return f"{file_name_string.lower()}".replace(".scene.mbin", ".geometry.mbin.pc")


def get_all_existing_parts():
    this_path = os.path.join(os.path.realpath(os.path.dirname(__file__)))
    full_model_path = os.path.join(
        this_path, "..", "src/addons/no_mans_sky_base_builder/models"
    )
    categories = os.listdir(full_model_path)
    all_files = {}
    for category in categories:
        category_path = os.path.join(full_model_path, category)
        files = os.listdir(category_path)
        for file in files:
            part_id = os.path.splitext(file)[0]
            full_path = os.path.join(category_path, file)
            all_files[part_id] = full_path
    return all_files


def get_buildable_ids_from_product_table_new():
    ids = set()
    for path in [LEGACYBASEBUILDINGTABLE_PATH, BASEBUILDINGTABLE_PATH]:
        products_tree = ET.parse(path)
        products_root = products_tree.getroot()
        products = products_root
        for product in products:
            if "name" in product.attrib and product.attrib["name"] == "Objects":
                for object in product:
                    for data in object:
                        if "name" in data.attrib and data.attrib["name"] == "ID":
                            ids.add(data.attrib["value"])
    return ids


def get_buildable_ids_from_product_table(exml):
    category_index = 14
    buildable_value = "BuildingPart"
    products_tree = ET.parse(exml)
    products_root = products_tree.getroot()
    products = products_root[0]
    ids = set()
    for product in products:
        print(product[category_index][0].attrib["value"])
        if product[category_index][0].attrib["value"] == buildable_value:
            ids.add(product[0].attrib["value"])
    return ids


def get_buildable_ids_and_icons():
    ids = {}
    for product_path in [
        PRODUCTTABLE_PATH,
        U3PRODUCTTABLE_PATH,
        MODULARTABLE_PATH,
        BASEPARTPRODUCTSTABLE_PATH,
    ]:
        icon_index = 10
        category_index = 14
        buildable_value = "BuildingPart"
        products_tree = ET.parse(product_path)
        products_root = products_tree.getroot()
        products = products_root[0]
        for product in products:
            if product[category_index][0].attrib["value"] == buildable_value:
                ids[product[0].attrib["value"]] = product[icon_index][0].attrib["value"]
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
    known_parts, unknown_parts = list_missing_parts()
    return [
        part
        for part in list(known_parts.keys()) + list(unknown_parts.keys())
        if get_category_by_id(part) == "Uncategorized"
    ]


def get_unknown_subcategory_parts():
    known_parts, unknown_parts = list_missing_parts()
    return [
        part
        for part in list(known_parts.keys()) + list(unknown_parts.keys())
        if get_subcategory_by_id(part) == "Uncategorized"
    ]
