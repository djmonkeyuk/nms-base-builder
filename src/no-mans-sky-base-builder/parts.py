import logging
import math
import os
from copy import deepcopy

import bpy
import mathutils

from . import material, utils

LOGGER = logging.getLogger(__name__)


class PartBuilder(object):

    # Resources.
    FILE_PATH = os.path.dirname(os.path.realpath(__file__))
    MODEL_PATH = os.path.join(FILE_PATH, "models")
    LIGHTS_JSON = os.path.join(FILE_PATH, "resources", "lights.json")
    NICE_JSON = os.path.join(FILE_PATH, "resources", "nice_names.json")
    # Mods.
    USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
    MODS_PATH = os.path.join(USER_PATH, "mods")

    def __init__(self):
        """Initialise.

        Create a dictionary reference of part ID's and their OBJ path.
        """
        # Load in light information.
        self.lights_dictionary = utils.load_dictionary(self.LIGHTS_JSON)
        # Load in nice name information.
        self.nice_name_dictionary = utils.load_dictionary(self.NICE_JSON)
        # Set an initial order flag.
        self.part_order = 0
        # Construct part information.
        self.part_cache = {}
        self.part_reference = {}

        # Create default part pack.
        self.available_packs = [("Parts", self.MODEL_PATH)]

        # Find any mods with model packs inside.
        if os.path.exists(self.MODS_PATH):
            mod_folders = os.listdir(self.MODS_PATH)
            for mod_folder in mod_folders:
                full_mod_path = os.path.join(self.MODS_PATH, mod_folder)
                if "models" in os.listdir(full_mod_path):
                    full_model_path = os.path.join(
                        self.MODS_PATH,
                        mod_folder,
                        "models"
                    )
                    self.available_packs.append((mod_folder, full_model_path))

        # Find Parts and build a reference dictionary.
        for (pack_name, pack_folder) in self.available_packs:
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
                        "pack": pack_name
                    }

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

    def clear_cache(self):
        """Clear the part cache."""
        self.part_cache.clear()

    @staticmethod
    def by_order(item):
        """Sorting method to get objects by the order attribute.
        
        Args:
            items (bpy.ob): A blender object.

        Returns:
            int: The order of which the item is/was built.
        """
        if "Order" in item:
            return item["Order"]
        return 0

    def get_all_nms_objects(self, capture_presets=False, skip_object_type=None):
        """Wrapper to retrieve all blender objects that are made for NMS.

        If capture_presets is True, we get a list of all top level parts and
        preset objects.

        If it's False, we get all top level and preset level NMS items. We
        also excluse all top level preset items. 
        
        Args:
            capture_presets (bool): Decide whether or not we want to be aware
                of presets. If not it will get all individual pieces.
            skip_object_type (list): Specify item types we want to skip.
                Use this to skip BASE_FLAG for saving presets.
        """
        if capture_presets:
            # Get all preset and top level parts.
            presets = [part for part in bpy.data.objects if "PresetID" in part]
            # Get All top level flat parts.
            flat_parts = [part for part in bpy.data.objects if "ObjectID" in part]
            flat_parts = [part for part in flat_parts if part["belongs_to_preset"] == False]
            flat_parts = [part for part in flat_parts if part["ObjectID"] not in skip_object_type]
            flat_parts = sorted(flat_parts, key=self.by_order)
            return presets + flat_parts
        else:
            # Get all individual NMS parts.
            flat_parts = [part for part in bpy.data.objects if "ObjectID" in part]
            flat_parts = [part for part in flat_parts if part["ObjectID"] not in skip_object_type]
            flat_parts = sorted(flat_parts, key=self.by_order)
            return flat_parts

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
        # Validate category path.
        if not os.path.exists(category_path):
            raise RuntimeError(category + " does not exist.")

        all_objs = [
            part for part in os.listdir(category_path) if part.endswith(".obj")
        ]
        file_names = sorted(all_objs)
        return file_names

    def get_obj_path(self, part):
        """Get the path to the OBJ file from a part."""
        part_dictionary = self.part_reference.get(part, {})
        return part_dictionary.get("full_path", None)

    def get_nice_name(self, part):
        """Get a nice version of the part id."""
        part = os.path.basename(part)
        nice_name = part.title().replace("_", " ")
        return self.nice_name_dictionary.get(part, nice_name)

    def retrieve_part(self, part_name):
        """Retrieve the object that represents the part.
        
        There are 3 outcomes.
        - If the object already exists in the scene cache, we can just
            duplciate it.
        - If it doesn't exist in the cache, find the obj path.
        - If the obj path doesn't exist, just createa  cube.
        """
        # Duplicate.
        if part_name in self.part_cache:
            cached_item_name = self.part_cache[part_name]
            # If it's in the cache, but deleted by user, we can import again.
            if cached_item_name in bpy.data.objects:
                cached_item = bpy.data.objects[cached_item_name]
                new_item = utils.duplicate_hierarchy(cached_item)
                utils.reset_selection_state(new_item)
                utils.clear_parent(new_item)
                utils.zero_transforms(new_item)
                return new_item

        # Obj.
        obj_path = self.get_obj_path(part_name) or ""
        # If it exists, import the obj.
        if os.path.isfile(obj_path):
            bpy.ops.import_scene.obj(filepath=obj_path, split_mode="OFF")
        else:
            # If not then create a blender cube.
            bpy.ops.mesh.primitive_cube_add()

        item = bpy.context.selected_objects[0]
        # Assign name.
        item.name = part_name
        item["ObjectID"] = part_name
        # Place in cache.
        self.part_cache[part_name] = item.name
        # Create Light.
        # self.build_light(item)
        return item

    def get_part_data(self, object, is_preset=False):
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
            "ObjectID": "^{0}".format(object["ObjectID"]),
            "Position": [pos[0], pos[1], pos[2]],
            "Up": [up[0], up[1], up[2]],
            "At": [at[0], at[1], at[2]]
        }

        # Add Particular information.
        if not is_preset:
            timestamp = object["Timestamp"]
            user_data = object["UserData"]
            data["Timestamp"] = int(timestamp)
            data["UserData"] = int(user_data)

        return data

    def get_all_part_data(self, capture_presets=False, skip_object_type=None):
        """Get a list of data of all No Man's Sky related objects."""
        skip_object_type = skip_object_type or []
        datas = []
        nms_objects = self.get_all_nms_objects(
            capture_presets=capture_presets,
            skip_object_type=skip_object_type
        )
        for item in nms_objects:
            if "ObjectID" in item:
                datas.append(self.get_part_data(item))
        return datas

    def build_item(
        self,
        part,
        timestamp=1539023700,
        userdata=0,
        position=[0, 0, 0],
        up_vec=[0, 1, 0],
        at_vec=[0, 0, 1]):
        """Build a part given a set of paremeters.
        
        This is they main function of the program for building.

        Args:
            part (str): The part ID.
            timestamp (int): The timestamp of build (this should go away and compute automatically).
            user_data(int): This determines the colour of a part, default is 0 for now.
            position (vector): The location of the part.
            up_vec(vector): The up vector for the part orientation.
            at_vec(vector): The aim vector for the part orientation.
        """
        # Get the obj path.
        item = self.retrieve_part(part)

        # Lock Scale
        item.lock_scale[0] = True
        item.lock_scale[1] = True
        item.lock_scale[2] = True
        # Lock Everything if it's the BASE_FLAG. Things can break if user
        # moves this around.
        if part == "BASE_FLAG":
            item.lock_location[0] = True
            item.lock_location[1] = True
            item.lock_location[2] = True
            item.lock_rotation[0] = True
            item.lock_rotation[1] = True
            item.lock_rotation[2] = True
        
        # Add custom attributes.
        item["ObjectID"] = part
        item["Timestamp"] = timestamp
        item["belongs_to_preset"] = False
        # Add an order flag to retain order when generating data..
        item["Order"] = self.part_order
        self.part_order += 1
        # Apply Colour
        material.assign_material(item, userdata)

        # Move
        utils.move_to(item, position=position, up=up_vec, at=at_vec)
        
        # Select the new object.
        item.select_set(True)
        return item

    def build_parts_from_json(self, json_path):
        # Validate preset existence.
        if not os.path.isfile(json_path):
            return

        # Load Data.
        data = utils.load_dictionary(json_path)

        if data:
            return self.build_parts_from_dict(data)

    def build_parts_from_dict(self, data):
        """Given the preset name, generate the items in scene.
        
        Args:
            preset_name (str): The name of the preset.
            edit_mode (bool): Toggle to build
        """
       
        # Validate Objects information.
        if "Objects" not in data:
            return

        # Start creating parts.
        parts = []
        for part_data in data["Objects"]:
            part = part_data["ObjectID"].replace("^", "")
            timestamp = part_data["Timestamp"]
            user_data = part_data["UserData"]
            part_position = part_data["Position"]
            up_vec = part_data["Up"]
            at_vec = part_data["At"]
            # Build the item.
            item = self.build_item(
                part,
                timestamp,
                user_data,
                part_position,
                up_vec,
                at_vec
            )
            parts.append(item)

        return parts

    # Lights ---
    def build_light(self, item):
        """If the part is is found to have light information, add them."""

        # Validete NMS object.
        if "ObjectID" not in item:
            return

        # Get object id from item.
        object_id = item["ObjectID"]
        # Find light data
        if object_id not in self.lights_dictionary:
            return

        # Build Lights
        light_information = self.lights_dictionary[object_id]
        for idx, light_values in enumerate(light_information.values()):
            # Get Light Properties.
            light_type = light_values["type"]
            light_location = light_values["location"]

            # Create light.
            light = bpy.ops.object.light_add(
                type=light_type.upper(),
                location=light_location
            )
            light = bpy.context.object
            light["NMS_LIGHT"] = True
            light.name = "{0}_light{1}".format(item.name, idx)
            data_copy = deepcopy(light_values)

            # Remove invalid blender properties.
            data_copy.pop("type")
            data_copy.pop("location")

            # Apply all other properties to blender object.
            for key, value in data_copy.items():
                if isinstance(value, list):
                    value = mathutils.Vector(tuple(value))
                setattr(light.data, key, value)

            # Parent to object.
            utils.parent(light, item)

            # Disable Selection.
            light.hide_viewport = True
            light.hide_select = True
