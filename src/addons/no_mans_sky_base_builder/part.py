import math
import os
import time
from copy import copy

import bpy
import mathutils
import no_mans_sky_base_builder.utils.blend_utils as blend_utils
import no_mans_sky_base_builder.utils.material as material
import no_mans_sky_base_builder.utils.python as python_utils


class Part(object):

    DEFAULT_USER_DATA = 0
    DEFAULT_BELONGS_TO_PRESET = False
    FILE_PATH = os.path.dirname(os.path.realpath(__file__))
    SNAP_MATRIX_JSON = os.path.join(FILE_PATH, "resources", "snapping_info.json")
    SNAP_PAIR_JSON = os.path.join(FILE_PATH,  "resources", "snapping_pairs.json")

    SNAP_MATRIX_DICTIONARY = python_utils.load_dictionary(SNAP_MATRIX_JSON)
    SNAP_PAIR_DICTIONARY = python_utils.load_dictionary(SNAP_PAIR_JSON)

    SNAP_CACHE = {}
    
    def __init__(
            self,
            object_id=None,
            bpy_object=None,
            builder_object=None,
            user_data=None,
            build_rigs=False):
        """Part __init__
        
        Args:
            object_id (str): The object ID we wish to create.
            bpy_object (bpy.data.object): An existing part we can reconstruct
                the class from.
            builder_object (Builder): The "parent" class for managing the NMS
                scene.
        """
        # Assign private variables.
        self.__builder_object = builder_object
        self.build_rigs = build_rigs
        user_data = user_data or self.DEFAULT_USER_DATA
       
        # Decide whether or not to retrieve from the scene
        # or create a new one.
        if bpy_object:
            self.__object = bpy_object
            object_id = bpy_object["ObjectID"]
        else:
            # Create new object.
            self.__object = self.retrieve_object_from_id(object_id)
            # Set properties.
            self.__object.hide_select = False
            self.object_id = object_id
            self.parent = None
            self.time_stamp = str(int(time.time()))
            self.belongs_to_preset = self.DEFAULT_BELONGS_TO_PRESET
            self.order = len(bpy.data.objects)
            # Assign material.
            material.assign_material(self.__object, user_data)
            # Set to origin.
            self.reset_transforms()

        # Place the blender item in the builder cache.
        builder_object.add_to_part_cache(object_id, self.__object)

        self.snap_id = object_id

    # Properties ---
    @property
    def name(self):
        return self.__object.name

    @name.setter
    def name(self, value):
        self.__object.name = value

    @property
    def object(self):
        return self.__object

    @object.setter
    def object(self, value):
        self.__object = value
        
    @property
    def location(self):
        return self.__object.location

    @location.setter
    def location(self, value):
        self.__object.location = value

    @property
    def rotation(self):
        return self.__object.euler_rotation

    @rotation.setter
    def rotation(self, value):
        self.__object.rotation_euler = value

    @property
    def scale(self):
        return self.__object.scale
    
    @scale.setter
    def scale(self, value):
        self.__object.scale = value

    @property
    def builder(self):
        return self.__builder_object

    @property
    def matrix_world(self):
        return self.__object.matrix_world

    @matrix_world.setter
    def matrix_world(self, value):
        self.__object.matrix_world = value

    @property
    def order(self):
        return self.__object["order"]

    @order.setter
    def order(self, value):
        self.__object["order"] = value
        
    @property
    def object_id(self):
        return self.__object["ObjectID"]

    @object_id.setter
    def object_id(self, value):
        self.__object["ObjectID"] = value.replace("^", "")

    @property
    def snap_id(self):
        return self.__object["SnapID"]

    @snap_id.setter
    def snap_id(self, value):
        self.__object["SnapID"] = value.replace("^", "")

    @property
    def object_id_format(self):
        return "^{0}".format(self.object_id)

    @property
    def time_stamp(self):
        return self.__object["Timestamp"]

    @time_stamp.setter
    def time_stamp(self, value):
        self.__object["Timestamp"] = value

    @property
    def user_data(self):
        return self.__object["UserData"]
    
    @user_data.setter
    def user_data(self, value):
        self.__object["UserData"] = str(value)

    @property
    def belongs_to_preset(self):
        return self.__object["belongs_to_preset"]

    @belongs_to_preset.setter
    def belongs_to_preset(self, value):
        self.__object["belongs_to_preset"] = value

    @property
    def hide_select(self):
        return self.__object.hide_select

    @hide_select.setter
    def hide_select(self, value):
        self.__object.hide_select = value

    @property
    def snapped_to(self):
        return self.__object["snapped_to"]

    @snapped_to.setter
    def snapped_to(self, value):
        self.__object["snapped_to"] = value

    # Methods ---
    def reset_transforms(self):
        """Reset transformations to default."""
        # Lock all translations and rotations.
        self.__object.lock_location = [False, False, False]
        self.__object.lock_rotation = [False, False, False]
        self.__object.lock_scale = [False, False, False]

        self.location = [0.0, 0.0, 0.0]
        self.rotation = [1.5708, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]

    def remove_constraints(self):
        # Remove any constraints from the duplication.
        for c in self.__object.constraints:
            self.__object.constraints.remove(c)

        # Remove any drivers from the duplication.
        anim_data = self.__object.animation_data
        if anim_data:
            drivers_data = anim_data.drivers
            for dr in drivers_data:  
                self.__object.driver_remove(dr.data_path, -1)


    def duplicate(self):
        """Duplicate the part and return it."""
        # Create new object as whole.
        new_object = self.__object.copy()
        # Transfer a copy of the mesh and material.
        new_object.data = self.__object.data.copy()

        if self.__object.active_material:
            new_object.active_material = self.__object.active_material.copy()

        # Clear Parent
        if new_object.parent:
            new_object.parent = None
            new_object.matrix_parent_inverse = mathutils.Matrix.Identity(4)

        # Convert to Base Builder Object.
        new_object = self.builder.get_builder_object_from_bpy_object(
            new_object
        )
        new_object.remove_constraints()
        return new_object

    def select(self, value=True, add=False):
        blend_utils.select(self.object)
    
    @property
    def parent(self):
        return self.__object.parent

    @parent.setter
    def parent(self, bpy_object):
        """Parent this to another blender object.
        
        Whilst maintaining the offset.
        """
        if bpy_object:
            self.__object.parent = bpy_object
            self.__object.matrix_parent_inverse = bpy_object.matrix_world.inverted()

    def add_to_scene(self):
        blend_utils.add_to_scene(self.object)

    def retrieve_object_from_id(self, object_id):
        """Given an ID. Find the best way to create a new one.
        
        As loading OBJ can be resource and time intensive. We can figure ways
        of caching and duplicating existing items via th Builder class.

        Method Priority.
        - If the object already exists in the builder cache, we can just
            dupliciate it.
        - If it doesn't exist in the cache, find the obj path.
        - If the obj path doesn't exist, just create a cube.
        """
        # Duplicate existing.
        existing_object = self.builder.find_object_by_id(object_id)
        if existing_object:
            duped = existing_object.duplicate()
            duped = duped.object
            blend_utils.add_to_scene(duped)
            return duped
        
        # Locate OBJ.
        obj_path = self.builder.get_obj_path(object_id)
        # If it exists, import the obj.
        if obj_path and os.path.isfile(obj_path):
            prev_objects_capture = [x.name for x in bpy.data.objects]
            bpy.ops.import_scene.obj(filepath=obj_path, split_mode="OFF")
            new_objects_capture = [x.name for x in bpy.data.objects]
            new_objects = [x for x in new_objects_capture if x not in prev_objects_capture]
            item = bpy.data.objects[new_objects[0]]
            # for convenience if saving obj/mtl files, delete any imported materials
            item.data.materials.clear()
            item.select_set(False)
            blend_utils.add_to_scene(item)
            return item

        # Create cube.
        bpy.ops.mesh.primitive_cube_add()
        item = bpy.data.objects[bpy.context.object.name]
        item.name = object_id
        blend_utils.add_to_scene(item)
        return item

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
            "ObjectID": self.object_id_format,
            "Position": [pos[0], pos[1], pos[2]],
            "Up": [up[0], up[1], up[2]],
            "At": [at[0], at[1], at[2]],
            "Timestamp": int(self.time_stamp),
            "UserData": int(self.user_data)
        }

    # Class Methods ---
    @classmethod
    def deserialise_from_object(cls, bpy_object, builder_object):
        """Reconstruct the class using an existing Blender object."""
        part = cls(bpy_object=bpy_object, builder_object=builder_object)
        return part

    @classmethod
    def deserialise_from_data(cls, data, builder_object, build_rigs=True, *args, **kwargs):
        """Reconstruct the class using an a data.
        
        Data usually comes from NMS or the serialise method.
        """
        # Create object based on the ID.
        object_id = data["ObjectID"].replace("^", "")
        user_data = data.get("UserData", 0)
        part = cls(
            object_id=object_id,
            builder_object=builder_object,
            build_rigs=build_rigs,
            user_data=user_data
        )
        # Get location data.
        pos = data.get("Position", [0.0, 0.0, 0.0])
        up = data.get("Up", [0.0, 0.0, 0.0])
        at = data.get("At", [0.0, 0.0, 0.0])
        # Set part position.
        world_matrix = cls.create_matrix_from_vectors(pos, up, at)
        part.matrix_world = world_matrix
        part.rotation = world_matrix.to_euler()
        # Apply metadata
        part.time_stamp = str(data.get("Timestamp", int(time.time())))
        part.user_data = data.get("UserData", 0)
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

    # Snapping Methods ---
    def get_snap_points(self):
        """Get the snap points related to this part."""
        # First find the snap group the part belonds to.
        use_group = self.get_snap_group()
        # Get nothing if it doesn't belong anywhere.
        if not use_group:
            return

        # Further validation.
        if "snap_points" not in self.SNAP_MATRIX_DICTIONARY[use_group]:
            return
        
        # Get the snap points from the dictionary.
        return self.SNAP_MATRIX_DICTIONARY[use_group]["snap_points"]

    def get_snap_group(self):
        """Search through the grouping dictionary and return the snap group.
        
        Args:
            part_id (str): The ID of the building part.
        """
        for group, value in self.SNAP_MATRIX_DICTIONARY.items():
            parts = value["parts"]
            if self.object_id in parts:
                return group

    def get_snap_pair_options(self, target_item):
        """Get the compatible snap points

        Args:
            target_item (part.Part): 
        """
        # Get Groups.
        target_group = target_item.get_snap_group()
        source_group = self.get_snap_group()

        # If no target and no source then we don't do anything.
        if not target_group and not source_group:
            return None

        # Get Pairing.
        if target_group in self.SNAP_PAIR_DICTIONARY:
            snapping_dictionary = self.SNAP_PAIR_DICTIONARY[target_group]
            if source_group in snapping_dictionary:
                return snapping_dictionary[source_group]

    def snap_to(
            self,
            target,
            next_target=False,
            prev_target=False,
            next_source=False,
            prev_source=False):
        """Snap this item to the specified builder object.

        Args:
            target (part.Part): The item to snap to.
            next_target (bool): Cycle to the next target snap point.
            prev_target (bool): Cycle to the prev target snap point.
            next_source (bool): Cycle to the next source snap point.
            prev_source (bool): Cycle to the prev source snap point.
        """
        # For preset targets, just snap them together.
        if hasattr(target, "control"):
            mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
            use_matrix = copy(target.matrix_world) @ mat_rot
            self.matrix_world = use_matrix
            self.select()
            return

        # Check for Snap IDs
        target_snap_check = "SnapID" in target.object
        source_snap_check = "SnapID" in self.object
        if not target_snap_check or not source_snap_check:
            return False

        # First and foremost, just move the source on top of the target.
        self.matrix_world = copy(target.matrix_world)
        # Set the snapped to property so it remembers it without selection.
        self.snapped_to = target.name
        self.select()

        # Get Pairing options.
        snap_pairing_options = self.get_snap_pair_options(target)
        # If no snap details are avaialbe then don't bother.
        if not snap_pairing_options:
            return False

        # Get pair options.
        target_pairing_options = [
            part.strip() for part in snap_pairing_options[0].split(",")
        ]
        source_pairing_options = [
            part.strip() for part in snap_pairing_options[1].split(",")
        ]

        # Get the per item reference.
        target_item_snap_reference = self.SNAP_CACHE.get(target.name, {})
        # Find corresponding dict in snap reference.
        target_local_matrix_datas = target.get_snap_points()
        if target_local_matrix_datas:
            # Get the default target.
            default_target_key = target_pairing_options[0]
            target_key = target_item_snap_reference.get(
                "target",
                default_target_key
            )

            # If the previous key is not in the available options
            # revert to default.
            if target_key not in target_pairing_options:
                target_key = default_target_key

            if next_target:
                target_key = python_utils.get_adjacent_dict_key(
                    target_pairing_options,
                    target_key,
                    step="next"
                )

            if prev_target:
                target_key = python_utils.get_adjacent_dict_key(
                    target_pairing_options,
                    target_key,
                    step="prev"
                )

        # Get the per item reference.
        source_item_snap_reference = self.SNAP_CACHE.get(self.name, {})

        # Find corresponding dict.
        source_local_matrix_datas = self.get_snap_points()
        if source_local_matrix_datas:
            default_source_key = source_pairing_options[0]

            # If the source and target are the same, the source key can be
            # the opposite of target.
            if self.snap_id == target.snap_id:
                default_source_key = target_local_matrix_datas[target_key].get(
                    "opposite", default_source_key
                )

            # Get the source key from the item reference, or use the default.
            if (self.snap_id == target.snap_id) and (prev_target or next_target):
                source_key = target_local_matrix_datas[target_key].get(
                    "opposite", default_source_key
                )
            else:
                source_key = source_item_snap_reference.get(
                    "source",
                    default_source_key
                )

            # If the previous key is not in the available options
            # revert to default.
            if source_key not in source_pairing_options:
                source_key = default_source_key

            if next_source:
                source_key = python_utils.get_adjacent_dict_key(
                    source_pairing_options,
                    source_key,
                    step="next"
                )

            if prev_source:
                source_key = python_utils.get_adjacent_dict_key(
                    source_pairing_options,
                    source_key,
                    step="prev"
                )
        
        # If no keys were found, don't snap.
        if not source_key and not target_key:
            return False
        
        # Snap-point to snap-point matrix maths.
        # As I've defined X to be always outward facing, we snap the rotated
        # matrix to the point.
        # s = source, t = target, o = local snap matrix.
        # [(s.so)^-1 * (t.to)] * [(s.so) * 180 rot-matrix * (s.so)^-1]

        # First Create a Flipped Y Matrix based on local offset.
        start_matrix = copy(self.matrix_world)
        start_matrix_inv = copy(self.matrix_world)
        start_matrix_inv.invert()
        offset_matrix = mathutils.Matrix(
            source_local_matrix_datas[source_key]["matrix"]
        )

        # Target Matrix
        target_matrix = copy(target.matrix_world)
        target_offset_matrix = mathutils.Matrix(
            target_local_matrix_datas[target_key]["matrix"]
        )

        # Calculate the location of the target matrix.
        target_snap_matrix = target_matrix @ target_offset_matrix

        # Calculate snap position.
        snap_matrix = start_matrix @ offset_matrix
        snap_matrix_inv = copy(snap_matrix)
        snap_matrix_inv.invert()

        # Rotate by 180 around Y at the origin.
        origin_matrix = snap_matrix_inv @ snap_matrix
        rotation_matrix = mathutils.Matrix.Rotation(
            math.radians(180.0),
            4,
            "Y"
        )
        origin_flipped_matrix = rotation_matrix @ origin_matrix
        flipped_snap_matrix = snap_matrix @ origin_flipped_matrix

        flipped_local_offset = start_matrix_inv @ flipped_snap_matrix

        # Diff between the two.
        flipped_local_offset.invert()
        target_location = target_snap_matrix @ flipped_local_offset

        # Set matrix, and then re-apply radian rotation for better accuracy.
        self.matrix_world = target_location
        self.rotation = target_location.to_euler()


        # Find the opposite source key and set it.
        next_target_key = target_key

        # If we are working with the same objects.
        next_target_key = source_local_matrix_datas[source_key].get(
            "opposite",
            None
        )

        # Update source item refernece.
        source_item_snap_reference["source"] = source_key
        source_item_snap_reference["target"] = next_target_key

        # Update target item reference.
        target_item_snap_reference["target"] = target_key

        # Update per item reference.
        self.SNAP_CACHE[self.name] = source_item_snap_reference
        self.SNAP_CACHE[target.name] = target_item_snap_reference

        return True

    def get_closest_snap_points(
            self,
            target,
            source_filter=None,
            target_filter=None):
        """Get the closest snap points of two objects.
        
        Args:
            target (part.Part): The object we are snapping on to.
            source_filter (str): A filter for the snap points being used.
            target_filter (str): A filter for the snap points being used.
        """
        source_matrices = self.get_snap_points()
        target_matrices = target.get_snap_points()
        
        lowest_source_key = None
        lowest_target_key = None
        lowest_distance = 9999999
        for source_key, source_info in source_matrices.items():
            # Check source filter.
            if source_filter and source_filter not in source_key:
                continue

            for target_key, target_info in target_matrices.items():
                # Check target filter.
                if target_filter and target_filter not in target_key:
                    continue
                
                # Find the distance and check if its lower then the one
                # stored.
                local_source_matrix = mathutils.Matrix(source_info["matrix"])
                local_target_matrix = mathutils.Matrix(target_info["matrix"])

                source_snap_matrix = self.matrix_world @ local_source_matrix
                target_snap_matrix = target.matrix_world @ local_target_matrix

                distance = blend_utils.get_distance_between(
                    source_snap_matrix, target_snap_matrix
                )
                if distance < lowest_distance:
                    lowest_distance = distance
                    lowest_source_key = source_key
                    lowest_target_key = target_key

        return lowest_source_key, lowest_target_key

    def get_matrix_from_key(self, key):
        """Get the matrix for a given item and the snap key."""
        # Get relavant snap information from item.
        snap_matrices = self.get_snap_points()
        # Validate key entry.
        if key not in snap_matrices:
            return None
        # Return matrix.
        return snap_matrices[key]["matrix"]

    def has_snap_point(self, filter=None):
        """Check for any matrix that would match the given filter."""
        # Get relavant snap information from item.
        snap_matrices = self.get_snap_points()
        # Validate key entry.
        for key, info in snap_matrices.items():
            if not filter or filter in key:
                return True
        return False

    def get_connected_snapped_objects(self, filter=None, include_lines=True):
        """Get all objects connected to the given snap category.
        
        Args:
            filter (str): A filter for the snap points being used.
        """
        source_matrices = self.get_snap_points()
        if filter is not None:
            source_matrices = { k: v for k, v in source_matrices.items() if filter in k }

        source_points = [self.matrix_world @ mathutils.Matrix(info["matrix"]) for k, info in source_matrices.items()]

        result = []
        if not source_points:
            return result

        for target in self.builder.get_all_parts(include_lines=include_lines):
            if target == self.object:
                continue

            target = self.builder.get_builder_object_from_bpy_object(target)
            snap_points = target.get_snap_points()
            if not snap_points:
                continue
            for target_key, target_info in snap_points.items():
                # Check target filter.
                if filter and filter not in target_key:
                    continue
                
                local_target_matrix = mathutils.Matrix(target_info["matrix"])
                target_snap_matrix = target.matrix_world @ local_target_matrix

                found = False
                for source_snap_matrix in source_points:
                    distance = blend_utils.get_distance_between(
                        source_snap_matrix, target_snap_matrix
                    )
                    if distance < 0.050:  # XXX what is actual game threshold?
                        found = True
                        break
                if found:
                    result.append(target)
                    break

        return result

