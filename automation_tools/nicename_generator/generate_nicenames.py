import json
import os
import sys
import xml.etree.ElementTree as ET
from pprint import pprint

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from automation_utils import (
    BASEPARTPRODUCTSTABLE_PATH,
    MODULARTABLE_PATH,
    PATH_TO_UNPACKED,
    PRODUCTTABLE_PATH,
    U3PRODUCTTABLE_PATH,
    get_all_existing_parts,
    get_buildable_ids_from_product_table_new,
)

all_parts = get_all_existing_parts()

loc_files = [
    "nms_loc1_english.MXML",
    "nms_loc4_english.MXML",
    "nms_loc5_english.MXML",
    "nms_loc6_english.MXML",
    "nms_loc7_english.MXML",
    "nms_loc8_english.MXML",
    "nms_loc9_english.MXML",
    "nms_update3_english.MXML",
]
loc_files = [os.path.join(PATH_TO_UNPACKED, "language", path) for path in loc_files]
EXPORT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "export", "nice_names.json"
)


# Build language reference.
data = {}
for path in loc_files:
    language_tree = ET.parse(path)
    language_root = language_tree.getroot()
    local_table = language_root[0]
    for table in local_table:
        id = table[0].attrib["value"]
        data[id] = table[1].attrib["value"]
        # break

# Build
part_ids = get_buildable_ids_from_product_table_new()

product_tables = [
    PRODUCTTABLE_PATH,
    U3PRODUCTTABLE_PATH,
    MODULARTABLE_PATH,
    BASEPARTPRODUCTSTABLE_PATH,
]
language_ref = {}
for product_table in product_tables:
    product_tree = ET.parse(product_table)
    product_root = product_tree.getroot()
    table_root = product_root[0]
    for child in table_root:
        id = child[0].attrib["value"]
        name_ref = child[1].attrib["value"]
        if (child[14][0].attrib["value"] == "BuildingPart") and (name_ref in data):
            language_ref[id] = data[name_ref]

return_dict = {key: language_ref[key] for key in sorted(language_ref)}

with open(EXPORT_PATH, "w") as stream:
    json.dump(return_dict, stream, indent=4)
