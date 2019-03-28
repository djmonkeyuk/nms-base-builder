# Header Info ---
bl_info = {
    "name": "No Mans Sky Base Builder",
    "description": "A tool to assist with base building in No Mans Sky",
    "author": "Charlie Banks",
    "version": (0, 9, 0),
    "blender": (2, 70, 0),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "",
    "tracker_url": "",
    "category": "Game Engine"
}
# Imports ---
import json
import math
import os
from collections import OrderedDict
from decimal import Decimal, getcontext
from copy import copy, deepcopy
from functools import partial
import bpy.utils.previews
import bpy
import bpy.utils
import mathutils
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)
from bpy.types import Operator, Panel, PropertyGroup

# File Paths ---
file_path = os.path.dirname(os.path.realpath(__file__))
user_path = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
model_path = os.path.join(file_path, "models")
preset_path = os.path.join(user_path, "presets")

for user_data_path in [user_path, preset_path]:
    if not os.path.exists(user_data_path):
        os.makedirs(user_data_path)

# Load Auto Snap Dictionary ---
snap_matrix_json = os.path.join(file_path, "snapping_info.json")
snap_pair_json = os.path.join(file_path, "snapping_pairs.json")
nice_names_json = os.path.join(file_path, "nice_names.json")
colours_json = os.path.join(file_path, "colours.json")

# Keep track of snap keys.
global per_item_snap_reference
per_item_snap_reference = {}

# Load in the external dictionaries.
global snap_matrix_dictionary
global snap_pair_dictionary
snap_matrix_dictionary = {}
snap_pair_dictionary = {}

with open(snap_matrix_json, "r") as stream:
    snap_matrix_dictionary = json.load(stream)
with open(snap_pair_json, "r") as stream:
    snap_pair_dictionary = json.load(stream)

# Colours
global colours_dictionary
colours_dictionary = {}
with open(colours_json, "r") as stream:
    colours_dictionary = json.load(stream)

# Nice Names
global nice_names_dictionary
nice_names_dictionary = {}
with open(nice_names_json, "r") as stream:
    nice_names_dictionary = json.load(stream)

# Utility Methods ---
def get_direction_vector(matrix, direction_matrix = None):
    """Calculate direction matrices."""
    if direction_matrix == "up":
        return [matrix[0][1], matrix[1][1], matrix[2][1]]
    elif direction_matrix == "at":
        return [matrix[0][2], matrix[1][2], matrix[2][2]]
    return [0, 0, 0]
    

# Category Methods ---
def get_categories():
    """Get the list of categories."""
    return os.listdir(model_path)


# Part Methods ---
def get_nice_name(part_id):
    remove_tags = ["BUILD", "BUILD_"]
    nice_name = part_id
    for tag in remove_tags:
        nice_name = nice_name.replace(tag, "")
    nice_name = nice_name.title()
    return nice_names_dictionary.get(part_id, nice_name)

def get_parts_from_category(category):
    """Get a list of parts belonging to a category."""
    category_path = os.path.join(model_path, category)
    if not os.path.exists(category_path):
        raise RuntimeError(category + " does not exist.")
    
    return sorted(
        [part.split(".obj")[0] for part in os.listdir(category_path) if part.endswith(".obj")],
        key=get_nice_name
    )


def get_category_from_part(part):
    """Get the category of a part."""
    check_categories = get_categories()
    for category in check_categories:
        if part in get_parts_from_category(category):
            return category


def get_obj_path(part):
    """Get the path to the OBJ file from a part."""
    category = get_category_from_part(part)
    if not category:
        return
    obj_path = os.path.join(model_path, category, part+".obj")
    return obj_path


def import_obj(part):
    """Given a part, get the obj path and call blender API to import."""
    obj_part = get_obj_path(part)
    imported_object = bpy.ops.import_scene.obj(filepath=obj_part, split_mode="OFF")
    obj_object = bpy.context.selected_objects[0] 
    return obj_object


def delete_preset(preset_id):
    """Remove preset."""
    preset_path = get_preset_path(preset_id)
    if os.path.isfile(preset_path):
        os.remove(preset_path)


def build_item(
        part,
        timestamp=1539023700,
        userdata=0,
        position=[0, 0, 0],
        up_vec=[0, 1, 0],
        at_vec=[0, 0, 1],
        is_preset=False,
        material="white",
        auto_snap=False):
    """Build a part given a set of paremeters.
    
    This is they main function of the program for building.

    Args:
        part (str): The part ID.
        timestamp (int): The timestamp of build (this should go away and compute automatically).
        user_data(int): This determines the colour of a part, default is 0 for now.
        position (vector): The location of the part.
        up_vec(vector): The up vector for the part orientation.
        at_vec(vector): The aim vector for the part orientation.
        is_preset(bool): Determine if this part belongs to a preset or standalone.
    """
    # Get Current Selection
    current_selection = None
    current_world_matrix = None
    if bpy.context.selected_objects:
        current_selection = bpy.context.selected_objects[0]
        current_world_matrix = current_selection.matrix_world

    # Get the obj path.
    obj_path = get_obj_path(part) or ""
    # If it exists, import the obj.
    if os.path.isfile(obj_path):
        item = import_obj(part)
    else:
        # If not then create a blender cube.
        item = bpy.ops.mesh.primitive_cube_add()
        item = bpy.context.object
        item.name = part

    # Lock Scale
    item.lock_scale[0] = True
    item.lock_scale[1] = True
    item.lock_scale[2] = True
    # Lock Everything if base flag
    if part == "BASE_FLAG":
        item.lock_location[0] = True
        item.lock_location[1] = True
        item.lock_location[2] = True
        item.lock_rotation[0] = True
        item.lock_rotation[1] = True
        item.lock_rotation[2] = True
    # Add custom attributes.
    item["objectID"] = part
    item["Timestamp"] = timestamp
    item["is_preset"] = is_preset
    # Apply Colour
    if is_preset:
        assign_preset_material(item, userdata)
    else:
        assign_material(item, userdata)

    # Position.
    item.location = position
    # Rotation
    up_vec = mathutils.Vector(up_vec)
    at_vec = mathutils.Vector(at_vec)
    
    # Calculate a normal using the up vector
    right_vector = at_vec.cross(up_vec)
    new_up_vec = right_vector.cross(at_vec)
    # Flip the right vector.
    right_vector *= -1
    # Construct a world matrix for the item.
    mat = mathutils.Matrix(
        [
            [right_vector[0], new_up_vec[0] , at_vec[0],  position[0]],
            [right_vector[1], new_up_vec[1] , at_vec[1],  position[1]],
            [right_vector[2], new_up_vec[2] , at_vec[2],  position[2]],
            [0.0,             0.0,            0.0,        1.0        ]
        ]
    )
    # Create a rotation matrix that turns the whole thing 90 degrees at the origin.
    # This is to compensate blender's Z up axis.
    mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    mat = mat_rot * mat
    # Place the item in world space.
    item.matrix_world = mat

    # Auto Snap
    if auto_snap and current_selection:
        # Set selection to be snap friendly.
        bpy.ops.object.select_all(action='DESELECT') 
        current_selection.select = True
        item.select = True
        bpy.context.scene.objects.active = item

        snap_state = snap_objects(item, current_selection)

        # If no snap was done, deselect the old item.
        if not snap_state:
            current_selection.select= False



    return item


