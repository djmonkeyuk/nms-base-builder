import os
from collections import defaultdict
from copy import copy, deepcopy

import bpy
import mathutils

from . import utils
from . import snap

# Create a snapper utility class.
SNAPPER = snap.Snapper()

def create_point(name):
    """Create a new electric wire point."""
    # Move point if there is a selection.
    selection = utils.get_current_selection()

    # path to the blend
    file_path = os.path.dirname(os.path.realpath(__file__))
    blend_path = os.path.join(file_path, "resources", "power_control.blend")
    # name of object to append or link
    obj_name = "power_control"

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name.startswith(obj_name)]

    for obj in data_to.objects:
        if obj is not None:
            bpy.context.scene.collection.objects.link(obj)
            point = obj
    
    point["base_builder_item"] = True
    point["SnapID"] = "POWER_CONTROL"
    point.name = name

    # Move the new point slightly away from current selection.
    if selection:
        point.location = selection.location
        point.location[0] += 1
        point.location[1] += 1
        
    return point

def create_power_controls(power_line, start=None, end=None):
    """Given the power line object, create 2 empties to control end points.

    Args:
        power_line (object): The power line object in scene.
        start (object): Pass a start control, if None a new one is made.
        end (object): Pass an end control, if None a new one is made.
    """
    if not start:
        start = create_point(name="_".join([power_line.name, "START"]))
        # Snap the start location to the power line.
        start.location = deepcopy(power_line.location)
    
    if not end:
        end = create_point(name="_".join([power_line.name, "END"]))
        # Snap the end location to the end of power line.
        world_pos = deepcopy(power_line.matrix_world)
        world_loc = world_pos.decompose()[0]
        at_vec = mathutils.Vector([world_pos[0][2], world_pos[1][2], world_pos[2][2]])
        end_location = world_loc + at_vec
        end.location = end_location

    point_constraint(power_line, start)
    stretch_constraint(power_line, start, end)
    aim_constraint(power_line, end)

    # Tag controls onto powerline
    power_line["start_control"] = start.name
    power_line["end_control"] = end.name
    # Tag powerlines onto controls.
    start["power_line"] = power_line.name
    end["power_line"] = power_line.name
    

def aim_constraint(power_line, end):
    """Constrain the position using a track to constraint."""
    track = power_line.constraints.new(type='TRACK_TO')
    track.target = end
    track.track_axis = 'TRACK_Z'
    track.up_axis = 'UP_Y'
    

def point_constraint(power_line, start):
    """Constrain the position using drivers."""
    driver_x = power_line.driver_add("location", 0).driver
    driver_y = power_line.driver_add("location", 1).driver
    driver_z = power_line.driver_add("location", 2).driver

    x_var = driver_x.variables.new()
    x_var.name                 = "location_X"
    x_var.targets[0].id        = start
    x_var.targets[0].data_path = "location.x"

    y_var = driver_y.variables.new()
    y_var.name                 = "location_y"
    y_var.targets[0].id        = start
    y_var.targets[0].data_path = "location.y"

    z_var = driver_z.variables.new()
    z_var.name                 = "location_z"
    z_var.targets[0].id        = start
    z_var.targets[0].data_path = "location.z"

    driver_x.expression = x_var.name
    driver_y.expression = y_var.name
    driver_z.expression = z_var.name


def stretch_constraint(power_line, start, end):
    """Constrain the position using drivers."""
    driver_z = power_line.driver_add("scale", 2).driver

    z_var = driver_z.variables.new()
    z_var.type = "LOC_DIFF"
    z_var.name                 = "scale_z"
    z_var.targets[0].id        = start
    z_var.targets[0].data_path = "location"

    z_var.targets[1].id        = end
    z_var.targets[1].data_path = "location"

    driver_z.expression = z_var.name


def divide(power_line):
    """Divide the power line in the middle and create an additional control."""
    # Middle control.
    middle = create_point("_".join([power_line.name, "MID"]))
    middle["base_builder_item"] = True

    # Snap the middle location to the middle of power line.
    world_pos = deepcopy(power_line.matrix_world)
    world_loc = world_pos.decompose()[0]
    at_vec = mathutils.Vector(
        [
            world_pos[0][2] / 2,
            world_pos[1][2] / 2,
            world_pos[2][2] / 2
        ]
    )
    middle_location = world_loc + at_vec
    middle.location = middle_location

    # Create new powerline.
    new_powerline = utils.duplicate_hierarchy(power_line)

    # Remove existing power line constraints
    for c in power_line.constraints:
        power_line.constraints.remove(c)

    # Create additional controls.
    prev_start_control_name = power_line["start_control"]
    prev_end_control_name = power_line["end_control"]

    create_power_controls(
        power_line,
        utils.get_item_by_name(prev_start_control_name),
        middle
    )
    create_power_controls(
        new_powerline,
        middle,
        utils.get_item_by_name(prev_end_control_name)
    )

    # Select the middle controller.
    utils.select(middle)

