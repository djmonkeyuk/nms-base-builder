"""The builder contains all top level scene methods for managing NMS parts."""

# import cProfile
import importlib
import json
import math
import os
import time
from collections import defaultdict
from copy import copy

import bpy
from mathutils import Matrix

from . import part, preset
from .part_overrides import (bone, bone_replacer, line, locked, message,
                             power_control, turret, u_bytebeatline, u_pipeline,
                             u_portalline, u_powerline)
from .utils import blend_utils
from .utils import python as python_utils


class Builder(object):

    # Tool Level Paths ---
    USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
    FILE_PATH = os.path.dirname(os.path.realpath(__file__))
    MODEL_PATH = os.path.join(FILE_PATH, "models")
    FOSSIL_PARTS_PATH = os.path.join(FILE_PATH, "models", "fossil_parts")
    NICE_JSON = os.path.join(FILE_PATH, "resources", "nice_names.json")
    MODS_PATH = os.path.join(USER_PATH, "mods")
    PRESET_PATH = os.path.join(USER_PATH, "presets")

    # Load in nice name information.
    nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)

    override_classes = {
        bone_replacer.BONE_REPLACER: [
            "FOS_HEAD",
            "FOS_SKULL",
            "FOS_LIMBS",
            "FOS_TAIL",
            "FOS_BODY",
        ],
        bone.BONE: [
            os.path.splitext(filename)[0] for filename in os.listdir(FOSSIL_PARTS_PATH)
        ],
        turret.TURRET: ["B_TUR_A", "B_TUR_B", "B_TUR_C", "B_TUR_D", "B_TUR_E"],
        u_powerline.U_POWERLINE: ["U_POWERLINE"],
        u_pipeline.U_PIPELINE: ["U_PIPELINE"],
        u_portalline.U_PORTALLINE: ["U_PORTALLINE"],
        u_bytebeatline.U_BYTEBEATLINE: ["U_BYTEBEATLINE"],
        power_control.POWER_CONTROL: ["POWER_CONTROL"],
        locked.LOCKED: [
            "BASE_FLAG",
            "BRIDGECONNECTOR",
            "AIRLCKCONNECTOR",
            "FREIGHTER_CORE",
        ],
        message.MESSAGE: [
            "MESSAGEMODULE",
            "BYTEBEAT",
            "BYTEBEATSWITCH",
            "HOLO_DISCO_0",
            "FOS_BI",
            "FOS_BIRD",
            "FOS_BIRD_DIS",
            "FOS_BI_DIS",
            "FOS_BODY",
            "FOS_BODY_DISP",
            "FOS_BODY_MNT",
            "FOS_GRUN",
            "FOS_GRUN_DIS",
            "FOS_LIMBS",
            "FOS_LIMBS_DISP",
            "FOS_LIMBS_MNT",
            "FOS_QUAD",
            "FOS_QUAD_DIS",
            "FOS_SKULL",
            "FOS_SKULL_DISP",
            "FOS_SKULL_MNT",
            "FOS_TAIL",
            "FOS_TAIL_DISP",
            "FOS_TAIL_MNT",
            "FOS_WORM",
            "FOS_WORM_DIS",
        ],
    }

    def __init__(self):
        """Builder __init__."""

        # Part Cache.
        self.__part_cache = {}
        self.__preset_cache = {}

        # Construct category and OBJ reference.
        # Create default part pack.
        self.available_packs = [("Parts", self.MODEL_PATH)]

        # Find any mods with model packs inside.
        if os.path.exists(self.MODS_PATH):
            mod_folders = os.listdir(self.MODS_PATH)
            for mod_folder in mod_folders:
                full_mod_path = os.path.join(self.MODS_PATH, mod_folder)
                if "models" in os.listdir(full_mod_path):
                    full_model_path = os.path.join(self.MODS_PATH, mod_folder, "models")
                    self.available_packs.append((mod_folder, full_model_path))

        # Find Parts and build a reference dictionary.
        self.part_reference = {}
        for pack_name, pack_folder in self.available_packs:
            for category in self.get_categories(pack=pack_name):
                parts = self.get_objs_from_category(category, pack=pack_name)
                for part in parts:
                    # Get Unique ID.
                    unique_id = os.path.splitext(part)[0]
                    # Construct full path.
                    search_path = pack_folder or self.MODEL_PATH
                    part_path = os.path.join(search_path, category, part)
                    # Place part information into reference.
                    self.part_reference[unique_id] = {
                        "category": category,
                        "full_path": part_path,
                        "pack": pack_name,
                    }

    def clear_caches(self):
        """Clear all the caches we use in this class."""
        self.__part_cache.clear()

    def add_to_part_cache(self, object_id, bpy_object):
        """Add item to part cache."""
        self.__part_cache[object_id] = bpy_object.name

    def add_to_preset_cache(self, object_id, bpy_object):
        """Add item to preset cache."""
        self.__part_cache[object_id] = bpy_object.name

    def find_object_by_id(self, object_id):
        """Get the item from the part cache."""
        part_name = self.__part_cache.get(object_id, None)
        # Return None if not found.
        if not part_name:
            return None
        # If something is found, we need to check if it still exists.
        if part_name in bpy.data.objects:
            bpy_object = bpy.data.objects[part_name]
            return self.get_builder_object_from_bpy_object(bpy_object)
        # If all fails, return None.
        return None

    @classmethod
    def get_part_class(cls, object_id):
        for class_ref, part_list in cls.override_classes.items():
            if object_id in part_list:
                return class_ref
        return part.Part

    def get_builder_object_from_bpy_object(self, bpy_object):
        # Handle Presets.
        if "PresetID" in bpy_object:
            return preset.Preset.deserialise_from_object(
                bpy_object=bpy_object, builder_object=self
            )

        # Handle Parts.
        object_id = None
        if "ObjectID" in bpy_object:
            object_id = bpy_object.get("ObjectID")
        elif "SnapID" in bpy_object:
            object_id = bpy_object.get("SnapID")

        if not object_id:
            return None

        use_class = self.get_part_class(object_id)
        return use_class.deserialise_from_object(
            bpy_object=bpy_object, builder_object=self
        )

    def find_preset_by_id(self, preset_id):
        """Get the item from the part cache."""
        preset_name = self.__part_cache.get(preset_id, None)
        # Return None if not found.
        if not preset_name:
            return None
        # If something is found, we need to check if it still exists.
        if preset_name in bpy.data.objects:
            bpy_object = bpy.data.objects[preset_name]
            return preset.Preset.deserialise_from_object(
                bpy_object=bpy_object, builder_object=self
            )
        # If all fails, return None.
        return None

    def get_all_parts(
        self, exclude_presets=False, skip_object_type=None, include_lines=False
    ):
        """Get all NMS parts in the scene.

        Args:
            get_presets (bool): Choose to exclude parts generated via
                preset.
        """
        # Validate skip list
        skip_object_type = skip_object_type or []

        # Get all individual NMS parts.
        flat_parts = [part for part in bpy.data.objects if "ObjectID" in part]
        flat_parts = [
            part for part in flat_parts if part["ObjectID"] not in skip_object_type
        ]

        # Include line conatrol points?
        if include_lines:
            flat_parts.extend(
                [
                    part
                    for part in bpy.data.objects
                    if "SnapID" in part and not "ObjectID" in part
                ]
            )

        # If exclude presets is on, just return the top level objects.
        if exclude_presets:
            flat_parts = [
                part for part in flat_parts if part["belongs_to_preset"] == False
            ]
        flat_parts = sorted(flat_parts, key=Builder.by_order)
        return flat_parts

    def get_all_presets(self):
        """Get all Builder preset items in the scene."""
        return [part for part in bpy.data.objects if "PresetID" in part]

    def add_part(self, object_id, user_data=None, build_rigs=True):
        """Add an item based on it's object ID."""
        use_class = self.get_part_class(object_id)
        item = use_class(
            object_id=object_id,
            builder_object=self,
            user_data=user_data,
            build_rigs=build_rigs,
        )
        return item

    def add_preset(self, preset_id):
        """Add an item based on it's preset ID."""
        item = preset.Preset(preset_id=preset_id, builder_object=self)
        return item

    def mirror_part(self, part_object):
        object_id = part_object["ObjectID"]
        new_object_id = part.Part.get_mirror_part_id(object_id)
        # Flip mesh vertices across X
        mirror_matrix = Matrix.Scale(-1, 4, (1, 0, 0))
        part_object.data.transform(mirror_matrix)
        # Update ObjectID and name
        part_object["ObjectID"] = new_object_id
        part_object.name = new_object_id
        # Update cache
        if object_id in self.__part_cache:
            del self.__part_cache[object_id]
        self.__part_cache[new_object_id] = part_object.name
        return part_object

    def flip_part(self, part_object):
        object_id = part_object["ObjectID"]
        new_object_id = part.Part.get_flip_part_id(object_id)
        # Flip mesh vertices across Y
        mirror_matrix = Matrix.Scale(-1, 4, (0, 1, 0))
        part_object.data.transform(mirror_matrix)
        # Update ObjectID and name
        part_object["ObjectID"] = new_object_id
        part_object.name = new_object_id
        # Update cache
        if object_id in self.__part_cache:
            del self.__part_cache[object_id]
        self.__part_cache[new_object_id] = part_object.name
        return part_object

    # Serialising ---
    def serialise(self, get_presets=False, add_timestamp=False, as_prefab=False):
        """Return NMS compatible dictionary.

        Args:
            get_presets (bool): This will generate data for presets. And
                exclude parts generated from presets.
        Returns:
            dict: Dictionary of base information.
        """
        # Get all object part data.
        object_list = []

        for item in self.get_all_parts(exclude_presets=get_presets):
            object_id = item["ObjectID"]
            use_class = self.get_part_class(object_id)
            item_obj = use_class.deserialise_from_object(item, builder_object=self)
            object_list.append(item_obj.serialise())

        # Create full dictionary.
        key = "Prefab" if as_prefab else "Objects"
        data = {key: object_list}

        if add_timestamp:
            data["timestamp"] = int(time.time())

        # Add Base Version
        data["BaseVersion"] = 8

        # Add preset information if specified.
        if get_presets:
            preset_list = []
            for _preset in self.get_all_presets():
                preset_obj = preset.Preset.deserialise_from_object(
                    _preset, builder_object=self
                )
                preset_list.append(preset_obj.serialise())
            data["Presets"] = preset_list

        return data

    def deserialise_from_data(self, data):
        """Given NMS data, reconstruct the base.

        We don't need to create a new class, we can act upon this one.
        """

        base_version = data.get("BaseVersion", 8)

        compensate_normal = True
        if base_version < 5:
            compensate_normal = False

        # Reconstruct objects.
        for part_data in data.get("Objects", []):
            object_id = part_data.get("ObjectID").replace("^", "")
            use_class = self.get_part_class(object_id)
            use_class.deserialise_from_data(
                part_data, self, compensate_normal=compensate_normal
            )

        # Reconstruct presets.
        for preset_data in data.get("Presets", []):
            preset.Preset.deserialise_from_data(
                preset_data, self, compensate_normal=compensate_normal
            )

        # Build Rigs.
        self.build_rigs()
        # Optimise control points.
        self.optimise_control_points()

    @staticmethod
    def by_order(bpy_object):
        """Sorting method to get objects by the order attribute.

        Args:
            bpy_object (bpy.ob): A blender object.

        Returns:
            int: The order of which the item is/was built.
        """
        return bpy_object.get("order", 0)

    # Category Methods ---
    def get_categories(self, pack=None):
        """Get the list of categories.

        Args:
            pack (str): The model pack search under for categories.
                Use this for mod support. Defaults to vanilla 'Parts'.
        Returns:
            list: List of folders underneath category path.
        """
        # Validate Pack name.
        pack = pack or "Parts"
        # Get the associated model path.
        search_path = self.get_model_path_from_pack(pack)
        return os.listdir(search_path)

    def get_preset_categories(self):
        """Get the list of preset categories.

        Returns:
            list: List of folders underneath preset path.
        """
        return [
            item
            for item in os.listdir(preset.Preset.PRESET_PATH)
            if os.path.isdir(os.path.join(preset.Preset.PRESET_PATH, item))
        ]

    def get_uncategorized_presets(self):
        presets = []
        for preset_file in os.listdir(preset.Preset.PRESET_PATH):
            if preset_file.endswith(".json") or preset_file.endswith(".nmsprefab"):
                presets.append(os.path.splitext(preset_file)[0])
        return presets

    def get_presets_from_category(self, category):
        """Get a list of presets underneath a category.

        Args:
            category (str): The name of the category.
        """
        presets = []
        for preset_file in os.listdir(
            os.path.join(preset.Preset.PRESET_PATH, category)
        ):
            if preset_file.endswith(".json") or preset_file.endswith(".nmsprefab"):
                presets.append(os.path.splitext(preset_file)[0])
        return presets

    def get_objs_from_category(self, category, pack=None):
        """Get a list of parts belonging to a category.

        Args:
            category (str): The name of the category.
            pack (str): The model pack search under for categories.
                Use this for mod support. Defaults to vanilla 'Parts'.
        """
        # Validate Pack name.
        pack = pack or "Parts"
        # Get the associated model path.
        search_path = self.get_model_path_from_pack(pack)
        category_path = os.path.join(search_path, category)
        all_objs = [part for part in os.listdir(category_path) if part.endswith(".fbx")]
        file_names = sorted(all_objs)
        return file_names

    def get_obj_path(self, part):
        """Get the path to the OBJ file from a part."""
        part_dictionary = self.part_reference.get(part, {})
        return part_dictionary.get("full_path", None)

    def get_obj_parent_folder(self, part):
        """Get the path to the OBJ file from a part."""
        path = self.get_obj_path(part)
        folder = os.path.dirname(path).split(os.sep)[-1]
        return folder

    def get_model_path_from_pack(self, pack_request):
        """Given a pack name, return it's associated path.

        Args:
            pack_request (str): The name of the pack

        Return:
            str: The model path of the pack.
        """
        for pack_name, pack_path in self.available_packs:
            if pack_name == pack_request:
                return pack_path

    def get_parts_from_category(self, category, pack=None):
        """Get all the parts from a specific category.

        Args:
            category (str): The category to search.
            pack (str): The model pack name. Defaults to vanilla 'Parts'.
        """
        # Validate pack name.
        pack = pack or "Parts"
        parts = []
        for item, value in self.part_reference.items():
            # Get pack and category values.
            part_category = value["category"]
            part_pack = value["pack"]
            # Check both are valid.
            pack_check = part_pack == pack
            category_check = part_category == category
            # Add to parts.
            if pack_check and category_check:
                parts.append(item)
        return sorted(parts)

    def get_nice_name(self, part):
        """Get a nice version of the part id."""
        part = os.path.basename(part)
        nice_name = part.title().replace("_", " ")
        return self.nice_name_dictionary.get(part, nice_name)

    def save_preset_to_file(self, preset_name):
        # Get a file path.
        all_presets = preset.Preset.get_presets()
        if preset_name in preset.Preset.get_presets():
            file_path = all_presets[preset_name]
        else:
            file_path = os.path.join(self.PRESET_PATH, preset_name)
        # Add .json if it's not specified.
        if not file_path.endswith(".nmsprefab"):
            file_path += ".nmsprefab"
        # Save to file path
        with open(file_path, "w") as stream:
            json.dump(self.serialise(add_timestamp=False, as_prefab=True), stream, indent=4)

    def build_rigs(self):
        """Get all items that require a rig and build them."""
        blend_utils.scene_refresh()
        parts = self.get_all_parts(exclude_presets=True)
        for part in parts:
            builder_object = self.get_builder_object_from_bpy_object(part)
            if hasattr(builder_object, "build_rig"):
                builder_object.build_rig()

    def optimise_control_points(self):
        """Find all control points that share the same location and combine them."""
        blend_utils.scene_refresh()

        # First build a dictionary of controls that match.
        power_control_objects = [obj for obj in bpy.data.objects if "rig_item" in obj]
        power_control_reference = defaultdict(list)
        for power_control in power_control_objects:
            # Create a key that will group the controls based on their location.
            # I am rounding the decimal point to 4 as the accuracy means items
            # in the same location have slightly different values.
            key = ",".join(
                [
                    str(round(loc, 3))
                    for loc in power_control.matrix_world.decompose()[0]
                ]
            )
            # Append the control to the key.
            power_control_reference[key].append(power_control)

        # Swap any duplicate controls with the first instance.
        for key, value in power_control_reference.items():
            unique_control = value[0]
            other_controls = value[1:]

            if not other_controls:
                continue

            for control in other_controls:
                power_line = blend_utils.get_item_by_name(control["power_line"])
                power_line_obj = self.get_builder_object_from_bpy_object(power_line)
                prev_start_control = bpy.data.objects[power_line_obj.start_control]
                prev_end_control = bpy.data.objects[power_line_obj.end_control]

                # Assign new controls.
                if control == prev_start_control:
                    power_line_obj.build_rig(unique_control, prev_end_control)
                else:
                    power_line_obj.build_rig(prev_start_control, unique_control)

                # Hide away control.
                blend_utils.remove_object(control.name)