# Snap Methods ---
def get_snap_matrices_from_group(group):
    global snap_matrix_dictionary
    if group in snap_matrix_dictionary:
        if "snap_points" in snap_matrix_dictionary[group]:
            print (snap_matrix_dictionary[group]["snap_points"])
            return snap_matrix_dictionary[group]["snap_points"]

def get_snap_group_from_part(part_id):
    """Search through the grouping dictionary and return the snap group.
    
    Args:
        part_id (str): The ID of the building part.
    """
    global snap_matrix_dictionary
    for group, value in snap_matrix_dictionary.items():
        parts = value["parts"]
        if part_id in parts:
            return group

def get_snap_pair_options(target_item_id, source_item_id):
    global snap_pair_dictionary
    # Get Groups.
    target_group = get_snap_group_from_part(target_item_id)
    source_group = get_snap_group_from_part(source_item_id)
    
    if not target_group and not source_group:
        return None

    # Get Pairing.
    if target_group in snap_pair_dictionary:
        snapping_dictionary = snap_pair_dictionary[target_group]
        if source_group in snapping_dictionary:
            return snapping_dictionary[source_group]

def cycle_keys(data, current, step="next"):
    # Sort the keys by the order sub-key.
    keys = data
    current_index = 0
    if current in keys:
        current_index = keys.index(current)
    if step == "next":
        next_index = current_index + 1
    elif step == "prev":
        next_index = current_index - 1
    
    if next_index > len(keys) - 1:
        next_index = 0

    if next_index < 0:
        next_index = len(keys) - 1

    return keys[next_index]

def snap_objects(
        source, target,
        next_source=False,
        prev_source=False,
        next_target=False,
        prev_target=False):
    """Given a source and a target, snap one to the other."""
    global per_item_snap_reference
    
    # Get Current Selection Object Type.
    source_key = None
    target_key = None

    if "objectID" not in target:
        return False

    if "objectID" not in source:
        return False
    
    # If anything, move the item to the target.
    source.matrix_world = copy(target.matrix_world)
    
    # Get Pairing options.
    snap_pairing_options = get_snap_pair_options(target["objectID"], source["objectID"])
    # IF no snap details are avaialbe then don't bother.
    if not snap_pairing_options:
        return False

    target_pairing_options = [part.strip() for part in snap_pairing_options[0].split(",")]
    source_pairing_options = [part.strip() for part in snap_pairing_options[1].split(",")]

    # Get the per item reference.
    target_item_snap_reference = per_item_snap_reference.get(target.name, {})
    # Get the target item type.
    target_id = target["objectID"]
    # Find corresponding dict in snap reference.
    target_snap_group = get_snap_group_from_part(target_id)
    target_local_matrix_datas = get_snap_matrices_from_group(target_snap_group)
    if target_local_matrix_datas:
        # Get the default target.
        default_target_key = target_pairing_options[0]
        target_key = target_item_snap_reference.get("target", default_target_key)

        # If the previous key is not in the available options, revert to default.
        if target_key not in target_pairing_options:
            target_key = default_target_key

        if next_target:
            target_key = cycle_keys(
                target_pairing_options,
                target_key,
                step="next",
            )

        if prev_target:
            target_key = cycle_keys(
                target_pairing_options,
                target_key,
                step="prev",
            )

    # Get the per item reference.
    source_item_snap_reference = per_item_snap_reference.get(source.name, {})
    # Get the source type.
    source_id = source["objectID"]
    # Find corresponding dict.
    source_snap_group = get_snap_group_from_part(source_id)
    source_local_matrix_datas = get_snap_matrices_from_group(source_snap_group)
    if source_local_matrix_datas:
        default_source_key = source_pairing_options[0]

        # If the source and target are the same, the source key can be the opposite of target.
        if source_id == target_id:
            default_source_key = target_local_matrix_datas[target_key].get("opposite", default_source_key)

        # Get the source key from the item reference, or use the default.
        if (source_id == target_id) and (prev_target or next_target):
            source_key = target_local_matrix_datas[target_key].get("opposite", default_source_key)
        else:
            source_key = source_item_snap_reference.get("source", default_source_key)

        # If the previous key is not in the available options, revert to default.
        if source_key not in source_pairing_options:
            source_key = default_source_key

        if next_source:
            source_key = cycle_keys(
                source_pairing_options,
                source_key,
                step="next",
            )

        if prev_source:
            source_key = cycle_keys(
                source_pairing_options,
                source_key,
                step="prev",
            )

    if source_key and target_key:
        # Snap-point to snap-point matrix maths.
        # As I've defined X to be always outward facing, we snap the rotated
        # matrix to the point.
        # s = source, t = target, o = local snap matrix.
        # [(s.so)^-1 * (t.to)] * [(s.so) * 180 rot-matrix * (s.so)^-1]
        
        # First Create a Flipped Y Matrix based on local offset.
        start_matrix = copy(source.matrix_world)
        start_matrix_inv = copy(source.matrix_world)
        start_matrix_inv.invert()
        offset_matrix = mathutils.Matrix(source_local_matrix_datas[source_key]["matrix"])

        # Target Matrix
        target_matrix = copy(target.matrix_world)
        target_offset_matrix = mathutils.Matrix(target_local_matrix_datas[target_key]["matrix"])

        # Calculate the location of the target matrix.
        target_snap_matrix = target_matrix * target_offset_matrix

        # Calculate snap position.
        snap_matrix = start_matrix * offset_matrix
        snap_matrix_inv = copy(snap_matrix)
        snap_matrix_inv.invert()

        # Rotate by 180 around Y at the origin.
        origin_matrix = snap_matrix_inv * snap_matrix
        rotation_matrix = mathutils.Matrix.Rotation(math.radians(180.0), 4, "Y")
        origin_flipped_matrix = rotation_matrix * origin_matrix
        flipped_snap_matrix = snap_matrix * origin_flipped_matrix
        
        flipped_local_offset =  start_matrix_inv * flipped_snap_matrix

        # Diff between the two.
        flipped_local_offset.invert()
        target_location =  target_snap_matrix * flipped_local_offset

        source.matrix_world = target_location

        # Find the opposite source key and set it.
        next_source_key = source_key
        next_target_key = target_key
        
        # If we are working with the same objects.
        next_target_key = source_local_matrix_datas[source_key].get("opposite", None)

        # Update source item refernece.
        source_item_snap_reference["source"] = source_key
        source_item_snap_reference["target"] = next_target_key

        # Update target item reference.
        target_item_snap_reference["target"] = target_key
        
        # Update per item reference.
        per_item_snap_reference[source.name] = source_item_snap_reference
        per_item_snap_reference[target.name] = target_item_snap_reference
        return True

