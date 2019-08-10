import os

import bpy

from . import utils

# Get Colour Information.
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
COLOURS_JSON = os.path.join(FILE_PATH, "resources", "colours.json")
COLOUR_REFERENCE = utils.load_dictionary(COLOURS_JSON)


def assign_material(item, colour_index=0, material=None, preset=False):
    """Given a blender object. assign a material and UserData index.
    
    Args:
        item (bpy.ob): A Blender object.
        colour_index (int): The colour index determined by No Man's Sky.
        material (str): The material type.
        preset (bool): Toggle to use golden preset material.
    """
    # Some Defaults
    alpha_value = 1.0
    # Material+Colour
    if material:
        material_index = 0
        if material == {"RUST"}:
            material_index = 16777216
        elif material == {"STONE"}:
            material_index = 33554432
        elif material == {"WOOD"}:
            material_index = 50331648
        colour_index = material_index + colour_index

    # Apply Custom Variable.
    item["UserData"] = colour_index
    # Create Material
    colour_name = "{0}_material".format(colour_index)
    if preset:
        colour_name = "preset_material"
    colour_material = None

    # Retrieve material if it already exists.
    for material in bpy.data.materials:
        if colour_name == material.name:
            colour_material = material

    # Ensure we have a transparent shader.
    if not colour_material:
        # Create material
        colour_material = bpy.data.materials.new(name=colour_name)
        colour_material.diffuse_color[3] = alpha_value
        # Apply colour.
        if preset:
            colour_material.diffuse_color[0] = 0.8
            colour_material.diffuse_color[1] = 0.300186
            colour_material.diffuse_color[2] = 0.0178301
            colour_material.diffuse_color[3] = alpha_value
        else:
            colour_data = COLOUR_REFERENCE.get(str(colour_index), {})
            colour_tuple = colour_data.get("colour", [0.8, 0.8,0.8, alpha_value])
            if len(colour_tuple) < 4:
                colour_tuple.append(alpha_value)
            colour_material.diffuse_color = (
                colour_tuple[0],
                colour_tuple[1],
                colour_tuple[2],
                colour_tuple[3],
            )
    
    
    # Don't bother if we can't even apply mateiral to object.
    if not hasattr(item.data, "materials"):
        return

    # Assign Material
    if not item.data.materials:
        # Add the material to the object
        item.data.materials.append(colour_material) 
    else:
        # If a material already exists, swap it.
        item.data.materials[0] = colour_material

    return colour_material