def split(power_line, line_type):
    """split the power line in the middle and create two additional control.
    
    This will create a gap in the wire.
    """
    # Middle A control.
    middle_a = create_point("_".join([power_line.name, "MID_A"]))
    middle_a["base_builder_item"] = True

    middle_b = create_point("_".join([power_line.name, "MID_B"]))
    middle_b["base_builder_item"] = True

    # Snap the middle location to the middle of power line.
    world_pos = deepcopy(power_line.matrix_world)
    world_loc = world_pos.decompose()[0]
    mid_a_pos = mathutils.Vector(
        [
            world_pos[0][2] * 0.4,
            world_pos[1][2] * 0.4,
            world_pos[2][2] * 0.4
        ]
    )
    middle_a_location = world_loc + mid_a_pos
    middle_a.location = middle_a_location

    mid_b_pos = mathutils.Vector(
        [
            world_pos[0][2] * 0.6,
            world_pos[1][2] * 0.6,
            world_pos[2][2] * 0.6
        ]
    )
    middle_b_location = world_loc + mid_b_pos
    middle_b.location = middle_b_location


    # Create new powerline.
    new_powerline = utils.duplicate_hierarchy(power_line)

    # Remove existing power line constraints
    for c in power_line.constraints:
        power_line.constraints.remove(c)

    # Create additional controls.
    prev_start_control_name = power_line["start_control"]
    prev_end_control_name = power_line["end_control"]

    create_power_controls(
        power_line,
        utils.get_item_by_name(prev_start_control_name),
        middle_a
    )
    create_power_controls(
        new_powerline,
        middle_b,
        utils.get_item_by_name(prev_end_control_name)
    )

    # Select the middle controller.
    utils.select([middle_a, middle_b])


def optimise_control_points():
    """Find all control points that share the same location and combine them."""
    # First build a dictionary of controls that match.
    power_control_objects = [obj for obj in bpy.data.objects if "base_builder_item" in obj]
    power_control_reference = defaultdict(list)
    for power_control in power_control_objects:
        # Create a key that will grouop the controls based on their location.
        # I am rounding the decimel point to 4 as the accuracy means items
        # in the same location have slightly different values.
        key = ",".join([str(round(loc, 3)) for loc in power_control.matrix_world.decompose()[0]])
        # Append the control to the key.
        power_control_reference[key].append(power_control)

    # Swap any duplicate controls with the first instance.
    for key, value in power_control_reference.items():
        first_control = value[0]
        other_controls = value[1:]
        for control in other_controls:
            power_line = utils.get_item_by_name(control["power_line"])
            prev_start_control = utils.get_item_by_name(power_line["start_control"])
            prev_end_control = utils.get_item_by_name(power_line["end_control"])
            if control == prev_start_control:
                create_power_controls(
                    power_line,
                    first_control,
                    prev_end_control
                )
            else:
                create_power_controls(
                    power_line,
                    prev_start_control,
                    first_control,
                )
            
            # Hide away control.
            control.hide_viewport = True

def generate_control_points(source, target):
    """Given two inputs, check if we can generate power connections points.
    
    Args:
        source (bpy.ob): The source input.
        target (bpy.ob): The target input.
    """
    # If not, find the closest point between the two targets and create
    # new power controls from them.
    source_key, target_key = SNAPPER.get_closest_snap_points(
        source,
        target,
        source_filter="POWER",
        target_filter="POWER"
    )

    if source["SnapID"] == "POWER_CONTROL":
        source_control = source
    else:
        # Get local value.
        source_local_value = SNAPPER.get_matrix_from_key(source, source_key)
        # Create a control if it's found.
        if not source_local_value:
            source_control = None
        else:
            source_local = mathutils.Matrix(source_local_value)
            source_snap_matrix = source.matrix_world @ source_local
            source_control = create_point(source.name + "_START")
            source_control.location = source_snap_matrix.decompose()[0]

    if target["SnapID"] == "POWER_CONTROL":
        target_control = target
    else:
        target_local_value = SNAPPER.get_matrix_from_key(target, target_key)
        if not target_local_value:
            target_control = None
        else:
            target_local = mathutils.Matrix(target_local_value)
            target_snap_matrix = target.matrix_world @ target_local
            target_control = create_point(target.name + "_END")
            target_control.location = target_snap_matrix.decompose()[0]


    return source_control, target_control