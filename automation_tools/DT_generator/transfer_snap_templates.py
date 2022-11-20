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

headings = ["---", "ObjectModel", "Category", "Icon", "SubCategory", "SocketClassIDs", "PlugClassIDs", "NiceName"]

existing_rows = {}


template_map = {
    "^T_WALL": [
        "^T_ARCH",
        "^T_WALLDIAGONAL",
        "^T_WALL_WIN1",
        "^T_WALL_WIN2",
        "^T_WALL_WIN3",
        "^T_WALL_WINDOW",
        "^T_CHEV_DOOR",
        "^T_CHEV_WALL",
        "^T_CHEV_WIN0",
        "^T_CHEV_WIN1",
        "^T_CHEV_WIN2",
        "^T_DOOR",
        "^T_DOOR1",
        "^T_DOORWINDOW",

        "^S_ARCH",
        "^S_WALL",
        "^S_WALLDIAGONAL",
        "^S_WALL_WIN1",
        "^S_WALL_WIN2",
        "^S_WALL_WIN3",
        "^S_WALL_WINDOW",
        "^S_CHEV_DOOR",
        "^S_CHEV_WALL",
        "^S_CHEV_WIN0",
        "^S_CHEV_WIN1",
        "^S_CHEV_WIN2",
        "^S_DOOR",
        "^S_DOOR1",
        "^S_DOORWINDOW",

        "^F_ARCH",
        "^F_WALL",
        "^F_WALLDIAGONAL",
        "^F_WALL_WIN1",
        "^F_WALL_WIN2",
        "^F_WALL_WIN3",
        "^F_WALL_WINDOW",
        "^F_CHEV_DOOR",
        "^F_CHEV_WALL",
        "^F_CHEV_WIN0",
        "^F_CHEV_WIN1",
        "^F_CHEV_WIN2",
        "^F_DOOR",
        "^F_DOOR1",
        "^F_DOORWINDOW",

        "^C_ARCH",
        "^C_WALL",
        "^C_WALLDIAGONAL",
        "^C_WALL_WIN1",
        "^C_WALL_WIN2",
        "^C_WALL_WIN3",
        "^C_WALL_WINDOW",
        "^C_CHEV_DOOR",
        "^C_CHEV_WALL",
        "^C_CHEV_WIN0",
        "^C_CHEV_WIN1",
        "^C_CHEV_WIN2",
        "^C_DOOR",
        "^C_DOOR1",
        "^C_DOORWINDOW",

        "^M_ARCH",
        "^M_WALL",
        "^M_WALLDIAGONAL",
        "^M_WALL_WIN1",
        "^M_WALL_WIN2",
        "^M_WALL_WIN3",
        "^M_WALL_WINDOW",
        "^M_CHEV_DOOR",
        "^M_CHEV_WALL",
        "^M_CHEV_WIN0",
        "^M_CHEV_WIN1",
        "^M_CHEV_WIN2",
        "^M_DOOR",
        "^M_DOOR1",
        "^M_DOORWINDOW",

        "^W_ARCH",
        "^W_WALL",
        "^W_WALLDIAGONAL",
        "^W_WALL_WIN1",
        "^W_WALL_WIN2",
        "^W_WALL_WIN3",
        "^W_WALL_WINDOW",
        "^W_CHEV_DOOR",
        "^W_CHEV_WALL",
        "^W_CHEV_WIN0",
        "^W_CHEV_WIN1",
        "^W_CHEV_WIN2",
        "^W_DOOR",
        "^W_DOOR1",
        "^W_DOORWINDOW",
    ],

    "^T_FLOOR": [
        "^T_GFLOOR",
        "^S_FLOOR",
        "^F_FLOOR",
        "^M_FLOOR",
        "^C_FLOOR",
        "^W_FLOOR",
        "^S_GFLOOR",
        "^F_GFLOOR",
        "^M_GFLOOR",
        "^C_GFLOOR",
        "^W_GFLOOR",

        "^C_ROOF",
        "^C_ROOF_C",
        "^C_ROOF_IC",
        "^C_ROOF_M",
        "^C_ROOF",

        "^M_ROOF",
        "^M_ROOF_C",
        "^M_ROOF_IC",
        "^M_ROOF_M",
        "^M_ROOF",

        "^W_ROOF",
        "^W_ROOF_C",
        "^W_ROOF_IC",
        "^W_ROOF_M",
        "^W_ROOF",

        "^F_ROOF0",
        "^F_ROOF1",
        "^F_ROOF2",
        "^F_ROOF3",
        "^F_ROOF4",
        "^F_ROOF5",
        "^F_ROOF6",
        "^F_ROOF7",
        "^F_ROOF8",
        "^F_ROOF_C",
        "^F_ROOF_E_CAP",
        "^F_ROOF_E_Q",
        "^F_ROOF_IC",
        "^F_ROOF_M",
        "^F_ROOF_M_CAP",
        "^F_ROOF_M_Q",

        "^T_ROOF0",
        "^T_ROOF1",
        "^T_ROOF2",
        "^T_ROOF3",
        "^T_ROOF4",
        "^T_ROOF5",
        "^T_ROOF6",
        "^T_ROOF7",
        "^T_ROOF8",
        "^T_ROOF_C",
        "^T_ROOF_E_CAP",
        "^T_ROOF_E_Q",
        "^T_ROOF_IC",
        "^T_ROOF_M",
        "^T_ROOF_M_CAP",
        "^T_ROOF_M_Q",

        "^S_ROOF0",
        "^S_ROOF1",
        "^S_ROOF2",
        "^S_ROOF3",
        "^S_ROOF4",
        "^S_ROOF5",
        "^S_ROOF6",
        "^S_ROOF7",
        "^S_ROOF8",
        "^S_ROOF_C",
        "^S_ROOF_E_CAP",
        "^S_ROOF_E_Q",
        "^S_ROOF_IC",
        "^S_ROOF_M",
        "^S_ROOF_M_CAP",
        "^S_ROOF_M_Q"
    ],

    "^T_FLOOR_Q": [
        "^S_FLOOR_Q",
        "^F_FLOOR_Q",
        "^M_FLOOR_Q",
        "^C_FLOOR_Q",
        "^W_FLOOR_Q"
    ],

    "^T_WALL_H": [
        "^S_WALL_H",
        "^F_WALL_H",
        "^M_WALL_H",
        "^C_WALL_H",
        "^W_WALL_H",
        "^T_ARCH_H",
        "^S_ARCH_H",
        "^F_ARCH_H",
        "^M_ARCH_H",
        "^C_ARCH_H",
        "^W_ARCH_H"
    ],

    "^T_WALL_Q": [
        "^T_WALL_Q1"
        "^S_WALL_Q",
        "^S_WALL_Q1"
        "^F_WALL_Q",
        "^F_WALL_Q1",
        "^M_WALL_Q",
        "^M_WALL_Q1",
        "^C_WALL_Q",
        "^C_WALL_Q1",
        "^W_WALL_Q",
        "^W_WALL_Q1"
    ],

    "^T_TRIFLOOR": [
        "^S_TRIFLOOR",
        "^F_TRIFLOOR",
        "^M_TRIFLOOR",
        "^C_TRIFLOOR",
        "^W_TRIFLOOR"
    ],

    "^T_TRIFLOOR_Q": [
        "^S_TRIFLOOR_Q",
        "^F_TRIFLOOR_Q",
        "^M_TRIFLOOR_Q",
        "^C_TRIFLOOR_Q",
        "^W_TRIFLOOR_Q"
    ],

    "^T_RAMP": [
        "^S_RAMP",
        "^F_RAMP",
        "^M_RAMP",
        "^C_RAMP",
        "^W_RAMP"
    ],

    "^T_RAMP_H": [
        "^S_RAMP_H",
        "^F_RAMP_H",
        "^M_RAMP_H",
        "^C_RAMP_H",
        "^W_RAMP_H"
    ]
}

with open(EXISTING_CSV_FILE, encoding="utf-16") as csv_file:
# with open(EXISTING_CSV_FILE) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for idx, row in enumerate(csv_reader):
        if idx == 0:
            continue
        id = row[0]
        existing_rows[id] = row


def get_template_row(key_check):
    for key, value in template_map.items():
        if key_check in value:
            return key
    return None

for key, value in existing_rows.items():
    template_row = get_template_row(key)
    if template_row:
        value[5] = existing_rows[template_row][5]
        value[6] = existing_rows[template_row][6]

build_data = ""
build_data += "---,ObjectModel,Category,Icon,SubCategory,SocketClassIDs,PlugClassIDs,NiceName\n"
for key in sorted(existing_rows.keys()):
    value = existing_rows[key]
    build_data += "{},\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"\n".format(
        value[0], value[1], value[2], value[3], value[4], value[5].replace("\"", "\"\""), value[6].replace("\"", "\"\""), value[7]
    )

with open(EXISTING_CSV_FILE, mode='w', newline='', encoding='utf-8') as csv_file:
    csv_file.write(build_data)
