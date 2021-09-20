"""Convenient curve related methods."""
import bpy


def duplicate_along_curve(builder, bpy_object, curve, gap_distance=0.1):
    """Given an object ID and a curve, duplicate uniformly along curve.

    Args:
        builder (object): The NMS Builder object.
        bpy_object (bpy_types.Object): The Blender object to duplicate.
        curve (bpy_types.Curve): The Blender curve object.
        gap_distance (float): The percentage of the curve distance to
            distribute the item , This will likely be tweaked around by the
            user to get desired result.
    """
    percentage_count = 0.0
    while percentage_count <= 1.0:
        # Build Item.
        if "ObjectID" in bpy_object:
            object_id = bpy_object["ObjectID"]
            user_data = bpy_object["UserData"]
            # Build Item.
            new_item = builder.add_part(object_id, user_data=user_data)
            bpy_object = new_item.object
        # Build Preset.
        if "PresetID" in bpy_object:
            preset_id = bpy_object["PresetID"]
            # Build Item.
            new_item = builder.add_preset(preset_id)
            bpy_object = new_item.control

        # Create constraint properties.
        constraint = bpy_object.constraints.new(type='FOLLOW_PATH')
        constraint.target = bpy.data.objects[curve.name]
        constraint.use_fixed_location = True
        constraint.use_curve_follow = True
        constraint.use_fixed_location = True
        constraint.offset_factor = percentage_count
        percentage_count += gap_distance