# Preset Methods ---
def get_preset_path(preset_id):
    return_preset_path = os.path.join(preset_path, preset_id+".json")
    return return_preset_path


def get_presets():
    """Get the list of categories."""
    return [preset.split(".")[0] for preset in os.listdir(preset_path)]


def build_preset(
        preset_id,
        build_control=False,
        position=None,
        up=None,
        at=None,
        material="preset"):
    preset_json = get_preset_path(preset_id)
    data = {}
    with open(preset_json, "r") as stream:
        data = json.load(stream)

    if "Objects" in data:
        parts = []
        for part_data in data["Objects"]:
            part = part_data["ObjectID"]
            timestamp = part_data["Timestamp"]
            user_data = part_data["UserData"]
            part_position = part_data["Position"]
            up_vec = part_data["Up"]
            at_vec = part_data["At"]
            # Build the item.
            part = part.replace("^", "")
            blender_part = build_item(
                part,
                timestamp,
                user_data,
                part_position,
                up_vec,
                at_vec,
                is_preset=True,
                material=material
            )
            
            parts.append(blender_part)
        # Get highest radius value.
        highest_x = max([part.location[0] for part in parts])
        lowest_x = min([part.location[0] for part in parts])
        highest_y = max([part.location[1] for part in parts])
        lowest_y = min([part.location[1] for part in parts])
        radius = max([abs(lowest_x), highest_x, abs(lowest_y), highest_y])
        # Build Nurbs Circle
        if build_control:
            preset_controller = bpy.ops.curve.primitive_nurbs_circle_add(
                radius=radius+4,
                view_align=False,
                enter_editmode=False,
                location=(0, 0, 0),
                layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False),
            )
            curve_object = bpy.context.scene.objects.active
            curve_object.name = preset_id
            curve_object.show_name = True
            curve_object["objectID"] = preset_id
            curve_object["preset_object"] = True
            me = curve_object.data
            me.name = preset_id + 'Mesh'
            for part in parts:
                bpy.ops.object.select_all(action='DESELECT') 
                curve_object.select = True
                part.select = True
                bpy.context.scene.objects.active = curve_object
                bpy.ops.object.parent_set()
                part.hide_select = True

            # Select Control
            bpy.ops.object.select_all(action='DESELECT')
            curve_object.select = True

            # Position.
            if position and up and at:
                curve_object.location = position
                # Rotation
                preset_up_vec = mathutils.Vector(up)
                preset_at_vec = mathutils.Vector(at)
                
                # Calculate a normal using the up vector
                right_vector = preset_at_vec.cross(preset_up_vec)
                new_up_vec = right_vector.cross(preset_at_vec)
                # Flip the right vector.
                right_vector *= -1
                # Construct a world matrix for the item.
                mat = mathutils.Matrix(
                    [
                        [right_vector[0], new_up_vec[0] , preset_at_vec[0],  position[0]],
                        [right_vector[1], new_up_vec[1] , preset_at_vec[1],  position[1]],
                        [right_vector[2], new_up_vec[2] , preset_at_vec[2],  position[2]],
                        [0.0,             0.0,            0.0,        1.0        ]
                    ]
                )
                # Create a rotation matrix that turns the whole thing 90 degrees at the origin.
                # This is to compensate blender's Z up axis.
                mat_rot = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
                mat = mat_rot * mat
                # Place the item in world space.
                curve_object.matrix_world = mat
            
            # Lock Scale
            curve_object.lock_scale[0] = True
            curve_object.lock_scale[1] = True
            curve_object.lock_scale[2] = True

