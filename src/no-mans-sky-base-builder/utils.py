import json
import math

import bpy
import mathutils


def load_dictionary(json_path):
    """Build dictionary from json path.
    
    Args:
        json_path(str): The path to the JSON file.
    
    """
    dictionary = {}
    with open(json_path, "r") as stream:
        dictionary = json.load(stream)
    return dictionary

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
        return bpy.context.selected_objects[0]

def get_active_item():
    return bpy.context.scene.objects.active

def set_active_item(item):
    bpy.context.scene.objects.active = item

def select(selection, add=False):
    # Deselect all.
    if not add:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.objects.active = None
    
    # Ensure List.
    if not isinstance(selection, list):
        selection = [selection]

    for item in selection:
        item.select = True

    # Make the last item the active one.
    bpy.context.scene.objects.active = selection[-1]

def reset_selection_state(item):
    """Restore selection and visibility state."""
    bpy.ops.object.select_all(action='DESELECT')
    item.select = True
    bpy.context.object.hide_select = False
    bpy.context.object.hide = False

def clear_parent(item):
    """Clear the parent relationship of the item."""
    bpy.ops.object.select_all(action='DESELECT')
    item.select = True
    bpy.context.scene.objects.active = item
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    
def parent(child, parent):
    """Convenient wrapper to parent things.
    
    Args:
        parent (bpy.ob): Object to place under.
        child (bpy.ob): The object to move.
    """
    bpy.ops.object.select_all(action='DESELECT')
    child.select = True
    parent.select = True
    bpy.context.scene.objects.active = parent
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
        preset_up_vec = mathutils.Vector(up)
        preset_at_vec = mathutils.Vector(at)
        
        # Calculate a normal using the up vector
        right_vector = preset_at_vec.cross(preset_up_vec)
        new_up_vec = right_vector.cross(preset_at_vec)
        # Flip the right vector.
        right_vector *= -1
        # Construct a world matrix for the item.
        mat = mathutils.Matrix(
            [
                [right_vector[0], new_up_vec[0] , preset_at_vec[0],  position[0]],
                [right_vector[1], new_up_vec[1] , preset_at_vec[1],  position[1]],
                [right_vector[2], new_up_vec[2] , preset_at_vec[2],  position[2]],
                [0.0,             0.0,            0.0,        1.0        ]
            ]
        )
        # Create a rotation matrix that turns the whole thing 90 degrees at the origin.
        # This is to compensate blender's Z up axis.
        mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
        mat = mat_rot * mat
        # Place the item in world space.
        item.matrix_world = mat


def duplicate_hierarchy(item):
    """Wrapper for duplicating a hiearchy in Blender.
    
    Args:
        item(bpy.obj): The blender object to duplicate.
    """
    # Deselect everything.
    bpy.ops.object.select_all(action='DESELECT')

    # Select item.
    item["hide_select_state"] = item.hide_select
    item["hide_state"] = item.hide
    item.hide_select = False
    item.hide = False
    item.select = True
    # Expose children and capture their states.
    for c in item.children:
        c["hide_select_state"] = c.hide_select
        c["hide_state"] = c.hide
        c.hide_select = False
        c.hide = False
        c.select = True

    # Duplicate hiearchy.
    bpy.ops.object.duplicate()
    new_item = bpy.context.selected_objects[0]

    # Restore child state.
    for each in [item, new_item]:
        each.hide_select = each["hide_select_state"]
        each.hide = each["hide_state"]
        for c in each.children:
            c.select = False
            c.hide_select = c["hide_select_state"]
            c.hide = c["hide_state"]

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
