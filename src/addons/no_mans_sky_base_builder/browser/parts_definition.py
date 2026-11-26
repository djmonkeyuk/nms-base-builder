import csv
import os
from pprint import pprint

RESOURCES_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "resources")
)
PART_DEFINITION = os.path.join(RESOURCES_DIR, "DT_PartDefinition.csv")

headings = [
    "---",
    "ObjectModel",
    "Category",
    "Icon",
    "SubCategory",
    "SocketClassIDs",
    "PlugClassIDs",
    "NiceName",
    "bShowInDrawer",
    "VariantOf",
    "bIncludeMessage",
    "bFossilPart",
]


def read_rows():
    existing_rows = {}
    with open(PART_DEFINITION, "r", encoding="utf-16") as csv_file:
        csv_reader = csv.reader((x.replace("\0", "") for x in csv_file), delimiter=",")
        for idx, row in enumerate(csv_reader):
            if (not row) or (idx == 0):
                continue
            id = row[0]
            existing_rows[id] = row
    return existing_rows


ROWS = read_rows()


def get_top_categories():
    categories = set()
    for item in ROWS.values():
        # Pipe connector parts (_PIPE3CORNER, _PIPEL, etc.) have no
        # Category/SubCategory in the CSV, which would otherwise surface
        # as an untitled category full of pipe parts in the browser.
        if not item[2]:
            continue
        categories.add(item[2])
    return sorted(categories)


def get_sub_categories(category):
    sub_categories = set()
    for item in ROWS.values():
        if item[2] != category:
            continue
        sub_categories.add(item[4])
    return sorted(sub_categories)


def get_parts_from_categories(category, sub_category):
    parts = []
    for item in ROWS.values():
        if item[2] == category and item[4] == sub_category:
            parts.append(
                {
                    "id": item[0][1:],
                    "showInDrawer": item[8],
                    "variantOf": item[9],
                    "nice_name": item[7],
                }
            )
    return sorted(parts, key=lambda part: part["id"])


def get_part_definition():
    data = {}
    categories = get_top_categories()
    for category in categories:
        data[category] = {}
        sub_categories = get_sub_categories(category)
        for sub_category in sub_categories:
            data[category][sub_category] = []
            parts = get_parts_from_categories(category, sub_category)
            for part in parts:
                data[category][sub_category].append(part)

    return data