# Material Methods ---
def assign_preset_material(item, colour_index=0, starting_index=0):
    # Material+Colour
    colour_index = starting_index + colour_index
    # Apply Custom Variable.
    item["UserData"] = colour_index
    preset_name = "preset_material"
    preset_material = None
    for material in bpy.data.materials:
        if preset_name == material.name:
            preset_material = material

    # Ensure we have a transparent shader.
    if not preset_material:
        preset_material = bpy.data.materials.new(name=preset_name) #set new material to variable
        preset_material.alpha = 0.07
        preset_material.diffuse_color = (0.8, 0.300186, 0.0178301)

    # Assign Material
    item.data.materials.append(preset_material) #add the material to the object
    
    return preset_material

def assign_material(item, colour_index=0, starting_index=0):
    global colours_dictionary
    # Material+Colour
    colour_index = starting_index + colour_index
    # Apply Custom Variable.
    item["UserData"] = colour_index
    # Create Material
    colour_name = "{0}_material".format(colour_index)
    colour_material = None
    for material in bpy.data.materials:
        if colour_name == material.name:
            colour_material = material

    # Ensure we have a transparent shader.
    if not colour_material:
        colour_material = bpy.data.materials.new(name=colour_name) #set new material to variable
        colour_material.alpha = 0.07
        colour_data = colours_dictionary.get(str(colour_index), {})
        colour_tuple = colour_data.get("colour", [0.8, 0.8,0.8])
        colour_material.diffuse_color = (colour_tuple[0], colour_tuple[1], colour_tuple[2])
    
    # Assign Material
    if not item.data.materials:
        item.data.materials.append(colour_material) #add the material to the object
    else:
        item.data.materials[0] = colour_material
    return colour_material

# Settings Class ---
def part_switch(self, context):
    """Toggle method for switching between parts and presets."""
    scene = context.scene
    part_list = "presets" if self.enum_switch == {'PRESETS'} else "parts"
    refresh_part_list(scene, part_list)

