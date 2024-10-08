import csv
import json
import os
import sys
from copy import deepcopy
from pprint import pprint

root_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
sys.path.append(root_dir)

NICE_NAME_FILE = os.path.join(root_dir, "nicename_generator", "export", "nice_names.json")
with open(NICE_NAME_FILE, "r") as stream:
    nice_name_data = json.load(stream)

from automation_utils import get_all_existing_parts

EXISTING_CSV_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "DT_PartDefinition.csv")
# ---,ObjectModel,Category,Icon,SubCategory,SocketClassIDs,PlugClassIDs

headings = ["---", "ObjectModel", "Category", "Icon", "SubCategory", "SocketClassIDs", "PlugClassIDs", "NiceName", "bShowInDrawer", "VariantOf"]


existing_rows = {}
with open(EXISTING_CSV_FILE) as csv_file:
    csv_reader = csv.reader((x.replace('\0', '') for x in csv_file), delimiter=',')
    line_count = 0
    for idx, row in enumerate(csv_reader):
        if idx == 0:
            continue
        id = row[0]
        existing_rows[id] = row

existing_parts = [str(key.replace("^", "")) for key in existing_rows.keys()]
obj_parts = get_all_existing_parts().keys()
missing_parts = sorted([x for x in obj_parts if x not in existing_parts])
# print(existing_parts)
# print(obj_parts)
for part in missing_parts:
    print(f"Part {part} was missing, adding to the list.")
    existing_rows["^"+part] = ["^"+part, "", "", "", "", "", "", "", "", ""]

# Validate data
update_model_paths = False
UE_model_path = "StaticMesh'/Game/NMSBaseBuilder/Features/Models/"
UE_texture_path = "Texture2D'/Game/NMSBaseBuilder/Features/UI/Icons/"
for key, value in existing_rows.items():
    nice_key = key.replace("^", "")
    if update_model_paths or (value[1] == ""):
        value[1] = UE_model_path+nice_key+"."+nice_key+"'"
    value[3] = UE_texture_path+nice_key+"."+nice_key+"'"
    value[7] = nice_name_data.get(nice_key, "")

build_data = ""
build_data += "---,ObjectModel,Category,Icon,SubCategory,SocketClassIDs,PlugClassIDs,NiceName,bShowInDrawer,VariantOf\n"
for key in sorted(existing_rows.keys()):
    value = existing_rows[key]
    build_data += "{},\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"\n".format(
        value[0], value[1], value[2], value[3], value[4], value[5].replace("\"", "\"\""), value[6].replace("\"", "\"\""), value[7], value[8], value[9]
    )

with open(EXISTING_CSV_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
    csv_file.write(build_data)