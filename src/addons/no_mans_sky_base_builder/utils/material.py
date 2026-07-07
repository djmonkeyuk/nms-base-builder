"""Convenient material related methods."""

import csv
import os
import re

import bpy

from ..utils import python as python_utils
from ..utils import userdata

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


def get_nice_name_from_indicies(colour_index, material_index):
    with open(COLOURS_CSV, "r") as csv_file:
        csv_reader = csv.reader((x.replace("\0", "") for x in csv_file), delimiter=",")
        for idx, row in enumerate(csv_reader):
            if idx == 0:
                continue
            colour_id = row[3]
            material_id = row[4]
            if int(colour_index) == int(colour_id) and int(material_index) == int(
                material_id
            ):
                return f"{row[2]}: {row[5]}"
    return ""


BAKED_COLOURS = get_all_colours()


def get_colours_from_palette(palette):
    data = []
    # palette_index = palette.split("_")[0]
    palette_string = palette.split("_")[1]
    for row in BAKED_COLOURS:
        if palette_string == get_palette_from_row(row):
            data.append(row)
    return data


def validate_material(colour_name, colour_value):
    """Creates or returns a material based on its name.

    Args:
        colour_name (str): The name of the material.
        colour_value (list): RGBA values representing the colour.

    Returns:
        bpy.Material: The Blender material.
    """
    # Retrieve material if it already exists.
    colour_material = bpy.data.materials.get(colour_name, None)
    # Create material.
    if not colour_material:
        colour_material = bpy.data.materials.new(name=colour_name)
        colour_material.diffuse_color = colour_value
    return colour_material


def set_material(item, material):
    """Set the material on an item.

    Args:
        item (bpy.Object): The Blender object to assign the material to.
        material (bpy.Material): The material to assign.

    Returns:
        bpy.Material: The Blender material.
    """
    # Don't bother if we can't even apply material to object.
    if not hasattr(item.data, "materials"):
        return
    # Assign Material
    if not item.data.materials:
        # Add the material to the object
        item.data.materials.append(material)
    else:
        # If a material already exists, swap it.
        item.data.materials[0] = material
    return material


def assign_power_material(item):
    """Assign light blue material to object.

    Args:
        item (bpy.Object): The Blender object to assign the material to.
    """
    material = validate_material("powerline_material", [0.0, 0.5, 1.0, 0.5])
    set_material(item, material)


def assign_portal_material(item):
    """Assign teal material to object.

    Args:
        item (bpy.Object): The Blender object to assign the material to.
    """
    material = validate_material("portalline_material", [0.0, 1.0, 1.0, 0.5])
    set_material(item, material)


def assign_pipe_material(item):
    """Assign grey material to object.

    Args:
        item (bpy.Object): The Blender object to assign the material to.
    """
    material = validate_material("pipeline_material", [0.3, 0.3, 0.3, 0.9])
    set_material(item, material)


def assign_bytebeat_material(item):
    """Assign light purple material to object.

    Args:
        item (bpy.Object): The Blender object to assign the material to.
    """
    material = validate_material("bytebeat_material", [0.8, 0.0, 0.8, 0.5])
    set_material(item, material)


def assign_preset_material(item):
    """Assign gold material to object.

    Args:
        item (bpy.Object): The Blender object to assign the material to.
    """
    # Material name.
    material_name = "preset_material"
    # Add transparent tag to material name.
    item_name = item.get("ObjectID", "")
    if item_name in GHOSTED_ITEMS:
        material_name += "_transparent"

    material = validate_material(material_name, [0.8, 0.300186, 0.178301, 1.0])
    set_material(item, material)


def assign_default_material(item, index=0):
    """Given a blender object. Assign the default material,

    Args:
        item (bpy_types.Object): A Blender object.

    Returns:
        bpy_types.Material: The material that is applied.
    """
    # Apply Custom Variable.
    item["UserData"] = str(index)
    # Get colour values.
    colour_values = [0.8, 0.8, 0.8, 1.0]
    # Get or create the material.
    material = validate_material("default_material", colour_values)
    set_material(item, material)
    return material


def get_colour_from_palette_data(colour_index, material_index):
    """Get colour data from palette data.

    Args:
        index (int): The colour index.
    """
    return BAKED_INDEX_COLOURS.get(colour_index, [0.8, 0.8, 0.8, 1.0])


def darken_color(color, factor=0.6):
    """Return a darker version of an RGB color."""
    return [c * factor for c in color]


def restore_material(item, user_data_value):
    # Validate material+color index
    try:
        user_data_value = int(user_data_value)
    except ValueError:
        return
    col = userdata.get_colour(user_data_value)
    mat = userdata.get_material(user_data_value)
    assign_material(item, col, mat)


def assign_material(item, colour_index=0, material_index=0):
    """Given a blender object. assign a material and UserData index.

    Args:
        item (bpy_types.Object): A Blender object.
        colour_index (int): The colour index determined by No Man's Sky.
        material (str): The material type.

    Returns:
        bpy_types.Material: The material that is applied.
    """
    # Some Defaults
    alpha_value = 1.0

    # Apply Custom Variable.
    reference_value = int(item.get("UserData", 0))
    new_userdata_value = userdata.update_colour_material(
        reference_value, colour_index=colour_index, material_index=material_index
    )
    item["UserData"] = str(new_userdata_value)

    # Create Material
    colour_name = "{0}_material".format(new_userdata_value)
    # Add transparent tag to material name.
    item_name = item.get("ObjectID", "")
    if item_name in GHOSTED_ITEMS:
        colour_name += "_transparent"

    # Get colour values.
    primary = get_colour_from_palette_data(colour_index, material_index)
    if isinstance(primary, str):
        primary = eval(primary)
    if len(primary) < 4:
        primary.append(alpha_value)

    # Get or create the material.
    material = validate_material(colour_name, primary)

    # Add Metadata to object.
    nice_name = get_nice_name_from_indicies(colour_index, material_index)
    if nice_name and ":" in nice_name:
        item["readonly:Material"] = nice_name.split(":")[0].strip()
        item["readonly:Colour"] = nice_name.split(":")[1].strip()

    set_material(item, material)
    return material