class NMSSettings(PropertyGroup):

    enum_switch = EnumProperty(
            name = "enum_switch",
            description = "Toggle to display between parts and presets.",
            items = [
                ("PARTS" , "Parts" , "View Base Parts..."),
                ("PRESETS", "Presets", "View Presets...")
            ],
            options = {"ENUM_FLAG"},
            default= {"PARTS"},
            update=part_switch
        )

    material_switch = EnumProperty(
            name = "material_switch",
            description = "Decide what type of material to apply",
            items = [
                ("CONCRETE" , "Concrete" , "Concrete"),
                ("RUST", "Rust", "Rust"),
                ("STONE", "Stone", "Stone"),
                ("WOOD", "Wood", "Wood")
            ],
            options = {"ENUM_FLAG"},
            default= {"CONCRETE"},
        )

    preset_name = StringProperty(
        name="preset_name",
        description="The of a preset.",
        default="",
        maxlen=1024,
    )

    string_base = StringProperty(
        name="Base Name",
        description="The name of the base set in game.",
        default="",
        maxlen=1024,
    )

    string_address = StringProperty(
        name="Galactic Address",
        description="The galactic address.",
        default="",
        maxlen=1024,
    )

    string_usn = StringProperty(
        name="USN",
        description="The username attribute.",
        default="",
        maxlen=1024,
    )

    string_uid = StringProperty(
        name="UID",
        description="A user ID.",
        default="",
        maxlen=1024,
    )

    string_lid = StringProperty(
        name="LID",
        description="Not sure what this is.",
        default="",
        maxlen=1024,
    )

    string_ts = StringProperty(
        name="TS",
        description="Timestamp - not sure what this is.",
        default="",
        maxlen=1024,
    )

    float_pos_x = FloatProperty(
        name = "X",
        description = "The X position of the base in planet space.",
        default = 0.0,
    )

    float_pos_y = FloatProperty(
        name = "Y",
        description = "The Y position of the base in planet space.",
        default = 0.0,
    )

    float_pos_z = FloatProperty(
        name = "Z",
        description = "The Z position of the base in planet space.",
        default = 0.0,
    )

    float_ori_x = FloatProperty(
        name = "X",
        description = "The X orientation vector of the base in planet space.",
        default = 0.0,
    )

    float_ori_y = FloatProperty(
        name = "Y",
        description = "The Y orientation vector of the base in planet space.",
        default = 0.0,
    )

    float_ori_z = FloatProperty(
        name = "Z",
        description = "The Z orientation vector of the base in planet space.",
        default = 0.0,
    )

    room_vis_switch = IntProperty(
        name = "room_vis_switch",
        default = 0
    )

    
    def import_nms_data(self):
        """Import and build a base based on NMS Save Editor data.
        
        This will read from the player clip-board as there's no easy way
        of creating large entry fields in Blender.
        """
        # Read clipboard data.
        clipboard_data = bpy.context.window_manager.clipboard
        try:
            nms_import_data = json.loads(clipboard_data)
        except:
            raise RuntimeError(
                "Could not import base data, are you sure you copied "
                "the data to the clipboard?"
            )
            return {"FAILED"}
        # Start a new file
        self.generate_from_data(nms_import_data)
    
    def generate_object_data(self, object, is_preset=False):
        """Given a blender object, generate useful NMS data from it.
        
        Args:
            object(ob): Blender scene object.
        Returns:
            dict: Dictionary of information.
        """
        # Get Object ID
        objectID = "^"+object["objectID"]
        # Get Matrix Data
        ob_world_matrix = object.matrix_world
        mat_rot = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
        obj_wm_offset = mat_rot * ob_world_matrix
        pos = obj_wm_offset.decompose()[0]
        up = get_direction_vector(obj_wm_offset, direction_matrix="up")
        at = get_direction_vector(obj_wm_offset, direction_matrix="at")
        
        sub_dict = OrderedDict()
        sub_dict["ObjectID"] = objectID
        sub_dict["Position"] = [
            pos[0],
            pos[1],
            pos[2]
        ]
        sub_dict["Up"] = [
            up[0],
            up[1],
            up[2]
        ]
        sub_dict["At"] = [
            at[0],
            at[1],
            at[2]
        ]

        # Bake NMS Object Data
        if not is_preset:
            timestamp = object["Timestamp"]
            print (object.name)
            user_data = object["UserData"]
            sub_dict["Timestamp"] = int(timestamp)
            sub_dict["UserData"] = int(user_data)


        return sub_dict

    def generate_from_data(self, nms_data):
        # Start new file
        self.new_file()
        # Start bringing the data in.
        if "GalacticAddress" in nms_data:
            self.string_address = str(nms_data["GalacticAddress"])
        if "Position" in nms_data:
            self.float_pos_x = nms_data["Position"][0]
            self.float_pos_y = nms_data["Position"][1]
            self.float_pos_z = nms_data["Position"][2]
        if "Forward" in nms_data:
            self.float_ori_x = nms_data["Forward"][0]
            self.float_ori_y = nms_data["Forward"][1]
            self.float_ori_z = nms_data["Forward"][2]
        if "Name" in nms_data:
            self.string_base = str(nms_data["Name"])
        if "Owner" in nms_data:
            Owner_details = nms_data["Owner"]
            self.string_uid = str(Owner_details["UID"])
            self.string_ts = str(Owner_details["TS"])
            self.string_lid = str(Owner_details["LID"])
            self.string_usn = str(Owner_details["USN"])

        # Build Objects
        if "Objects" in nms_data:
            for each in nms_data["Objects"]:
                each_position = each["Position"]
                each_up = each["Up"]
                each_at = each["At"]
                object_id = each["ObjectID"]
                user_data = each["UserData"]
                timestamp = each["Timestamp"]
                object_id = object_id.replace("^", "")
                build_item(
                    object_id,
                    userdata=user_data,
                    timestamp=timestamp,
                    position=each_position,
                    up_vec=each_up,
                    at_vec=each_at
                )

        if "Presets" in nms_data:
            for preset_data in nms_data["Presets"]:
                each_position = preset_data["Position"]
                each_up = preset_data["Up"]
                each_at = preset_data["At"]
                object_id = preset_data["ObjectID"]
                object_id = object_id.replace("^", "")
                build_preset(
                    object_id,
                    build_control=True,
                    position=each_position,
                    up = each_up,
                    at= each_at
                )

    def by_order(self, item):
        if "order" in item:
            return item["order"]
        return 0

    def generate_preset_data(self):
        """Generate dictionary of just objects for a preset."""
        preset_dict = {}
        preset_dict["Objects"] = []
        all_objects = sorted(bpy.data.objects, key=self.by_order)
        for ob in all_objects:
            if "objectID" in ob:
                if ob["objectID"] not in ["BASE_FLAG"]:
                    sub_dict = self.generate_object_data(ob)
                    preset_dict["Objects"].append(sub_dict)
        return preset_dict

    def save_preset_data(self, preset_name):
        data = self.generate_preset_data()
        file_path = os.path.join(preset_path, preset_name)
        # Add .json if it's not specified.
        if not file_path.endswith(".json"):
            file_path += ".json"
        # Save to file path
        with open(file_path, "w") as stream:
            json.dump(data, stream, indent=4)


    def generate_data(self, capture_presets=False):
        """Export the data in the blender scene to NMS compatible data.
        
        This will slot the data into the clip-board so you can easy copy
        and paste data back and forth between the tool.
        """
        # Try making the address an int.
        try:
            galactive_address = int(self.string_address)
        except BaseException:
            galactive_address = self.string_address

        data = {
            "BaseVersion": 3,
            "GalacticAddress": galactive_address,
            "Position": [self.float_pos_x, self.float_pos_y, self.float_pos_z],
            "Forward": [self.float_ori_x, self.float_ori_y, self.float_ori_z],
            "UserData": 0,
            "RID": "",
            "Owner": self.get_user_details(),
            "Name": self.string_base,
            "BaseType": {"PersistentBaseTypes":"HomePlanetBase"},
            "LastUpdateTimestamp": 1539982731
        }
        
        all_objects = sorted(bpy.data.objects, key=self.by_order)
        
        # Capture objects
        data["Objects"] = []
        if not capture_presets:
            for ob in all_objects:
                if "objectID" in ob:
                    # Skip if its a preset.
                    if "preset_object" in ob:
                        continue
                    # Capture object.
                    sub_dict = self.generate_object_data(ob)
                    data["Objects"].append(sub_dict)

        if capture_presets:
            data["Presets"] = []
            for ob in all_objects:
                if "objectID" in ob:
                    # Capture presets
                    if "preset_object" in ob:
                        sub_dict = self.generate_object_data(ob, is_preset=True)
                        data["Presets"].append(sub_dict)
                    if "is_preset" in ob:
                        if ob["is_preset"] == 0:
                            sub_dict = self.generate_object_data(ob)
                            data["Objects"].append(sub_dict)
        return data
        
    def generate_nms_data(self):
        data = self.generate_data()
        bpy.context.window_manager.clipboard = json.dumps(data, indent=4)

    def generate_save_data(self, file_path):
        data = self.generate_data(capture_presets=True)
        # Generate Presets
        data["presets"] = {}
        
        # Add .json if it's not specified.
        if not file_path.endswith(".json"):
            file_path += ".json"
        # Save to file path
        with open(file_path, "w") as stream:
            json.dump(data, stream, indent=4)

    def get_user_details(self):
        """Get user details from the json store."""
        try:
            ts = int(self.string_ts)
        except:
            ts = self.string_ts
        return {
            "UID": self.string_uid,
            "LID": self.string_lid,
            "USN": self.string_usn,
            "TS": ts
        }

    def load_nms_data(self, file_path):
        # First load 
        with open(file_path, "r") as stream:
            try:
                save_data = json.load(stream)
            except BaseException:
                raise RuntimeError(
                    "Could not load base data, are you sure you chose the correct file?"
                )
                return
        # Build from Data
        self.generate_from_data(save_data)
        # Build Presets.
        pass

    def new_file(self):
        self.string_address = ""
        self.string_base = ""
        self.string_lid = ""
        self.string_ts = ""
        self.string_uid = ""
        self.string_usn = ""
        self.float_pos_x = 0
        self.float_pos_y = 0
        self.float_pos_z = 0
        self.float_ori_x = 0
        self.float_ori_y = 0
        self.float_ori_z = 0

        # Remove all no mans sky items from scene.
        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')
        # Select NMS Items
        for ob in bpy.data.objects:
            if "objectID" in ob:
                ob.hide_select = False
                ob.select = True
        # Remove
        bpy.ops.object.delete() 
        # Reset room vis
        self.room_vis_switch = 0

    def toggle_room_visibility(self):
        # Ensure we are in the CYCLES renderer.
        bpy.context.scene.render.engine = 'CYCLES'
        # Increment Room Vis
        if self.room_vis_switch < 2:
            self.room_vis_switch += 1
        else:
            self.room_vis_switch = 0

        # Select NMS Items
        invisible_objects = [
            "CUBEROOM",
            "CUBEROOMCURVED",
            "CURVEDCUBEROOF",
            "CUBEGLASS",
            "CUBEFRAME",
            "CUBEWINDOW",

            "BUILDLANDINGPAD",

            "CORRIDORC",
            "CORRIDOR",
            "GLASSCORRIDOR",
            "MAINROOM",
            "MAINROOMCUBE",
            
            "VIEWSPHERE",
            "BIOROOM",

            "W_WALL",
            "W_WALL_H",
            "W_WALL_Q",
            "W_WALL_Q_H",
            "W_ROOF_M",
            "W_RAMP",
            "W_FLOOR",
            "W_GFLOOR",
            "W_FLOOR_Q",
            "W_ARCH",
            "W_WALLDIAGONAL",
            "W_WALLWINDOW",
            "W_RAMP_H",
            "W_WALL_WINDOW",

            "C_WALL",
            "C_WALL_H",
            "C_WALL_Q",
            "C_WALL_Q_H",
            "C_ROOF_M",
            "C_RAMP",
            "C_FLOOR",
            "C_GFLOOR",
            "C_FLOOR_Q",
            "C_ARCH",
            "C_WALLDIAGONAL",
            "C_WALLWINDOW",
            "C_RAMP_H",
            "C_WALL_WINDOW",
            
            "M_WALL",
            "M_WALL_H",
            "M_WALL_Q",
            "M_WALL_Q_H",
            "M_ROOF_M",
            "M_RAMP",
            "M_FLOOR",
            "M_GFLOOR",
            "M_FLOOR_Q",
            "M_ARCH",
            "M_WALLDIAGONAL",
            "M_WALLWINDOW",
            "M_RAMP_H",
            "M_WALL_WINDOW",
        ]
        for ob in bpy.data.objects:
            if "objectID" in ob:
                if ob["objectID"] in invisible_objects:
                    is_preset = False
                    if "is_preset" in ob:
                        is_preset = ob["is_preset"]
                    if self.room_vis_switch == 0:
                        ob.hide = False
                        ob.show_transparent = False
                        if not is_preset:
                            ob.hide_select = False    
                    if self.room_vis_switch == 1:
                        ob.hide = False
                        ob.show_transparent = True
                        if not is_preset:
                            ob.hide_select = True
                    if self.room_vis_switch == 2:
                        ob.hide = True
                    ob.select = False


    def duplicate(self):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.",
                title="Duplicate"
            )
            return

        source_object = bpy.context.scene.objects.active
        object_id = source_object["objectID"]
        userdata = source_object["UserData"]
        build_item(object_id, auto_snap=True, userdata=userdata)

    def apply_colour(self, colour_index=0, starting_index=0):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.",
                title="Apply Colour"
            )
            return

        for obj in selected_objects:
            # Set Colour Index
            obj["UserData"] = colour_index
            # Apply Colour Material.
            assign_material(obj, colour_index, starting_index)

        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

    def snap(
        self,
        next_source=False,
        prev_source=False,
        next_target=False,
        prev_target=False):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects
        
        if len(selected_objects) != 2:
            ShowMessageBox(
                message="Make sure you have two items selected. Select the item you want to snap to, then the item you want to snap.",
                title="Snap"
            )
            return

        # Perform Snap
        source_object = bpy.context.scene.objects.active
        target_object = [obj for obj in selected_objects if obj != source_object][0]
        snap_objects(
            source_object,
            target_object,
            next_source=next_source,
            prev_source=prev_source,
            next_target=next_target,
            prev_target=prev_target
        )


