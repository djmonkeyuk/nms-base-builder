import math
import os
from copy import copy

import bpy
import mathutils
import no_mans_sky_base_builder.part
import no_mans_sky_base_builder.utils.blend_utils as blend_utils
import no_mans_sky_base_builder.utils.constraints as constraints
import no_mans_sky_base_builder.utils.material as material


class Line(no_mans_sky_base_builder.part.Part):
    def __init__(self, bpy_object=None, build_rigs=True, *args, **kwargs):
        super(Line, self).__init__(
            bpy_object=bpy_object,
            build_rigs=build_rigs,
            *args,
            **kwargs
        )

        # Only create if a bpy object was not specified.
        if not bpy_object:
            # if self.build_rigs:
                # self.build_rig()

            # Lock all translations and rotations.
            self.object.lock_location = [True, True, True]
            self.object.lock_rotation = [True, True, True]
            self.object.lock_scale = [True, True, True]

            material.assign_power_material(self.object)

    @property
    def start_control(self):
        return self.object["start_control"]

    @start_control.setter
    def start_control(self, value):
        self.object["start_control"] = value

    @property
    def end_control(self):
        return self.object["end_control"]

    @end_control.setter
    def end_control(self, value):
        self.object["end_control"] = value

    def build_rig(self, start=None, end=None):
        """Given the power line object, create 2 empties to control end points.

        Args:
            self.object (object): The power line object in scene.
            start (object): Pass a start control, if None a new one is made.
            end (object): Pass an end control, if None a new one is made.
        """

        # Start creating controls.
        world_pos = copy(self.object.matrix_world)
        world_loc = world_pos.decompose()[0]
        if not start:
            start = Line.create_point(
                self.builder,
                name="_".join([self.object.name, "START"])
            )
            # Snap the start location to the power line.
            start.location = world_loc

        if not end:
            end = Line.create_point(
                builder=self.builder,
                name="_".join([self.object.name, "END"])
            )
            # Snap the end location to the end of power line.
            at_vec = mathutils.Vector([world_pos[0][2], world_pos[1][2], world_pos[2][2]])
            end_location = world_loc + at_vec
            end.location = end_location

        # Remove old constraints.
        self.remove_constraints()

        constraints.point_constraint(self.object, start)
        constraints.stretch_constraint(self.object, start, end)
        constraints.aim_constraint(self.object, end)

        # Tag controls onto powerline
        self.start_control = start.name
        self.end_control = end.name
        # Tag powerlines onto controls.
        start["power_line"] = self.object.name
        end["power_line"] = self.object.name

    def split(self):
        # Middle control.
        middle_control_a = self.create_point(self.builder, "_".join([self.name, "MID_A"]))
        middle_control_b = self.create_point(self.builder, "_".join([self.name, "MID_B"]))
        # Snap the middle locations to the middle of power line.
        world_pos = copy(self.matrix_world)
        world_loc = world_pos.decompose()[0]
        mid_a_pos = mathutils.Vector(
            [
                world_pos[0][2] * 0.4,
                world_pos[1][2] * 0.4,
                world_pos[2][2] * 0.4
            ]
        )
        middle_a_location = world_loc + mid_a_pos
        middle_control_a.location = middle_a_location

        mid_b_pos = mathutils.Vector(
            [
                world_pos[0][2] * 0.6,
                world_pos[1][2] * 0.6,
                world_pos[2][2] * 0.6
            ]
        )
        middle_b_location = world_loc + mid_b_pos
        middle_control_b.location = middle_b_location
        # Create new powerline.
        new_powerline = self.builder.add_part(
            self.object_id,
            build_rigs=False
        )
        # Create additional controls.
        prev_start_control_name = self.object["start_control"]
        prev_end_control_name = self.object["end_control"]
        prev_start_control = blend_utils.get_item_by_name(prev_start_control_name)
        prev_end_control = blend_utils.get_item_by_name(prev_end_control_name)
        # Remove constraints of the original power line.
        self.remove_constraints()
        # Assign new controls to the power lines.
        self.build_rig(prev_start_control, middle_control_a)
        new_powerline.build_rig(middle_control_b, prev_end_control)
        # Select the middle controller.
        blend_utils.select([middle_control_a, middle_control_b])

    def divide(self):
        # Middle control.
        middle_control = self.create_point(self.builder, "_".join([self.name, "MID"]))
        # Snap the middle location to the middle of power line.
        world_pos = copy(self.matrix_world)
        world_loc = world_pos.decompose()[0]
        at_vec = mathutils.Vector(
            [
                world_pos[0][2] / 2,
                world_pos[1][2] / 2,
                world_pos[2][2] / 2
            ]
        )
        middle_location = world_loc + at_vec
        middle_control.location = middle_location
        # Create new powerline.
        new_powerline = self.builder.add_part(
            self.object_id,
            build_rigs=False
        )
        # Create additional controls.
        prev_start_control_name = self.object["start_control"]
        prev_end_control_name = self.object["end_control"]
        prev_start_control = blend_utils.get_item_by_name(prev_start_control_name)
        prev_end_control = blend_utils.get_item_by_name(prev_end_control_name)
        # Remove constraints of the original power line.
        self.remove_constraints()
        # Assign new controls to the power lines.
        self.build_rig(prev_start_control, middle_control)
        new_powerline.build_rig(middle_control, prev_end_control)
        # Select the middle controller.
        blend_utils.select(middle_control)

    # Class Methods ---
    @classmethod
    def deserialise_from_data(cls, data, builder_object, build_rigs=True):
        """Reconstruct the class using an a data.
        
        Data usually comes from NMS or the serialise method.
        """
        # Create object based on the ID.
        object_id = data["ObjectID"].replace("^", "")
        part = cls(
            object_id=object_id,
            builder_object=builder_object,
            build_rigs=build_rigs
        )
        # if not build_rigs:
        part.position_matrix(data, part)
        # else:
            # part.position_controls(data, part)

        # Apply metadata
        part.time_stamp = data.get("Timestamp", 1539024128)
        part.user_data = data.get("UserData", 0)

        return part
    
    # Static Methods ---
    @staticmethod
    def create_point(builder, name=None):
        """Create a new electric wire point."""
        default_name = "ARBITRARY_POINT"
        name = name or default_name
        # path to the blend
        file_path = os.path.dirname(os.path.realpath(__file__))
        blend_path = os.path.join(file_path, "..", "resources", "power_control.blend")
        # name of object to append or link
        obj_name = "power_control"

        existing_object = builder.find_object_by_id("POWER_CONTROL")
        if existing_object:
            point = existing_object.duplicate()
            point = point.object
            point.rotation_euler[0] = 0
            point.rotation_euler[1] = 0
            point.rotation_euler[2] = 0
            blend_utils.add_to_scene(point)
        else:
            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                data_to.objects = [
                    scene_name for scene_name in data_from.objects if scene_name.startswith(obj_name)
                ]

            for obj in data_to.objects:
                if obj is not None:
                    point = obj.copy()
                    blend_utils.add_to_scene(point)
        

        point["rig_item"] = True
        point["SnapID"] = "POWER_CONTROL"

        if name == default_name:
            name = "{}.{}".format(name, point.name.split(".")[-1])

        point.name = name
        point.data.name = name+"_SHAPE"
        builder.add_to_part_cache("POWER_CONTROL", point)
        
        return bpy.data.objects[point.name]

    @staticmethod
    def position_matrix(data, bpy_object):
        # Get location data.
        pos = data.get("Position", [0.0, 0.0, 0.0])
        up = data.get("Up", [0.0, 0.0, 0.0])
        at = data.get("At", [0.0, 0.0, 0.0])
        # Set part position.
        world_matrix = Line.create_matrix_from_vectors(pos, up, at)
        bpy_object.matrix_world = world_matrix

    @staticmethod
    def position_controls(data, bpy_object):
        # Get location data.
        pos = data.get("Position", [0.0, 0.0, 0.0])
        at = data.get("At", [0.0, 0.0, 0.0])
        # Switch Y and Z
        rot_pos = [pos[0], -pos[2], pos[1]]
        rot_at = [at[0], -at[2], at[1]]

        # Add to get end control point.
        end_loc = []
        for x, y in zip(rot_pos, rot_at):
            end_loc.append(x+y)

        # Set control positions.
        bpy.data.objects[bpy_object.start_control].location = rot_pos
        bpy.data.objects[bpy_object.end_control].location = end_loc

    @staticmethod
    def create_matrix_from_vectors(pos, up, at):
        """Create a world space matrix given by an Up and At vector.
        
        This is very similar to the inherited method. But we normalize the
        right vector slightly differently to maintain the line width.

        Args:
            pos (list): 3 element list/vector representing the x,y,z position.
            up (list): 3 element list/vector representing the up vector.
            at (list): 3 element list/vector representing the aim vector.
        """
        # Create vectors that will construct the matrix.
        up_vector = mathutils.Vector(up)
        at_vector = mathutils.Vector(at)
        right_vector = at_vector.cross(up_vector)
        
        # Make sure the right vector magnitude is an average of the other two.
        right_vector.normalize()
        right_vector *= -1
        
        # Construct a world matrix for the item.
        mat = mathutils.Matrix(
            [
                [right_vector[0], up_vector[0] , at_vector[0],  pos[0]],
                [right_vector[1], up_vector[1] , at_vector[1],  pos[1]],
                [right_vector[2], up_vector[2] , at_vector[2],  pos[2]],
                [0.0,             0.0,            0.0,        1.0        ]
            ]
        )
        # Create a rotation matrix that turns the whole thing 90 degrees at the origin.
        # This is to compensate blender's Z up axis.
        mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
        mat = mat_rot @ mat
        return mat
    
    @staticmethod
    def generate_control_points(source, target, builder):
        """Given two inputs, check if we can generate power connections points.
        
        Args:
            source (bpy.ob): The source input.
            target (bpy.ob): The target input.
        """
        source_key, target_key = source.get_closest_snap_points(
            target,
            source_filter="POWER",
            target_filter="POWER"
        )
        # If not, find the closest point between the two targets and create
        # new power controls from them.
        if source.snap_id == "POWER_CONTROL":
            source_control = source
        else:
            # Get local value.
            source_local_value = source.get_matrix_from_key(source_key)
            # Create a control if it's found.
            if not source_local_value:
                source_control = None
            else:
                source_local = mathutils.Matrix(source_local_value)
                source_snap_matrix = source.matrix_world @ source_local
                source_control = Line.create_point(builder, source.name + "_START")
                source_control.location = source_snap_matrix.decompose()[0]
                source_control["snapped_to"] = source.name

        if target.snap_id == "POWER_CONTROL":
            target_control = target
        else:
            target_local_value = target.get_matrix_from_key(target_key)
            if not target_local_value:
                target_control = None
            else:
                target_local = mathutils.Matrix(target_local_value)
                target_snap_matrix = target.matrix_world @ target_local
                target_control = Line.create_point(builder, target.name + "_END")
                target_control.location = target_snap_matrix.decompose()[0]
                target_control["snapped_to"] = target.name


        return source_control, target_control