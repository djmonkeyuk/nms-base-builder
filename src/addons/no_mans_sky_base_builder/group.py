"""Groups merge parts into one object and keep each part in a cache.

The cache stores every part's ObjectID, UserData and matrix relative to the group,
so a group can be ungrouped, saved as its parts, or rebuilt somewhere else.
"""

import json
import math
import os
import time
import uuid

import bpy
import mathutils
from mathutils import Matrix, Vector

from .part import Part
from .utils import blend_utils, material, mirror_utils
from .utils import python as python_utils

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
nice_name_dictionary = python_utils.load_dictionary(
    os.path.join(FILE_PATH, "resources", "nice_names.json")
)


class Group:

    # part properties kept in the cache
    PROP_OBJECT_ID = Part.PROP_OBJECT_ID
    PROP_USER_DATA = Part.PROP_USER_DATA
    PROP_TIMESTAMP = Part.PROP_TIMESTAMP
    PROP_MESSAGE = Part.PROP_MESSAGE
    PROP_MATRIX_LOCAL = "matrix_local"

    # group properties
    PROP_CHILD_CACHE = "child_cache"
    PROP_GROUP_ID = "GroupID"
    PROP_ORIGIN_OFFSET = "origin_offset"
    PROP_ORIGIN_MATRIX = "origin_matrix"
    PROP_PART_COUNT = "part_count"
    PROP_IS_MIRROR = "is_mirror"

    MERGED_NAME = "Grouped_Objects"

    # Cache ---
    @staticmethod
    def cache_relative_matrices(parent_obj, object_list):
        """Cache each part relative to parent_obj, without parenting anything.

        Returns:
            str: JSON of {part name: part data}
        """
        cache_data = {}
        parent_matrix_inverted = parent_obj.matrix_world.inverted()

        for obj in object_list:
            if obj == parent_obj or Group.PROP_OBJECT_ID not in obj:
                continue

            matrix_local = parent_matrix_inverted @ obj.matrix_world
            cache = {
                Group.PROP_OBJECT_ID: obj[Group.PROP_OBJECT_ID],
                Group.PROP_USER_DATA: obj.get(Group.PROP_USER_DATA, 0),
                Group.PROP_TIMESTAMP: obj.get(Group.PROP_TIMESTAMP, int(time.time())),
                Group.PROP_MATRIX_LOCAL: [list(row) for row in matrix_local],
            }
            if obj.get(Group.PROP_MESSAGE):
                cache[Group.PROP_MESSAGE] = obj[Group.PROP_MESSAGE]

            cache_data[obj.name] = cache

        return json.dumps(cache_data)

    @staticmethod
    def extract_cached_data(parent_obj):
        """Returns (cached child data, origin matrix), or (None, None) when invalid."""
        if Group.PROP_CHILD_CACHE not in parent_obj:
            return None, None

        try:
            cache_child_data = json.loads(parent_obj[Group.PROP_CHILD_CACHE])
        except (TypeError, ValueError):
            return None, None
        origin_matrix = Group.str_to_matrix(parent_obj.get(Group.PROP_ORIGIN_MATRIX))
        return cache_child_data, origin_matrix

    # Grouping ---
    @staticmethod
    def group_objects(objects_to_group, target_matrix=None):
        """Merge parts into one group object.

        Args:
            objects_to_group (list): The objects to group, anything already a group stops it.
            target_matrix (Matrix): Origin and axes of the group, the parts' median if None.

        Returns:
            bpy.types.Object | None: The group object.
        """
        if not objects_to_group:
            return None

        objects_list = []
        for obj in objects_to_group:
            if Group.PROP_GROUP_ID in obj:
                return None
            if Group.PROP_OBJECT_ID in obj:
                objects_list.append(obj)

        if not objects_list:
            return None

        if target_matrix is not None:
            clean_matrix = target_matrix.copy()
        else:
            clean_matrix = Matrix.Identity(4)
            total_location = Vector((0.0, 0.0, 0.0))
            for obj in objects_list:
                total_location += obj.matrix_world.translation
            clean_matrix.translation = total_location / len(objects_list)

        merged_object = blend_utils.merge_objects(objects_list, Group.MERGED_NAME)
        if merged_object is None:
            return None

        merged_object[Group.PROP_ORIGIN_MATRIX] = (
            Group.matrix_to_str(target_matrix) if target_matrix is not None else ""
        )

        prev_position = merged_object.matrix_world.translation.copy()

        # move the geometry the opposite way, so the parts don't move when the origin does
        merged_object.data.transform(clean_matrix.inverted() @ merged_object.matrix_world)
        merged_object.matrix_world = clean_matrix
        merged_object.data.update()

        origin_difference = prev_position - merged_object.matrix_world.translation
        merged_object[Group.PROP_ORIGIN_OFFSET] = (
            merged_object.matrix_world.to_3x3().inverted() @ origin_difference
        )

        merged_object[Group.PROP_CHILD_CACHE] = Group.cache_relative_matrices(merged_object, objects_list)
        merged_object[Group.PROP_GROUP_ID] = str(uuid.uuid4())
        merged_object[Group.PROP_PART_COUNT] = len(objects_list)
        merged_object[Group.PROP_IS_MIRROR] = False

        # only the merged parts, anything else that was selected stays
        # one batch, a remove() per object re-syncs the whole scene each time
        bpy.data.batch_remove(objects_list)

        return merged_object

    @staticmethod
    def _get_child_user_data(parent_obj, cache_data):
        # a UserData on the group itself comes from recolouring it, and wins over the parts
        master_user_data = parent_obj.get(Group.PROP_USER_DATA) if parent_obj is not None else None
        if master_user_data is not None:
            return master_user_data
        return cache_data.get(Group.PROP_USER_DATA, 0)

    @staticmethod
    def _build_children(builder, cached_child_data, origin_matrix, parent_obj=None):
        restored_objects = []
        for cache_data in cached_child_data.values():
            matrix_local_data = cache_data.get(Group.PROP_MATRIX_LOCAL)
            if not matrix_local_data:
                continue

            new_part = builder.add_part(
                cache_data[Group.PROP_OBJECT_ID],
                user_data=Group._get_child_user_data(parent_obj, cache_data),
            )
            if new_part is None or not hasattr(new_part, "object"):
                continue

            new_obj = new_part.object
            new_obj[Group.PROP_TIMESTAMP] = str(cache_data.get(Group.PROP_TIMESTAMP, int(time.time())))
            if Group.PROP_MESSAGE in cache_data:
                new_obj[Group.PROP_MESSAGE] = cache_data[Group.PROP_MESSAGE]

            new_obj.matrix_world = origin_matrix @ Matrix(matrix_local_data)
            restored_objects.append(new_obj)
        return restored_objects

    @staticmethod
    def ungroup_objects(builder, parent_obj):
        """Rebuild a group's parts in place and remove the group.

        Returns:
            list | None: The restored parts.
        """
        cached_child_data, _ = Group.extract_cached_data(parent_obj)
        if not cached_child_data:
            return None

        restored_objects = Group._build_children(
            builder, cached_child_data, parent_obj.matrix_world.copy(), parent_obj
        )
        bpy.data.objects.remove(parent_obj, do_unlink=True)
        return restored_objects

    @staticmethod
    def deserialise_to_group(builder, child_cache, origin_matrix=None):
        """Build a group from a child cache string."""
        restored_objects = Group.deserialise_to_objects(builder, child_cache, origin_matrix)
        if not restored_objects:
            return None
        return Group.group_objects(restored_objects, origin_matrix or Group.get_default_origin_matrix())

    @staticmethod
    def deserialise_to_objects(builder, child_cache, origin_matrix=None):
        """Build the parts of a child cache string, without grouping them."""
        if origin_matrix is None:
            origin_matrix = Group.get_default_origin_matrix()

        try:
            cached_child_data = json.loads(child_cache)
        except (TypeError, ValueError) as error:
            print("Error reading group cache ", error)
            return None

        return Group._build_children(builder, cached_child_data, origin_matrix)

    # Serialising ---
    @staticmethod
    def serialise(parent_obj):
        """The group's parts as NMS object data.

        Returns:
            list | None
        """
        cached_child_data, _ = Group.extract_cached_data(parent_obj)
        if not cached_child_data:
            return None

        serialized_objects = []
        for cache_data in cached_child_data.values():
            matrix_world = Group.restore_matrix_world(parent_obj, cache_data)
            if matrix_world is None:
                continue

            pos, up, at = Group.extract_pos_up_at(matrix_world)
            data = {
                Part.PROP_TIMESTAMP: int(cache_data.get(Group.PROP_TIMESTAMP, int(time.time()))),
                Part.PROP_OBJECT_ID: "^{0}".format(cache_data[Group.PROP_OBJECT_ID]),
                Part.PROP_USER_DATA: int(Group._get_child_user_data(parent_obj, cache_data)),
                Part.PROP_POSITION: list(pos),
                Part.PROP_UP: list(up),
                Part.PROP_AT: list(at),
            }
            if Group.PROP_MESSAGE in cache_data:
                data[Part.PROP_MESSAGE] = cache_data[Group.PROP_MESSAGE]

            serialized_objects.append(data)

        return serialized_objects

    @staticmethod
    def restore_matrix_world(parent_obj, child_cache_data):
        matrix_local_data = child_cache_data.get(Group.PROP_MATRIX_LOCAL)
        if not matrix_local_data:
            return None
        return parent_obj.matrix_world @ Matrix(matrix_local_data)

    @staticmethod
    def extract_pos_up_at(matrix_world):
        # bring the matrix from blender Z up space into NMS Y up space
        world_matrix_offset = mathutils.Matrix.Rotation(math.radians(-90.0), 4, "X") @ matrix_world
        pos = world_matrix_offset.translation
        up = world_matrix_offset.col[1].to_3d()
        at = world_matrix_offset.col[2].to_3d()
        return pos, up, at

    # Colour ---
    @staticmethod
    def apply_colour(group_obj, colour_index, material_index):
        """Recolour the whole group, it becomes the colour of every part in it."""
        new_material = material.assign_material(group_obj, colour_index, material_index)
        # a merged group has one slot per colour it was made from
        for index in range(len(group_obj.data.materials)):
            group_obj.data.materials[index] = new_material

    # Lookups ---
    @staticmethod
    def get_all_groups():
        groups = []
        for obj in bpy.context.view_layer.objects:
            try:
                if obj is not None and Group.PROP_GROUP_ID in obj:
                    groups.append(obj)
            except ReferenceError:
                continue
        return groups

    @staticmethod
    def find_mirror_group(target, groups_list=None):
        """The first group sharing target's GroupID from the other side of the mirror."""
        existing_groups = Group.get_all_groups() if groups_list is None else groups_list
        is_target_mirror = target.get(Group.PROP_IS_MIRROR, False)

        for obj in existing_groups:
            try:
                if obj is None or Group.PROP_GROUP_ID not in obj or obj.name == target.name:
                    continue
                if obj[Group.PROP_GROUP_ID] != target[Group.PROP_GROUP_ID]:
                    continue
                if obj.get(Group.PROP_IS_MIRROR, False) != is_target_mirror:
                    return obj
            except ReferenceError:
                continue
        return None

    # Matrices ---
    @staticmethod
    def matrix_to_str(matrix):
        return json.dumps([list(row) for row in matrix])

    @staticmethod
    def str_to_matrix(json_string):
        if not json_string:
            return None
        try:
            return Matrix(json.loads(json_string))
        except (TypeError, ValueError):
            print("error decoding json string : ", json_string)
            return None

    @staticmethod
    def extract_origin_matrix(group_obj):
        return Group.str_to_matrix(group_obj.get(Group.PROP_ORIGIN_MATRIX))

    @staticmethod
    def get_default_origin_matrix():
        return Matrix.Identity(4)

    # Mirroring ---
    @staticmethod
    def mirror_cache_data(child_cache, origin_matrix, axis, center):
        """Mirror a group's cached parts without building any of them.

        Each part is mirrored the way the mirror tool mirrors a part, and swapped
        for its mirror twin when there is one.

        Returns:
            tuple: (new child cache json, new origin matrix) or (None, None).
        """
        try:
            cached_child_data = json.loads(child_cache)
        except (TypeError, ValueError) as error:
            print("Error mirroring group cache: ", error)
            return None, None

        if origin_matrix is None:
            origin_matrix = Group.get_default_origin_matrix()

        new_origin = mirror_utils.mirror_matrix_world_universal(None, origin_matrix, axis, center)
        new_origin_inverted = new_origin.inverted()

        new_child_cache = {}
        for child_name, cache_data in cached_child_data.items():
            matrix_local_data = cache_data.get(Group.PROP_MATRIX_LOCAL)
            if not matrix_local_data:
                continue

            new_cache_data = dict(cache_data)
            object_id = cache_data[Group.PROP_OBJECT_ID]
            mirror_part_id = Part.get_mirror_part_id(object_id)

            # corrections are keyed on the id before the swap, same as the mirror tool
            matrix_world = mirror_utils.mirror_matrix_world_universal(
                object_id, origin_matrix @ Matrix(matrix_local_data), axis, center
            )

            if mirror_part_id in nice_name_dictionary:
                new_cache_data[Group.PROP_OBJECT_ID] = mirror_part_id
            new_cache_data[Group.PROP_MATRIX_LOCAL] = [
                list(row) for row in new_origin_inverted @ matrix_world
            ]
            new_child_cache[child_name] = new_cache_data

        return json.dumps(new_child_cache), new_origin

    @staticmethod
    def mirror_group(builder, group_obj, axis, center, auto_duplicate=False, existing_groups=None):
        """Mirror a group, reusing an existing mirror twin's mesh when there is one.

        Returns:
            bpy.types.Object | None: The mirrored group.
        """
        is_target_mirror = group_obj.get(Group.PROP_IS_MIRROR, False)
        group_id = group_obj[Group.PROP_GROUP_ID]
        new_matrix_world = mirror_utils.mirror_matrix_world_universal(
            None, group_obj.matrix_world.copy(), axis, center
        )

        found_match = Group.find_mirror_group(group_obj, existing_groups)
        if found_match is not None:
            # a copy of the twin is the mirror already, no parts need building
            mirrored_group = blend_utils.duplicate_part(found_match)
            mirrored_group.matrix_world = new_matrix_world
        else:
            new_child_cache, new_origin = Group.mirror_cache_data(
                group_obj[Group.PROP_CHILD_CACHE], group_obj.matrix_world.copy(), axis, center
            )
            if new_child_cache is None:
                return None
            mirrored_group = Group.deserialise_to_group(builder, new_child_cache, new_origin)
            if mirrored_group is None:
                return None
            mirrored_group[Group.PROP_GROUP_ID] = group_id
            mirrored_group[Group.PROP_IS_MIRROR] = not is_target_mirror
            if Group.PROP_USER_DATA in group_obj:
                mirrored_group[Group.PROP_USER_DATA] = group_obj[Group.PROP_USER_DATA]

        if not auto_duplicate:
            group_name = group_obj.name
            bpy.data.objects.remove(group_obj, do_unlink=True)
            mirrored_group.name = group_name

        return mirrored_group