# Utility Classes ---
def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


# File Buttons Panel --- 
class NMSFileButtonsPanel(Panel):
    bl_idname = "NMSFileButtonsPanel"
    bl_label = "No Man's Sky Base Builder"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        first_column = layout.column(align=True)
        button_row = first_column.row(align=True)
        button_row.operator("nms.new_file", icon="NEW")
        save_load_row = first_column.row(align=True)
        save_load_row.operator("nms.save_data", icon="FILE_TICK")
        save_load_row.operator("nms.load_data", icon="FILE_FOLDER")
        nms_row = first_column.row(align=True)
        nms_row.operator("nms.import_nms_data", icon="PASTEDOWN")
        nms_row.operator("nms.export_nms_data", icon="COPYDOWN")

# Base Property Panel ---
class NMSBasePropPanel(Panel):
    bl_idname = "NMSBasePropPanel"
    bl_label = "Base Properties"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        properties_box = layout.box()
        properties_column = properties_box.column(align=True)
        properties_column.prop(nms_tool, "string_base")
        properties_column.prop(nms_tool, "string_address")


# Tools Panel --- 
class NMSToolsPanel(Panel):
    bl_idname = "NMSToolsPanel"
    bl_label = "Tools"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        # tools_box = layout.box()
        tools_column = layout.column()
        tools_column.operator("nms.toggle_room_visibility", icon="GHOST_ENABLED")
        tools_column.operator("nms.save_as_preset", icon="SCENE_DATA")


