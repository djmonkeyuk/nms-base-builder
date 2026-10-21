"""Convenient material related methods."""

import csv
import os
import re

import bpy

from ..utils import python as python_utils

# Get Colour Information.
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
COLOURS_CSV = os.path.join(FILE_PATH, "..", "resources", "DT_Palettes.csv")

GHOSTED_JSON = os.path.join(FILE_PATH, "..", "resources", "ghosted.json")
ghosted_reference = python_utils.load_dictionary(GHOSTED_JSON)
GHOSTED_ITEMS = ghosted_reference["GHOSTED"]


def get_palette_from_row(row):
    return row[2]


def get_palette_index_from_row(row):
    return row[4]


def get_all_palettes():
    palettes = {}
    with open(COLOURS_CSV, "r") as csv_file:
        csv_reader = csv.reader((x.replace("\0", "") for x in csv_file), delimiter=",")
        for idx, row in enumerate(csv_reader):
            if idx == 0:
                continue
            palette_name = get_palette_from_row(row)
            palette_index = get_palette_index_from_row(row)
            if palette_name not in palettes:
                palettes[palette_name] = palette_index

    return palettes


BAKED_PALETTES = get_all_palettes()
BAKED_PALETTES_UI = [
    (f"{value}_{key}", key, key) for key, value in BAKED_PALETTES.items()
]


def get_palette_categories():
    # "Legacy - Rust" is the Rust variant of Legacy, a name without " - " is its own category
    # variant ids match BAKED_PALETTES_UI so the chosen value means the same thing as before
    categories = {}
    for key, value in BAKED_PALETTES.items():
        category, _, variant = key.partition(" - ")
        categories.setdefault(category, []).append(
            (f"{value}_{key}", variant or category, key)
        )
    for variants in categories.values():
        variants.sort(key=lambda item: int(item[0].split("_")[0]))
    return categories


# built once, Blender needs dynamic enum items to stay referenced
PALETTE_VARIANTS_UI = get_palette_categories()
PALETTE_CATEGORIES_UI = [(category, category, category) for category in PALETTE_VARIANTS_UI]

BAKED_INDEX_COLOURS = {}


def get_all_colours():
    rows = []
    with open(COLOURS_CSV, "r") as csv_file:
        csv_reader = csv.reader((x.replace("\0", "") for x in csv_file), delimiter=",")
        for idx, row in enumerate(csv_reader):
            if idx == 0:
                continue
            rows.append(row)

            colour_id = row[3]
            primary_colour = row[6]
            if isinstance(primary_colour, str):
                primary_colour = [
                    float(v) for v in re.findall(r"[RGB]=([0-9.]+)", primary_colour)
                ]
            BAKED_INDEX_COLOURS[int(colour_id)] = primary_colour
    return rows


NICE_NAMES = {}


def get_nice_name_from_indicies(colour_index, material_index):
    # built once from the baked rows, this runs for every coloured part on import
    if not NICE_NAMES:
        for row in BAKED_COLOURS:
            try:
                key = (int(row[3]), int(row[4]))
                nice_name = f"{row[2]}: {row[5]}"
            except (ValueError, IndexError):
                continue
            NICE_NAMES.setdefault(key, nice_name)
    return NICE_NAMES.get((int(colour_index), int(material_index)), "")


BAKED_COLOURS = get_all_colours()


def get_colours_from_palette(palette):
    data = []
    # palette_index = palette.split("_")[0]
    palette_string = palette.split("_")[1]
    for row in BAKED_COLOURS:
        if palette_string == get_palette_from_row(row):
            data.append(row)
    return data


def darken_color(color, factor=0.6):
    """Return a darker version of an RGB color."""
    return [c * factor for c in color]


def _provider():
    # imported here because material_provider reads the palette data from this module
    from .material_provider import get_material_provider

    return get_material_provider()


# the addon calls these, they forward to whichever provider is active


def validate_material(colour_name, colour_value):
    return _provider().validate_material(colour_name, colour_value)


def set_material(item, material):
    return _provider().set_material(item, material)


def assign_power_material(item):
    return _provider().assign_power_material(item)


def assign_portal_material(item):
    return _provider().assign_portal_material(item)


def assign_pipe_material(item):
    return _provider().assign_pipe_material(item)


def assign_bytebeat_material(item):
    return _provider().assign_bytebeat_material(item)


def assign_preset_material(item):
    return _provider().assign_preset_material(item)


def assign_default_material(item, index=0):
    return _provider().assign_default_material(item, index=index)


def get_colour_from_palette_data(colour_index, material_index):
    return _provider().get_colour_from_palette_data(colour_index, material_index)


def restore_material(item, user_data_value):
    return _provider().restore_material(item, user_data_value)


def assign_material(item, colour_index=0, material_index=0):
    return _provider().assign_material(item, colour_index, material_index)


# parts with the same ObjectID and UserData share one mesh
# override classes and curve followers are left alone, they manage their own meshes
# returns (parts relinked, meshes removed)
def optimise_materials():
    from ..builder import overrides

    shared_meshes = {}
    replaced_meshes = set()
    relinked = 0

    for obj in bpy.data.objects:
        if obj.type != "MESH" or "ObjectID" not in obj or "curve_parent" in obj:
            continue
        if overrides.get_override_class(obj["ObjectID"]) is not None:
            continue

        mesh = obj.data
        # a shape key or an open edit session would be lost by swapping the mesh
        if mesh.shape_keys or mesh.is_editmode:
            continue

        # the first part's mesh is reused, nothing is copied
        key = (obj["ObjectID"], str(obj.get("UserData", 0)))
        shared_mesh = shared_meshes.setdefault(key, mesh)
        if shared_mesh != mesh:
            obj.data = shared_mesh
            replaced_meshes.add(mesh)
            relinked += 1

    # one batch, a remove() per mesh re-syncs the whole file each time
    unused_meshes = [mesh for mesh in replaced_meshes if mesh.users == 0]
    if unused_meshes:
        bpy.data.batch_remove(unused_meshes)

    return relinked, len(unused_meshes)

