"""The builder contains all top level scene methods for managing NMS parts."""

import json
import os
import time
from collections import defaultdict

import bpy
from mathutils import Matrix

from .. import group, part, preset
from ..utils import blend_utils
from . import importer, overrides, paths
from .catalog import Catalog


class Builder(Catalog):

    # Tool Level Paths ---
    USER_PATH = paths.USER_PATH
    FILE_PATH = paths.ADDON_PATH
    MODEL_PATH = paths.MODEL_PATH
    FOSSIL_PARTS_PATH = paths.FOSSIL_PARTS_PATH
    NICE_JSON = paths.NICE_JSON
    MODS_PATH = paths.MODS_PATH
    PRESET_PATH = paths.PRESET_PATH

    override_classes = overrides.OVERRIDE_CLASSES

    def __init__(self):
        """Builder __init__."""
        super(Builder, self).__init__()
        # parts and presets share one cache, keyed by their id
        self.__part_cache = {}

    # Cache ---
    def clear_caches(self):
        """Clear all the caches we use in this class."""
        self.__part_cache.clear()

    def add_to_part_cache(self, object_id, bpy_object):
        """Add item to part cache."""
        self.__part_cache[object_id] = bpy_object.name

    def add_to_preset_cache(self, preset_id, bpy_object):
        """Add item to preset cache."""
        self.__part_cache[preset_id] = bpy_object.name

    def _get_cached_bpy_object(self, item_id):
        # cached names can go stale when the user deletes or renames objects
        item_name = self.__part_cache.get(item_id, None)
        if not item_name:
            return None
        return bpy.data.objects.get(item_name)

    def find_object_by_id(self, object_id):
        """Get the item from the part cache."""
        bpy_object = self._get_cached_bpy_object(object_id)
        if bpy_object is None:
            return None
        return self.get_builder_object_from_bpy_object(bpy_object)

    def find_preset_by_id(self, preset_id):
        """Get the item from the part cache."""
        bpy_object = self._get_cached_bpy_object(preset_id)
        if bpy_object is None:
            return None
        return preset.Preset.deserialise_from_object(
            bpy_object=bpy_object, builder_object=self
        )

    # Lookups ---
    @classmethod
    def get_part_class(cls, object_id):
        return overrides.get_part_class(object_id)

    def get_builder_object_from_bpy_object(self, bpy_object):
        # Handle Presets.
        if "PresetID" in bpy_object:
            return preset.Preset.deserialise_from_object(
                bpy_object=bpy_object, builder_object=self
            )

        # Handle Parts.
        object_id = bpy_object.get("ObjectID") or bpy_object.get("SnapID")
        if not object_id:
            return None

        use_class = self.get_part_class(object_id)
        return use_class.deserialise_from_object(
            bpy_object=bpy_object, builder_object=self
        )

    def get_all_parts(
        self, exclude_presets=False, skip_object_type=None, include_lines=False
    ):
        """Get all NMS parts in the scene.

        Args:
            exclude_presets (bool): Choose to exclude parts generated via
                preset.
            skip_object_type (list): ObjectIDs to leave out.
            include_lines (bool): Include line control points.
        """
        skip_object_type = skip_object_type or []

        flat_parts = []
        for item in bpy.context.scene.objects:
            if "ObjectID" in item:
                if item["ObjectID"] in skip_object_type:
                    continue
                if exclude_presets and item.get("belongs_to_preset", False):
                    continue
                flat_parts.append(item)
            elif include_lines and "SnapID" in item:
                flat_parts.append(item)

        return sorted(flat_parts, key=Builder.by_order)

    def get_all_presets(self):
        """Get all Builder preset items in the scene."""
        return [item for item in bpy.context.scene.objects if "PresetID" in item]

    def get_all_groups(self):
        """Get all groups in the scene."""
        return [item for item in bpy.context.scene.objects if group.Group.PROP_GROUP_ID in item]

    @staticmethod
    def by_order(bpy_object):
        """Sorting method to get objects by the order attribute.

        Args:
            bpy_object (bpy.ob): A blender object.

        Returns:
            int: The order of which the item is/was built.
        """
        return bpy_object.get("order", 0)

    # Building ---
    def add_part(self, object_id, user_data=None, build_rigs=True):
        """Add an item based on it's object ID."""
        object_id = object_id.replace("^", "")
        use_class = self.get_part_class(object_id)

        # captured before the part exists so it lands on the previous selection
        active_object = blend_utils.get_selected_active_object()
        item = use_class(
            object_id=object_id,
            builder_object=self,
            user_data=user_data,
            build_rigs=build_rigs,
        )

        if active_object is not None:
            item.object.matrix_world = active_object.matrix_world.copy()
        return item

    def add_preset(self, preset_id):
        """Add an item based on it's preset ID."""
        return preset.Preset(preset_id=preset_id, builder_object=self)

    def mirror_part(self, part_object):
        new_object_id = part.Part.get_mirror_part_id(part_object["ObjectID"])
        return self._swap_to_twin(part_object, new_object_id, (1, 0, 0))

    def flip_part(self, part_object):
        new_object_id = part.Part.get_flip_part_id(part_object["ObjectID"])
        return self._swap_to_twin(part_object, new_object_id, (0, 1, 0))

    def _swap_to_twin(self, part_object, new_object_id, flip_axis):
        # meshes are shared between parts, so never transform a shared one in place
        if part_object.data.users > 1:
            part_object.data = part_object.data.copy()
        part_object.data.transform(Matrix.Scale(-1, 4, flip_axis))

        # Update ObjectID, name and cache
        self.__part_cache.pop(part_object["ObjectID"], None)
        part_object["ObjectID"] = new_object_id
        part_object.name = new_object_id
        self.__part_cache[new_object_id] = part_object.name
        return part_object

    def build_rigs(self):
        """Get all items that require a rig and build them."""
        blend_utils.scene_refresh()
        for item in self.get_all_parts(exclude_presets=True):
            # checked on the class, most parts have no rig and needn't be wrapped
            if not hasattr(self.get_part_class(item["ObjectID"]), "build_rig"):
                continue
            builder_object = self.get_builder_object_from_bpy_object(item)
            builder_object.build_rig()

    def optimise_control_points(self):
        """Find all control points that share the same location and combine them."""
        blend_utils.scene_refresh()

        # Group controls by location, rounded as controls in the same place
        # have slightly different values.
        power_control_reference = defaultdict(list)
        for power_control in bpy.data.objects:
            if "rig_item" not in power_control:
                continue
            key = ",".join(
                str(round(loc, 3)) for loc in power_control.matrix_world.decompose()[0]
            )
            power_control_reference[key].append(power_control)

        # Swap any duplicate controls with the first instance.
        # removed in one batch at the end, a remove() per control re-syncs the file each time
        doomed = []
        for controls in power_control_reference.values():
            unique_control = controls[0]
            for control in controls[1:]:
                power_line = blend_utils.get_item_by_name(control["power_line"])
                power_line_obj = self.get_builder_object_from_bpy_object(power_line)
                prev_start_control = bpy.data.objects[power_line_obj.start_control]
                prev_end_control = bpy.data.objects[power_line_obj.end_control]

                if control == prev_start_control:
                    power_line_obj.build_rig(unique_control, prev_end_control)
                else:
                    power_line_obj.build_rig(prev_start_control, unique_control)

                doomed.append(control)

        if doomed:
            bpy.data.batch_remove(doomed)

    # Serialising ---
    def serialise(self, get_presets=False, add_timestamp=False, as_prefab=False, include_groups=True):
        """Return NMS compatible dictionary.

        Args:
            get_presets (bool): This will generate data for presets. And
                exclude parts generated from presets.
            include_groups (bool): Save the parts inside groups.
        Returns:
            dict: Dictionary of base information.
        """
        object_list = []
        for item in self.get_all_parts(exclude_presets=get_presets):
            use_class = self.get_part_class(item["ObjectID"])
            item_obj = use_class.deserialise_from_object(item, builder_object=self)
            object_list.append(item_obj.serialise())

        # NMS has no groups, a group is saved as the parts in it
        if include_groups:
            for group_obj in self.get_all_groups():
                object_list += group.Group.serialise(group_obj) or []

        key = "Prefab" if as_prefab else "Objects"
        data = {key: object_list}

        if add_timestamp:
            data["timestamp"] = int(time.time())

        data["BaseVersion"] = 8

        if get_presets:
            data["Presets"] = [
                preset.Preset.deserialise_from_object(
                    _preset, builder_object=self
                ).serialise()
                for _preset in self.get_all_presets()
            ]

        return data

    def deserialise_from_data(self, data):
        """Given NMS data, reconstruct the base."""
        if data is None:
            return

        compensate_normal = data.get("BaseVersion", 8) >= 5

        importer.import_objects(
            self, data.get("Objects", []), compensate_normal=compensate_normal
        )

        for preset_data in data.get("Presets", []):
            preset.Preset.deserialise_from_data(
                preset_data, self, compensate_normal=compensate_normal
            )

        self.build_rigs()
        self.optimise_control_points()

    def save_preset_to_file(self, preset_name):
        all_presets = preset.Preset.get_presets()
        if preset_name in all_presets:
            file_path = all_presets[preset_name]
        else:
            file_path = os.path.join(self.PRESET_PATH, preset_name)

        if not file_path.endswith(".nmsprefab"):
            file_path += ".nmsprefab"

        with open(file_path, "w") as stream:
            json.dump(self.serialise(add_timestamp=False, as_prefab=True), stream, indent=4)