# Snap Panel --- 
class NMSSnapPanel(Panel):
    bl_idname = "NMSSnapPanel"
    bl_label = "Snap"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        snap_box = layout.box()
        snap_column = snap_box.column()
        snap_column.operator("nms.duplicate", icon="MOD_BOOLEAN")
        snap_column.operator("nms.snap", icon="SNAP_ON")
        target_row = snap_column.row()
        target_row.label("Target")
        target_row.operator("nms.snap_target_prev", icon="TRIA_LEFT")
        target_row.operator("nms.snap_target_next", icon="TRIA_RIGHT")
        
        source_row = snap_column.row()
        source_row.label("Source")
        source_row.operator("nms.snap_source_prev", icon="TRIA_LEFT")
        source_row.operator("nms.snap_source_next", icon="TRIA_RIGHT")

# Colour Panel --- 
class NMSColourPanel(Panel):
    bl_idname = "NMSColourPanel"
    bl_label = "Colour"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        pcoll = preview_collections["main"]
        enum_row = layout.row(align=True)
        enum_row.prop(nms_tool, "material_switch", expand=True)
        colour_row_1 = layout.row(align=True)
        colour_row_1.scale_y = 1.3
        colour_row_1.scale_x = 1.3
        for idx in range(16):
            colour_icon = pcoll["{0}_colour".format(idx)]
            colour_op = colour_row_1.operator(
                "nms.apply_colour",
                text="",
                icon_value=colour_icon.icon_id,
            )
            colour_op.colour_index = idx

# Build Panel ---
class NMSBuildPanel(Panel):
    bl_idname = "NMSBuildPanel"
    bl_label = "Build"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        layout.prop(nms_tool, "enum_switch", expand=True)
        layout.template_list(
            "Actions_List",
            "",
            context.scene,
            "col",
            context.scene,
            "col_idx"
        )

    
class Actions_List(bpy.types.UIList):
    previous_layout = None
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Add a category item if the title is specified.
            if item.title:
                layout.label(item.title)

            # Draw Parts
            if item.item_type == "parts" and item.description:
                all_parts = [x for x in item.description.split(",") if x]
                part_row = layout.column_flow(columns=3)
                for part in all_parts:
                    operator = part_row.operator("object.list_action_operator", text=get_nice_name(part))
                    operator.part_id = part
            
            # Draw Presets
            if item.item_type == "presets":
                if item.description in get_presets():
                    # Create Sub layuts
                    build_area = layout.split(0.7)
                    operator = build_area.operator("object.list_action_operator", text=item.description)
                    edit_area = build_area.split(0.6)
                    edit_operator = edit_area.operator("object.list_edit_operator", text="Edit")
                    delete_operator = edit_area.operator("object.list_delete_operator", text="X")
                    operator.part_id = item.description
                    edit_operator.part_id = item.description
                    delete_operator.part_id = item.description


class PartCollection(bpy.types.PropertyGroup):
    title = bpy.props.StringProperty()
    description = bpy.props.StringProperty()
    item_type = bpy.props.StringProperty()

def collection_hack(scene):
    """Remove and refresh part list."""
    bpy.app.handlers.scene_update_pre.remove(collection_hack)
    refresh_part_list(scene)
    
def create_sublists(input_list, n=3):
    """Create a list of sub-lists with n elements."""
    total_list = [input_list[x:x+n] for x in range(0, len(input_list), n)]
    # Fill in any blanks.
    last_list = total_list[-1]
    while len(last_list) < n:
        last_list.append("")
    return total_list


def generate_part_data(item_type="parts"):
    """Generate a list of Blender UI friendly data of categories and parts.
    
    When we retrieve presets we just want an item name.

    For parts I am doing a trick where I am grouping sets of 3 parts in order
    to make a grid in each UIList entry.

    Args:
        item_type (str): The type of items we want to retrieve
            options - "presets", "parts".
    
    Return:
        list: tuple (str, str): Label and Description of items for the UIList.
    """
    ui_list_data = []
        # Presets
    if "presets" in item_type:
        ui_list_data.append(("Presets", ""))
        for preset in get_presets():
            ui_list_data.append(("", preset))
    # Parts
    if "parts" in item_type:
        for category in get_categories():
            ui_list_data.append((category, ""))
            parts = get_parts_from_category(category)
            new_parts = create_sublists(parts)
            for part in new_parts:
                joined_list = ",".join(part)
                ui_list_data.append(("", joined_list))
    return ui_list_data


