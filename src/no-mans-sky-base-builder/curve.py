import bpy
from . import utils


def duplicate_along_curve(
        part_builder,
        preset_builder,
        dup_object,
        curve,
        gap_distance=0.1):
    """Given an object ID and a curve, duplicate uniformly along curve.

    Args:
        part_builder (object): The PartBuilder object.
        preset_builder (object): The PresetBuilder object.
        dup_object (bpy.object): The object to duplicate.
        curve (bpy.curve): The blender curve object.
        gap_distance (float): The percentage of the curve distance to
            distribute the item , This will likely be tweaked around by the
            user to get desired result.
    """


    percentage_count = 0.0
    while percentage_count <= 1.0:
        # Build Item.
        if "ObjectID" in dup_object:
            object_id = dup_object["ObjectID"]
            userdata = dup_object["UserData"]
            # Build Item.
            new_item = part_builder.build_item(object_id, userdata=userdata)
        if "PresetID" in dup_object:
            preset_id = dup_object["PresetID"]
            # Build Item.
            new_item = preset_builder.build_preset(preset_id)

        # Create constraint properties.
        utils.select(new_item)
        bpy.ops.object.constraint_add(type='FOLLOW_PATH')
        bpy.context.object.constraints["Follow Path"].target = bpy.data.objects[curve.name]
        bpy.context.object.constraints["Follow Path"].use_fixed_location = True
        bpy.context.object.constraints["Follow Path"].use_curve_follow = True
        bpy.context.object.constraints["Follow Path"].use_fixed_location = True
        bpy.context.object.constraints["Follow Path"].offset_factor = percentage_count
        percentage_count += gap_distance


        