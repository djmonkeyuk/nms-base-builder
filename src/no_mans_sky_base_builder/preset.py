import json
import math
import os
from copy import copy

import bpy
import mathutils
import no_mans_sky_base_builder.utils.material as material
import no_mans_sky_base_builder.part as part
import no_mans_sky_base_builder.utils.blend_utils as blend_utils

class Preset(object):

    USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
    PRESET_PATH = os.path.join(USER_PATH, "presets")

    def __init__(
            self,
            preset_id=None,
            bpy_object=None,
            builder_object=None,
            create_control=True,
            apply_shader=True,
            build_rigs=False):
        """Part __init__
        
        Args:
            preset_id (str): The preset ID we wish to create.
            bpy_object (bpy.data.object): An existing part we can reconstruct
                the class from.
            builder_object (Builder): The "parent" class for managing the NMS
                scene.
        """
        # Turn off relationship lines.
        bpy.context.space_data.overlay.show_relationship_lines = False

        # Assign private variables.
        self.__preset_id = preset_id
        self.__builder_object = builder_object
        self.__create_control = create_control
        self.__apply_shader = apply_shader
        self.build_rigs = build_rigs
       
        # Decide whether or not to retrieve from the scene
        # or create a new one.
        if bpy_object:
            self.__control = bpy_object
            preset_id = bpy_object["PresetID"]
        else:
            # Create new object.
            self.__control = self.retrieve_preset_from_id(preset_id)

            if create_control:
                # self.__control.name = preset_id
                self.parent = None
                self.reset_transforms()

                # Place the blender item in the builder cache.
                builder_object.add_to_preset_cache(preset_id, self.__control)

        # Set some IDs
        self.preset_id = preset_id

    # Properties ---
    @property
    def control(self):
        return self.__control

    @property
    def data_path(self):
        """Get the JSON data file for the preset."""
        json_file = self.preset_id + ".json"
        return os.path.join(self.PRESET_PATH, json_file)

    @staticmethod
    def get_presets():
        """Get the list of presets."""
        presets = os.listdir(Preset.PRESET_PATH)
        return [os.path.splitext(preset)[0] for preset in presets if preset.endswith(".json")]

    @property
    def builder(self):
        return self.__builder_object

    @property
    def matrix_world(self):
        return self.__control.matrix_world

    @matrix_world.setter
    def matrix_world(self, value):
        self.__control.matrix_world = value

    @property
    def preset_id(self):
        if hasattr(self, "__control"):
            return self.__control["PresetID"]
        return self.__preset_id

    @preset_id.setter
    def preset_id(self, value):
        valid_value = value.replace("^", "")
        self.__preset_id = valid_value
        if hasattr(self, "__control"):
            self.__control["PresetID"] = valid_value

    @property
    def preset_id_format(self):
        return "^{0}".format(self.preset_id)

    # Methods ---
    def select(self):
        blend_utils.select(self.control)

    def reset_transforms(self):
        """Reset transformations to default."""
        # Lock all translations and rotations.
        self.__control.lock_location = [False, False, False]
        self.__control.lock_rotation = [False, False, False]
        self.__control.lock_scale = [False, False, False]

        self.__control.location = [0.0, 0.0, 0.0]
        self.__control.rotation_euler = [0.0, 0.0, 0.0]
        self.__control.scale = [1.0, 1.0, 1.0]

    def duplicate(self):
        """Duplicate the part and return it."""
        # Copy the item
        new_item = self.__control.copy()
        blend_utils.add_to_scene(new_item)

        # Copy the children.
        new_children = [child.copy() for child in self.__control.children]

        # Parent each child under 
        for old_child, new_child in zip(self.__control.children, new_children):
            new_child.parent = new_item

        # Link to the scene
        for item in new_children:
            blend_utils.add_to_scene(item)

        # Remove the constraints.
        new_preset_object = Preset.deserialise_from_object(
            bpy_object=new_item,
            builder_object=self.builder
        )
        new_preset_object.remove_constraints()
        return new_preset_object

    def remove_constraints(self):
        # Remove any constraints from the duplication.
        for c in self.__control.constraints:
            self.__control.constraints.remove(c)

        # Remove any drivers from the duplication.
        anim_data = self.__control.animation_data
        if anim_data:
            drivers_data = anim_data.drivers
            for dr in drivers_data:  
                self.__control.driver_remove(dr.data_path, -1)

    def parent(self, bpy_object):
        """Parent this to another blender object.
        
        Whilst maintaining the offset.
        """
        self.__control.parent = bpy_object
        self.__control.matrix_parent_inverse = bpy_object.matrix_world.inverted()

    def retrieve_preset_from_id(self, preset_id):
        """Given an ID. Find the best way to create a new one.
        
        As loading OBJ can be resource and time intensive. We can figure ways
        of caching and duplicating existing items via th Builder class.

        Method Priority.
        - If the object already exists in the builder cache, we can just
            dupliciate it.
        - If not, generate it via json data.
        """
        # Duplicate existing.
        existing_object = self.builder.find_preset_by_id(preset_id)
        if existing_object:
            return existing_object.duplicate().control
        
        # Generate Preset from json data.
        parts = self.generate_preset(build_rigs=self.build_rigs)
        if self.__create_control:
            control = self.create_control(parts)
            return control

        # If no control was build, return all the parts instead.
        return parts

    def generate_preset(self, build_rigs=False):
        """Generate the preset."""
        # Load json file and construct.
        parts = []
        with open(self.data_path) as stream:
            data = json.load(stream)
            # Reconstruct objects.
            for part_data in data.get("Objects", []):
                object_id = part_data["ObjectID"].replace("^","")
                user_data = part_data["UserData"]
                use_class = self.builder.get_part_class(object_id)
                preset_part = use_class.deserialise_from_data(
                    part_data,
                    self.builder,
                    build_rigs=build_rigs
                )
                parts.append(preset_part)
        return parts

    def create_control(self, preset_items):
        """Create a control for the preset items.

        This will override the children to be locked and flagged to
        belong to a preset.
        
        Args:
            preset_items (list): The blender objects that make up the preset.
        """
        # Get highest radius value.
        highest_x = max([part.location[0] for part in preset_items])
        lowest_x = min([part.location[0] for part in preset_items])
        highest_y = max([part.location[1] for part in preset_items])
        lowest_y = min([part.location[1] for part in preset_items])
        highest_z = max([part.location[2] for part in preset_items])
        lowest_z = min([part.location[2] for part in preset_items])
        radius = max([abs(lowest_x), highest_x, abs(lowest_y), highest_y, abs(lowest_z), highest_z])

        # Create circle.
        curve_object = self.create_shape(
            lowest_x, highest_x, lowest_y, highest_y
        )
        curve_object.name = self.preset_id
        curve_object.show_name = True
        curve_object["PresetID"] = self.preset_id
        # Parent items to control.
        for part in preset_items:
            part.parent = curve_object
            part.hide_select = True
            part.belongs_to_preset = True
            material.assign_preset_material(part.object)
        
        return curve_object

    @staticmethod
    def create_shape(low_x, high_x, low_y, high_y):
        """Create a bounding-box shape control for the preset."""
        # Apply a buffer
        buffer = 4
        low_x -= buffer
        high_x += buffer
        low_y -= buffer
        high_y += buffer
        # Find middle points.
        x_mid = (high_x + low_x) * 0.5
        y_mid = (high_y + low_y) * 0.5
        # Build coordinate list.
        coords_list = [
            [x_mid,     low_y,  0],
            [high_x,    low_y,  0],
            [high_x,    y_mid,  0],
            [high_x,    high_y, 0],
            [x_mid,     high_y, 0],
            [low_x,     high_y, 0],
            [low_x,     y_mid,  0],
            [low_x,     low_y,  0],
            [x_mid,     low_y,  0],
            [high_x,    low_y,  0],
            [ high_x,    y_mid,  0]
        ]

        # make a new curve
        crv = bpy.data.curves.new('crv', 'CURVE')
        crv.dimensions = '3D'

        # make a new spline in that curve
        spline = crv.splines.new(type='NURBS')

        # a spline point for each point
        spline.points.add(len(coords_list)-1) # theres already one point by default

        # assign the point coordinates to the spline points
        for p, new_co in zip(spline.points, coords_list):
            p.co = (new_co + [1.0]) # (add nurbs weight)

        # make a new object with the curve
        obj = bpy.data.objects.new('object_name', crv)
        blend_utils.add_to_scene(obj)
        return obj

    # Serialisation ---
    def serialise(self):
        """Return NMS compatible dictionary.

        Returns:
            dict: Dictionary of part information.
        """
        # Get Matrix Data
        world_matrix = self.matrix_world
        # Bring the matrix from Blender Z-Up soace into standard Y-up space.
        z_compensate = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
        world_matrix_offset = z_compensate @ world_matrix
        # Retrieve Position, Up and At vectors.
        pos = world_matrix_offset.decompose()[0]
        up = [
            world_matrix_offset[0][1],
            world_matrix_offset[1][1],
            world_matrix_offset[2][1]
        ]
        at = [
            world_matrix_offset[0][2],
            world_matrix_offset[1][2],
            world_matrix_offset[2][2]
        ]

        return {
            "PresetID": self.preset_id_format,
            "Position": [pos[0], pos[1], pos[2]],
            "Up": [up[0], up[1], up[2]],
            "At": [at[0], at[1], at[2]]
        }

    @staticmethod
    def serialise_parts(self, builder_object):
        """Return NMS compatible dictionary.

        Args:
            get_presets (bool): This will generate data for presets. And 
                exclude parts generated from presets.
        Returns:
            dict: Dictionary of base information.
        """
        # Get all object part data.
        object_list = []

        for item in self.builder_object.get_all_parts():
            object_id = item["ObjectID"]
            use_class = self.builder_object.get_part_class(object_id)
            item_obj = use_class.deserialise_from_object(
                item,
                builder_object=self.builder_object
            )
            object_list.append(item_obj.serialise())

        # Create full dictionary.
        data = {"Objects": object_list}

    # Class Methods ---
    @classmethod
    def deserialise_from_object(cls, bpy_object, builder_object):
        """Reconstruct the class using an existing Blender object."""
        part = cls(bpy_object=bpy_object, builder_object=builder_object)
        return part

    @classmethod
    def deserialise_from_data(cls, data, builder_object):
        """Reconstruct the class using an a data.
        
        Data usually comes from NMS or the serialise method.
        """
        # Some old preset tests were using Object ID as a tag. So we can
        # use that as a fall back for those legacy builds.
        object_id = data.get("ObjectID", None)
        # Create object based on the ID.
        preset_id = data.get("PresetID", object_id).replace("^", "")
        part = cls(preset_id=preset_id, builder_object=builder_object)
        # Get location data.
        pos = data.get("Position", [0.0, 0.0, 0.0])
        up = data.get("Up", [0.0, 0.0, 0.0])
        at = data.get("At", [0.0, 0.0, 0.0])
        # Set part position.
        part.matrix_world = Preset.create_matrix_from_vectors(pos, up, at)
        return part

    # Static Methods ---
    @staticmethod
    def create_matrix_from_vectors(pos, up, at):
        """Create a world space matrix given by an Up and At vector.
        
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

        average = ((up_vector.length + at_vector.length) / 2)
        right_vector.length = right_vector.length * average
        
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


    def snap_to(self, target, *args, **kwargs):
        """Just move the preset to the target.

        Might need to offset as Preset origin space is 0, 0, 0 where as Parts
        are 90, 0, 0
        """
        use_matrix = target.matrix_world
        if hasattr(target, "object"):
            object_id = target.object.get("ObjectID", None)
            if object_id:
                mat_rot = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
                use_matrix = use_matrix @ mat_rot
        self.matrix_world = use_matrix