def refresh_part_list(scene, item_type="parts"):
    """Refresh the UI List.
    
    Args:
        item_type: The type of items we want to retrieve.
            options - "presets", "parts".
    """
    # Clear the scene col.
    try:
        scene.col.clear()
    except:
        pass

    # Get part data based on 
    ui_list_data = generate_part_data(item_type=item_type)
    # Create items with labels and descriptions.
    for i, (label, description) in enumerate(ui_list_data, 1):
        item = scene.col.add()
        item.title = label.title().replace("_", " ")
        item.description = description
        item.item_type = item_type
        item.name = " ".join((str(i), label, description))

# Operators ---
class NewFile(bpy.types.Operator):
    bl_idname = "nms.new_file"
    bl_label = "New"
    # bl_label = "Do you really want to start a new file??"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.new_file()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class ToggleRoom(bpy.types.Operator):
    bl_idname = "nms.toggle_room_visibility"
    bl_label = "Toggle Room Visibility"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.toggle_room_visibility()
        return {'FINISHED'}


class SaveData(bpy.types.Operator):
    bl_idname = "nms.save_data"
    bl_label = "Save"
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.generate_save_data(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class LoadData(bpy.types.Operator):
    bl_idname = "nms.load_data"
    bl_label = "Load"
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.load_nms_data(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ImportData(bpy.types.Operator):
    bl_idname = "nms.import_nms_data"
    bl_label = "Import NMS"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.import_nms_data()
        return {'FINISHED'}


class ExportData(bpy.types.Operator):
    bl_idname = "nms.export_nms_data"
    bl_label = "Export NMS"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.generate_nms_data()
        return {'FINISHED'}


class SaveAsPreset(bpy.types.Operator):
    bl_idname = "nms.save_as_preset"
    bl_label = "Save As Preset"
    preset_name = bpy.props.StringProperty(name="Preset Name")
    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.save_preset_data(self.preset_name)
        # Reset string variable.
        self.preset_name = ""
        if nms_tool.enum_switch == {'PRESETS'}:
            refresh_part_list(scene, ["presets"])
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class ListActionOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.list_action_operator"
    bl_label = "Simple Object Operator"
    
    part_id = StringProperty()

    def execute(self, context):
        if self.part_id in get_presets():
            build_preset(self.part_id, build_control=True)
        else:
            build_item(self.part_id, auto_snap=True)
        return {'FINISHED'}


class ListEditOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.list_edit_operator"
    bl_label = "Edit Preset"
    
    part_id = StringProperty()

    def execute(self, context):
        if self.part_id in get_presets():
            scene = context.scene
            nms_tool = scene.nms_base_tool
            nms_tool.new_file()
            build_preset(self.part_id, material="white")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class ListDeleteOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.list_delete_operator"
    bl_label = "Delete"
    
    part_id = StringProperty()

    def execute(self, context):
        if self.part_id in get_presets():
            scene = context.scene
            nms_tool = scene.nms_base_tool
            delete_preset(self.part_id)
            if nms_tool.enum_switch == {'PRESETS'}:
                refresh_part_list(scene, ["presets"])
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class Duplicate(bpy.types.Operator):
    bl_idname = "nms.duplicate"
    bl_label = "Duplicate"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.duplicate()
        return {'FINISHED'}

class ApplyColour(bpy.types.Operator):
    bl_idname = "nms.apply_colour"
    bl_label = "Apply Colour"
    bl_options = {'REGISTER', 'INTERNAL'}

    colour_index = IntProperty(default=0)

    @property
    def set_label(self, label):
        self.bl_label = label

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        material = nms_tool.material_switch
        if material == {'CONCRETE'}:
            starting_index = 0
        elif material == {'RUST'}:
            starting_index = 16777216
        elif material == {'STONE'}:
            starting_index = 33554432
        elif material == {'WOOD'}:
            starting_index = 50331648
        nms_tool.apply_colour(
            colour_index=self.colour_index,
            starting_index=starting_index
        )
        return {'FINISHED'}

class Snap(bpy.types.Operator):
    bl_idname = "nms.snap"
    bl_label = "Snap"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.snap()
        return {'FINISHED'}

class SnapSourceNext(bpy.types.Operator):
    bl_idname = "nms.snap_source_next"
    bl_label = "Next"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.snap(next_source=True)
        return {'FINISHED'}

class SnapSourcePrev(bpy.types.Operator):
    bl_idname = "nms.snap_source_prev"
    bl_label = "Prev"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.snap(prev_source=True)
        return {'FINISHED'}

class SnapTargetNext(bpy.types.Operator):
    bl_idname = "nms.snap_target_next"
    bl_label = "Next"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.snap(next_target=True)
        return {'FINISHED'}

class SnapTargetPrev(bpy.types.Operator):
    bl_idname = "nms.snap_target_prev"
    bl_label = "Prev"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.snap(prev_target=True)
        return {'FINISHED'}

# We can store multiple preview collections here,
# however in this example we only store "main"
preview_collections = {}

# Plugin Registeration ---
def register():
    # Load Icons.
    
    pcoll = bpy.utils.previews.new()
    # path to the folder where the icon is
    # the path is calculated relative to this py file inside the addon folder
    my_icons_dir = os.path.join(os.path.dirname(__file__), "images")

    # load a preview thumbnail of a file and store in the previews collection
    # Load Colours
    for idx in range(16):
        pcoll.load(
            "{0}_colour".format(idx),
            os.path.join(my_icons_dir, "{0}.jpg".format(idx)),
            'IMAGE'
        )

    preview_collections["main"] = pcoll

    # Register Plugin
    bpy.utils.register_module(__name__)
    bpy.types.Scene.nms_base_tool = PointerProperty(type=NMSSettings)
    bpy.types.Scene.col = bpy.props.CollectionProperty(type=PartCollection)
    bpy.types.Scene.col_idx = bpy.props.IntProperty(default=0)
    bpy.app.handlers.scene_update_pre.append(collection_hack)
    

def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.nms_base_tool

if __name__ == "__main__":
    register()
