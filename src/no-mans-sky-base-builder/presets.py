import math
import os
from copy import deepcopy

import bpy

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

    def get_presets(self):
        """Get the list of presets."""
        return [os.path.basename(preset) for preset in os.listdir(self.PRESET_PATH) if preset.endswith(".json")]

    def get_nice_name(self, preset):
        return os.path.basename(preset)

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

    def get_obj_path(self, part):
        """Get the path to the OBJ file from a part."""
        part_dictionary = self.part_reference.get(part, {})
        return part_dictionary.get("full_path", None)

    def retrieve_preset(self, preset_name):
        """Retrieve the preset that represents the part.
        
        There are 3 outcomes.
            - If the preset already exists in the scene cache, we can just
                duplciate it.
            - If it doesn't exist in the cache, find the obj path.
            - If the obj path doesn't exist, just createa  cube.
        """
        # Duplicate.
        if preset_name in self.preset_cache:
            item_object = self.preset_cache[preset_name]
            # If it's in the cache, but deleted by user, we can import again.
            all_item_names = [item.name for item in bpy.data.objects]
            if item_object.name in all_item_names:
                return utils.duplicate_hierarchy(item)

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
            radius=radius + 4,
            view_align=False,
            enter_editmode=False,
            location=(0, 0, 0),
            layers=(
                True, False, False, False, False, False, False, False, False,
                False, False, False, False, False, False, False, False, False,
                False, False
            ),
        )
        curve_object = bpy.context.scene.objects.active
        curve_object.name = preset_name
        curve_object.show_name = True
        curve_object["presetID"] = preset_name
        me = curve_object.data
        me.name = preset_name + 'Mesh'
        for part in preset_items:
            # Parent object.
            utils.parent(curve_object, part)
            # Add controler specific preset properties.
            part.hide_select = True
            part["belongs_to_preset"] = True
            user_data = part["UserData"]
            material.assign_material(part, user_data, preset=True)

        return curve_object
