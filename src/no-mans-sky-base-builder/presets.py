import json
import math
import os
from copy import deepcopy

import bpy
import mathutils

from . import material, utils


class PresetBuilder(object):

    USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
    PRESET_PATH = os.path.join(USER_PATH, "presets")

    def __init__(self, part_builder):
        """Initialise.

        Args:
            part_builder (PartBuilder): A reference to the part builder object.
        """
        self.part_builder = part_builder
        self.preset_cache = {}

        # Ensure custom paths are created.
        for data_path in [self.USER_PATH, self.PRESET_PATH]:
            if not os.path.exists(data_path):
                os.makedirs(data_path)

    def get_presets(self):
        """Get the list of presets."""
        return [os.path.splitext(preset)[0] for preset in os.listdir(self.PRESET_PATH) if preset.endswith(".json")]

    def get_nice_name(self, preset):
        return os.path.splitext(preset)[0]

    def get_full_path(self, preset):
        # Append file extention.
        if not preset.endswith(".json"):
            preset += ".json"
        return os.path.join(self.PRESET_PATH, preset)

    def delete_preset(self, preset_id):
        """Remove preset."""
        preset_path = self.get_full_path(preset_id)
        if os.path.isfile(preset_path):
            os.remove(preset_path)

    def get_all_preset_objects(self):
        """Wrapper to retrieve all preset objects in scene."""
        # Get all preset and top level parts.
        presets = [part for part in bpy.data.objects if "PresetID" in part]
        return presets

    def retrieve_preset(self, preset_name):
        """Retrieve the preset that represents the part.
        
        There are 3 outcomes.
        - If the preset already exists in the scene cache, we can just
            duplciate it.
        - If it doesn't exist in the cache, generate it via json data.
        """
        # Duplicate.
        if preset_name in self.preset_cache:
            cached_preset_name = self.preset_cache[preset_name]
            # If it's in the cache, but deleted by user, we can import again.
            if cached_preset_name in bpy.data.objects:
                cached_preset = bpy.data.objects[cached_preset_name]
                new_preset = utils.duplicate_hierarchy(cached_preset)
                utils.zero_transforms(new_preset)
                return new_preset

        # Generate preset and create a control for it.
        preset_items = self.generate_preset(preset_name)
        item = self.create_control(preset_name, preset_items)
        return item

    def generate_preset(self, preset_name):
        """Given the preset name, generate the items in scene.
        
        Args:
            preset_name (str): The name of the preset.
            edit_mode (bool): Toggle to build
        """
        # Get Preset JSON file.
        preset_json = self.get_full_path(preset_name)
        return self.part_builder.build_parts_from_json(preset_json)

    def build_presets_from_dict(self, data):
        """Given some data, build an array of presets found in the Presets key."""
        for preset_data in data["Presets"]:
            if "PresetID" in preset_data:
                object_id = preset_data["PresetID"]
            if "ObjectID" in preset_data:
                object_id = preset_data["ObjectID"]
            each_position = preset_data["Position"]
            each_up = preset_data["Up"]
            each_at = preset_data["At"]
            object_id = object_id.replace("^", "")
            self.build_preset(
                object_id,
                position=each_position,
                up = each_up,
                at= each_at
            )
    
    def build_preset(self, preset_id, position=None, up=None, at=None):
        """Given a preset ID. Create all the neccessary preset items.

        Args:
            preset_id (str): The preset ID.
            position (tuple): Position to move to.
            up (tuple): Up vector
            at (tuple):  At vector.
        """
        # Create the preset.
        preset_item = self.retrieve_preset(preset_id)
        # Position.
        utils.move_to(preset_item, position=position, up=up, at=at)
        # Lock Scale
        preset_item.lock_scale[0] = True
        preset_item.lock_scale[1] = True
        preset_item.lock_scale[2] = True
        return preset_item

    def create_control(self, preset_name, preset_items):
        """Create a control for the preset items.

        This will override the children to be locked and flagged to
        belong to a preset.
        
        Args:
            preset_name (str): The preset name.
            preset_items (list): The blender objects that make up the preset.
        """
        # Get highest radius value.
        highest_x = max([part.location[0] for part in preset_items])
        lowest_x = min([part.location[0] for part in preset_items])
        highest_y = max([part.location[1] for part in preset_items])
        lowest_y = min([part.location[1] for part in preset_items])
        radius = max([abs(lowest_x), highest_x, abs(lowest_y), highest_y])
        # Create circle.
        bpy.ops.curve.primitive_nurbs_circle_add(
            radius=radius+4,
            enter_editmode=False,
            align='WORLD',
            location=(0.0, 0.0, 0.0),
            rotation=(0.0, 0.0, 0.0)
        )

        curve_object = bpy.context.view_layer.objects.active
        curve_object.name = preset_name
        curve_object.show_name = True
        curve_object["PresetID"] = preset_name
        me = curve_object.data
        me.name = preset_name + 'Mesh'
        for part in preset_items:
            # Parent object.
            utils.parent(part, curve_object)
            # Add controler specific preset properties.
            part.hide_select = True
            part["belongs_to_preset"] = True
            user_data = part["UserData"]
            material.assign_material(part, user_data, preset=True)
        
        # Place in cache.
        self.preset_cache[preset_name] = curve_object.name
        
        return curve_object

    # Serialisation ---
    def get_preset_data(self, object):
        """Given a blender object, generate useful NMS data from it.
        
        Args:
            object (bpy.ob): Blender scene object.
            is_preset (bool): Toggle to ignore data not required for presets.
        Returns:
            dict: Dictionary of information.
        """
        # Get Matrix Data
        ob_world_matrix = object.matrix_world
        # Bring the matrix from Blender Z-Up soace into standard Y-up space.
        mat_rot = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
        obj_wm_offset = mat_rot @ ob_world_matrix
        # Retrieve Position, Up and At vectors.
        pos = obj_wm_offset.decompose()[0]
        up = utils.get_direction_vector(obj_wm_offset, direction_matrix="up")
        at = utils.get_direction_vector(obj_wm_offset, direction_matrix="at")

        # Build dictionary.
        data = {
            "PresetID": "^{0}".format(object["PresetID"]),
            "Position": [pos[0], pos[1], pos[2]],
            "Up": [up[0], up[1], up[2]],
            "At": [at[0], at[1], at[2]]
        }
        return data

    def get_all_preset_data(self):
        """Get a list of data of all No Man's Sky related objects."""
        datas = []
        preset_objects = self.get_all_preset_objects()
        for item in preset_objects:
            datas.append(self.get_preset_data(item))
        return datas

    def generate_preset_internal_data(self):
        return self.part_builder.get_all_part_data(
            skip_object_type=["BASE_FLAG"]
        )

    def save_preset_data(self, preset_name):
        data = {"Objects": self.generate_preset_internal_data()}
        file_path = os.path.join(self.PRESET_PATH, preset_name)
        # Add .json if it's not specified.
        if not file_path.endswith(".json"):
            file_path += ".json"
        # Save to file path
        with open(file_path, "w") as stream:
            json.dump(data, stream, indent=4)
