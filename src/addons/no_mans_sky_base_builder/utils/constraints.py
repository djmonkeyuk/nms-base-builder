"""Convenient methods for performing rigging-like constraints."""
import bpy


def aim_constraint(bpy_object, target):
    """Constrain the rotation using a TRACK_TO constraint.

    Args:
        bpy_object (bpy_types.Object): The Blender object to constraint.
        target (bpy_types.Object): The Blender object to use as a target.
    """
    track = bpy_object.constraints.new(type='TRACK_TO')
    track.target = target
    track.track_axis = 'TRACK_Z'
    track.up_axis = 'UP_Y'


def point_constraint(bpy_object, target):
    """Constrain the position using drivers.
    
    Args:
        bpy_object (bpy_types.Object): The Blender object to constraint.
        target (bpy_types.Object): The Blender object to use as a target.
    """
    driver_x = bpy_object.driver_add("location", 0).driver
    driver_y = bpy_object.driver_add("location", 1).driver
    driver_z = bpy_object.driver_add("location", 2).driver

    x_var = driver_x.variables.new()
    x_var.name = "location_X"
    x_var.targets[0].id = target
    x_var.targets[0].data_path = "location.x"

    y_var = driver_y.variables.new()
    y_var.name = "location_y"
    y_var.targets[0].id = target
    y_var.targets[0].data_path = "location.y"

    z_var = driver_z.variables.new()
    z_var.name = "location_z"
    z_var.targets[0].id = target
    z_var.targets[0].data_path = "location.z"

    driver_x.expression = x_var.name
    driver_y.expression = y_var.name
    driver_z.expression = z_var.name


def stretch_constraint(bpy_object, source, target):
    """Constrain the scale z channel using drivers.

    There is a LOC_DIFF driver that gives you the distance between to objects.
    
    Args:
        bpy_object (bpy_types.Object): The Blender object to constraint.
        source (bpy_types.Object): The Blender object to use as a target.
        target (bpy_types.Object): The Blender object to use as a target.
    """
    driver_z = bpy_object.driver_add("scale", 2).driver

    z_var = driver_z.variables.new()
    z_var.type = "LOC_DIFF"
    z_var.name = "scale_z"
    z_var.targets[0].id = source
    z_var.targets[0].data_path = "location"
    z_var.targets[1].id = target
    z_var.targets[1].data_path = "location"
    driver_z.expression = z_var.name