"""Convenient methods to perform common blender related tasks."""
import math

import addon_utils
import bpy


def load_plugin(plugin_name):
    """Load a blender plugin."""
    is_enabled, _ = addon_utils.check(plugin_name)
    if not is_enabled:
        addon_utils.enable(plugin_name)

def add_to_scene(item, collection_name="Collection"):
    """Add an item to the main blender collection.

    A Collection is a concept introduced in Blender 2.8. Which can be seen
    as a group/scene of items.

    By default we should add all new items to the default "Collection".

    Args:
        item (bpy_types.Object): The blender object.
        collection_name(str): The name of the collection to place the item in.
    """
    # Validate collection existence.
    if collection_name not in bpy.data.collections:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    # Add the item to the collection.
    object_set = bpy.data.collections[collection_name].objects
    if item.name not in object_set:
        object_set.link(item)


def get_item_by_name(item_name):
    """Get a Blender object by specifying the name of the object.
    
    Args:
        item_name (str): The name of the item.
        
    Returns:
        bpy_types.Object: The Blender object.    
    """
    return bpy.data.objects[item_name]

def item_exists_by_name(item_name):
    """Check for a Blender object by specifying the name of the object.
    
    Args:
        item_name (str): The name of the item.
        
    Returns:
        bool: True iff object exists.    
    """
    return item_name in bpy.data.objects

def remove_object(name):
    """Remove an item from the scene by specifying it's name.
    
    Args:
        name (str): The name of the object to remove.
    """
    objs = bpy.data.objects
    if name in objs:
        objs.remove(objs[name], do_unlink=True)


# Force refresh of scene so the matrix values are correct.
def scene_refresh():
    """Force the dependency graph to update.

    This is sometimes required when adding and removing constraints on 
    certain objects.
    """
    layer = bpy.context.view_layer
    layer.update()


def set_active_item(item):
    """Set the item to be the active item.

    This is similar to the selected state.

    Args:
        item (bpy_types.Object): The item to set as active.
    """
    bpy.context.view_layer.objects.active = item


def select(selection, add=False):
    """Select an item.

    The add flag determines if the item is appended to the current selection
    or if we should only select that particular item.

    Args:
        selection (bpy_types.Object, list): The item to be selected.
            This can be a singular object or a list of objects.
        add (bool): Appends the selection if `True` else select by itself.
    """
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


def get_current_selection():
    """Get the current selected item.
    
    Returns:
        bpy_types.Object: The selected item.
    """
    if bpy.context.selected_objects:
        return bpy.context.selected_objects[-1]


def get_distance_between(matrix1, matrix2):
    """Get the distance between two matrices.
    
    Args:
        matrix1: First matrix input.
        matrix2: Second matrix input.

    Returns:
        float: The distance between the two.
    """
    translate1 = matrix1.decompose()[0]
    translate2 = matrix2.decompose()[0]
    return math.sqrt(
        (translate2.x - translate1.x)**2 + (translate2.y - translate1.y)**2  + (translate2.z - translate1.z)**2
    )


def delete(bpy_object):
    """Remove the item and everything below it."""
    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')
    
    # Parent items to control.
    for part in bpy_object.children:
        part.hide_select = False
        part.select_set(True)
    
    bpy_object.select_set(True)
    bpy.ops.object.delete() 
