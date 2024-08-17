import json
import os
import sys
import xml.etree.ElementTree as ET
from pprint import pprint

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from automation_utils import PATH_TO_MOD_PROJECT, get_all_existing_parts

all_parts = get_all_existing_parts()


LOC1_PATH = "LANGUAGE/NMS_LOC1_ENGLISH.EXML"
LOC4_PATH = "LANGUAGE/NMS_LOC4_ENGLISH.EXML"
LOC5_PATH = "LANGUAGE/NMS_LOC5_ENGLISH.EXML"
LOC6_PATH = "LANGUAGE/NMS_LOC6_ENGLISH.EXML"
LOC7_PATH = "LANGUAGE/NMS_LOC7_ENGLISH.EXML"
LOC8_PATH = "LANGUAGE/NMS_LOC8_ENGLISH.EXML"
UPDATE3_PATH = "LANGUAGE/NMS_UPDATE3_ENGLISH.EXML"
PRODUCT_PATH = "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"
PRODUCT_PATH = os.path.join(PATH_TO_MOD_PROJECT, PRODUCT_PATH)
LOC1_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, LOC1_PATH)
LOC4_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, LOC4_PATH)
LOC5_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, LOC5_PATH)
LOC6_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, LOC6_PATH)
LOC7_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, LOC7_PATH)
LOC8_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, LOC8_PATH)
UPDATE3_FULL_PATH = os.path.join(PATH_TO_MOD_PROJECT, UPDATE3_PATH)
EXPORT_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "export", "nice_names.json")



# Build language reference.
data = {}
for path in [LOC1_FULL_PATH, LOC4_FULL_PATH, LOC5_FULL_PATH, LOC6_FULL_PATH, LOC7_FULL_PATH, LOC8_FULL_PATH, UPDATE3_FULL_PATH]:
    language_tree = ET.parse(path)
    language_root = language_tree.getroot()
    local_table = language_root[0]
    for table in local_table:
        id = table[0].attrib["value"]
        data[id] = table[1].attrib["value"]
        # break

# Build
product_tree = ET.parse(PRODUCT_PATH)
product_root = product_tree.getroot()
table_root = product_root[0]
language_ref = {}
for child in table_root:
    id = child[0].attrib["value"]
    name_ref = child[1].attrib["value"]
    if (child[14][0].attrib["value"] == "BuildingPart") and (name_ref in data):
        language_ref[id] = data[name_ref]


with open(EXPORT_PATH, "w") as stream:
    json.dump(language_ref, stream, indent=4)