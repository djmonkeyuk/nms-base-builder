import json
import math

import bpy
import mathutils
import logging

LOG = logging.getLogger(__name__)

def load_dictionary(json_path):
    """Build dictionary from json path.
    
    Args:
        json_path(str): The path to the JSON file.
    
    """
    dictionary = {}
    with open(json_path, "r") as stream:
        dictionary = json.load(stream)
    return dictionary

def zero_scale(item):
    item.scale[0] = 1.0
    item.scale[1] = 1.0
    item.scale[2] = 1.0
    
def zero_transforms(item):
    item.location[0] = 0.0
    item.location[1] = 0.0
    item.location[2] = 0.0
    item.rotation_euler[0] = 0.0
    item.rotation_euler[1] = 0.0
    item.rotation_euler[2] = 0.0
    item.scale[0] = 1.0
    item.scale[1] = 1.0
    item.scale[2] = 1.0

def get_current_selection():
    if bpy.context.selected_objects:
        return bpy.context.selected_objects[-1]

def get_active_item():
    return bpy.context.view_layer.objects.active

def set_active_item(item):
    bpy.context.view_layer.objects.active = item

def select(selection, add=False):
    # Deselect all.
    if not add:
        bpy.ops.object.select_all(action='DESELECT')
        set_active_item(None)
    
    # Ensure List.
    if not isinstance(selection, list):
        selection = [selection]

    for item in selection:
        item.select_set(True)

    # Make the last item the active one.
    selection[-1].select_set(True)
    set_active_item(selection[-1])

def clear_parent(item):
    """Clear the parent relationship of the item."""
    # bpy.ops.object.select_all(action='DESELECT')
    # item.select_set(True)
    # bpy.context.view_layer.objects.active = item
    # bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    item.parent = None
    
def parent(child, parent):
    """Convenient wrapper to parent things.
    
    Args:
        parent (bpy.ob): Object to place under.
        child (bpy.ob): The object to move.
    """
    bpy.ops.object.select_all(action='DESELECT')
    child.select_set(True)
    parent.select_set(True)
    bpy.context.view_layer.objects.active = parent
    bpy.ops.object.parent_set()
    return child


def move_to(item, position=None, up=None, at=None):
    """Move a blender item to position using No Man's Sky details.

    Args:
        item (bpy.ob): The item to move.
        position (tuple): The position (x, y, z) to move to.
        up (tuple): The up direction vector.
        at (tuple): The at direction vector.
    
    """
    # Move
    if position:
        item.location = position
    
    # Rotation
    if up and at:
        # Create vectors that will construct the matrix.
        preset_up_vec = mathutils.Vector(up)
        preset_at_vec = mathutils.Vector(at)
        right_vector = preset_at_vec.cross(preset_up_vec)
        
        # Make sure the right vector magnitude is an average of the other two.
        right_vector.normalize()
        right_vector *= -1
        
        # If we're not dealing with power lines... figure out an average scale.
        line_parts = ["U_POWERLINE", "U_PIPELINE", "U_PORTALLINE"]
        if "ObjectID" in item:
            if item["ObjectID"] not in line_parts:
                average = ((preset_up_vec.length + preset_at_vec.length) / 2)
                right_vector.length = right_vector.length * average
            
            
        # Construct a world matrix for the item.
        mat = mathutils.Matrix(
            [
                [right_vector[0], preset_up_vec[0] , preset_at_vec[0],  position[0]],
                [right_vector[1], preset_up_vec[1] , preset_at_vec[1],  position[1]],
                [right_vector[2], preset_up_vec[2] , preset_at_vec[2],  position[2]],
                [0.0,             0.0,            0.0,        1.0        ]
            ]
        )
        # Create a rotation matrix that turns the whole thing 90 degrees at the origin.
        # This is to compensate blender's Z up axis.
        mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
        mat = mat_rot @ mat
        # Place the item in world space.
        item.matrix_world = mat

def get_item_by_name(item_name):
    return bpy.data.objects[item_name]

def duplicate_hierarchy(item):
    """Wrapper for duplicating a hiearchy in Blender.
    
    Args:
        item(bpy.obj): The blender object to duplicate.
    """
    # Deselect everything.
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select item.
    item["hide_select_state"] = item.hide_select
    item["hide_state"] = item.hide_viewport
    item.hide_select = False
    item.hide_viewport = False
    select(item)

    # Expose children and capture their states.
    for c in item.children:
        c["hide_select_state"] = c.hide_select
        c["hide_state"] = c.hide_viewport
        c.hide_select = False
        c.hide_viewport = False
        select(c, add=True)
    
    # Duplicate hiearchy.
    bpy.ops.object.duplicate()

    # Get Old and new item.
    new_item = get_current_selection()

    # Remove any constraints from the duplication.
    for c in new_item.constraints:
        new_item.constraints.remove(c)

    # Remove any drivers from the duplication.
    anim_data = new_item.animation_data
    if anim_data:
        drivers_data = anim_data.drivers
        for dr in drivers_data:  
            new_item.driver_remove(dr.data_path, -1)

    # Restore child state.
    for each in [item, new_item]:
        each.hide_select = each["hide_select_state"]
        each.hide_viewport = each["hide_state"]
        for c in each.children:
            c.select_set(False)
            c.hide_select = c["hide_select_state"]
            c.hide_viewport = c["hide_state"]

    # Select the new item.
    select(new_item)
    return new_item


def get_direction_vector(matrix, direction_matrix=None):
    """Get the vectors that No Man's Sky cares about."""
    if direction_matrix == "up":
        return [matrix[0][1], matrix[1][1], matrix[2][1]]
    elif direction_matrix == "at":
        return [matrix[0][2], matrix[1][2], matrix[2][2]]
    return [0, 0, 0]


def get_adjacent_dict_key(data, current, step="next"):
    """Get the next key in the dictionary
    
    Args:
        data (dict): The data to inspect.
        current`(str): The current key.
        ste (str): next/prev: The direction in which to look for the next
            key.

    Returns:
        str: The next or previous key.
    ."""
    # Sort the keys by the order sub-key.
    keys = data
    current_index = 0
    if current in keys:
        current_index = keys.index(current)
    if step == "next":
        next_index = current_index + 1
    elif step == "prev":
        next_index = current_index - 1

    if next_index > len(keys) - 1:
        next_index = 0

    if next_index < 0:
        next_index = len(keys) - 1

    return keys[next_index]
