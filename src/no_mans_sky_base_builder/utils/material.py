"""Convenient material related methods."""
import os

import bpy
import no_mans_sky_base_builder.utils.python as python_utils

# Get Colour Information.
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
COLOURS_JSON = os.path.join(FILE_PATH, "..", "resources", "colours.json")
material_reference = python_utils.load_dictionary(COLOURS_JSON)

GHOSTED_JSON = os.path.join(FILE_PATH, "..", "resources", "ghosted.json")
ghosted_reference = python_utils.load_dictionary(GHOSTED_JSON)
GHOSTED_ITEMS = ghosted_reference["GHOSTED"]

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

    material = validate_material(
        material_name,
        [0.8, 0.300186, 0.178301, 1.0]
    )
    set_material(item, material)


def assign_material(item, colour_index=0, material=None):
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

    material_map = {
        "CONCRETE": 0,
        "RUST": 16777216,
        "STONE": 33554432,
        "WOOD": 50331648,
    }

    material_key = "CONCRETE"
    if material:
        material_key = list(material)[0]
        material_index = material_map[material_key]
        colour_index = material_index + colour_index

    # Apply Custom Variable.
    item["UserData"] = str(colour_index)

    # Create Material
    colour_name = "{0}_material".format(colour_index)
    # Add transparent tag to material name.
    item_name = item.get("ObjectID", "")
    if item_name in GHOSTED_ITEMS:
        colour_name += "_transparent"

    # Get colour values.
    colour_data = material_reference.get(str(colour_index), {})
    colour_values = colour_data.get("colour", [0.8, 0.8, 0.8, alpha_value])
    if len(colour_values) < 4:
        colour_values.append(alpha_value)

    # Get or create the material.
    material = validate_material(colour_name, colour_values)

    set_material(item, material)
    return material
