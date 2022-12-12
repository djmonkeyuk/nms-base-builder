import csv
import json
import os
import shutil
import sys
from copy import deepcopy
from pprint import pprint

# ensure export folder exists.
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "part_generator", "OBJ_export", "Variants")
if not os.path.exists(OUTPUT_FOLDER):
    os.mkdir(OUTPUT_FOLDER)


root_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
sys.path.append(root_dir)

from automation_utils import get_all_existing_parts

all_existing_part_paths = get_all_existing_parts()

EXISTING_CSV_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "DT_PartDefinition.csv")

with open(EXISTING_CSV_FILE) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for idx, row in enumerate(csv_reader):
        if idx == 0:
            continue
        if row[9] not in ["None", ""]:
            variant_of = row[9]
            source_path = all_existing_part_paths[variant_of.replace("^", "")]
            output_path = os.path.join(OUTPUT_FOLDER, row[0].replace("^", "")+".obj")
            shutil.copy(source_path, output_path)
