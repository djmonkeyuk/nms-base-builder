import csv
import os
import sys
from copy import deepcopy
from pprint import pprint

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

from automation_utils import get_all_existing_parts

EXISTING_CSV_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "DT_PartDefinition.csv")
# ---,ObjectModel,Category,Icon,SubCategory,SocketClassIDs,PlugClassIDs

headings = ["---", "ObjectModel", "Category", "Icon", "SubCategory", "SocketClassIDs", "PlugClassIDs"]

existing_rows = {}
with open(EXISTING_CSV_FILE) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for idx, row in enumerate(csv_reader):
        if idx == 0:
            continue
        id = row[0]
        existing_rows[id] = row


existing_parts = [str(key.replace("^", "")) for key in existing_rows.keys()]
obj_parts = get_all_existing_parts()
missing_parts = sorted([x for x in obj_parts if x not in existing_parts])
for part in missing_parts:
    existing_rows["^"+part] = ["^"+part, "", "", "", "", "", ""]

# Validate data
UE_model_path = "StaticMesh'/Game/NMSBaseBuilder/Features/Models/"
UE_texture_path = "Texture2D'/Game/NMSBaseBuilder/Features/UI/Icons/"
for key, value in existing_rows.items():
    nice_key = key.replace("^", "")
    value[1] = UE_model_path+nice_key+"."+nice_key+"'"
    value[3] = UE_texture_path+nice_key+"."+nice_key+"'"

build_data = ""
build_data += "---,ObjectModel,Category,Icon,SubCategory,SocketClassIDs,PlugClassIDs\n"
for key, value in existing_rows.items():
    build_data += "{},\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"\n".format(
        value[0], value[1], value[2], value[3], value[4], value[5].replace("\"", "\"\""), value[6].replace("\"", "\"\"")
    )
with open(EXISTING_CSV_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
    csv_file.write(build_data)