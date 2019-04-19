"""Blender utility wrappers.

Author: Charlie Banks <@charliebanks>

"""
import bpy


def duplicate_hierarchy(item):
    # Deselect everything.
    bpy.ops.object.select_all(action='DESELECT') 

    # Select item.
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
        for c in each.children:
            c.select = False
            c.hide_select = c["hide_select_state"]
            c.hide = c["hide_state"]

    return new_item