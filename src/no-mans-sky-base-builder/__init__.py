# Header Info ---
bl_info = {
    "name": "No Mans Sky Base Builder",
    "description": "A tool to assist with base building in No Mans Sky",
    "author": "Charlie Banks",
    "version": (0, 5, 0),
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

import bpy
import bpy.utils
import mathutils
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)
from bpy.types import Operator, Panel, PropertyGroup

# File Paths ---
file_path = os.path.dirname(os.path.realpath(__file__))
model_path = os.path.join(file_path, "models")
preset_path = os.path.join(file_path, "presets")

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
def get_parts_from_category(category):
    """Get a list of parts belonging to a category."""
    category_path = os.path.join(model_path, category)
    if not os.path.exists(category_path):
        raise RuntimeError(category + " does not exist.")
    
    return sorted(
        [part.split(".obj")[0] for part in os.listdir(category_path) if part.endswith(".obj")]
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
        material="white"):
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

    # Assign Material
    if material == "white":
        assign_white_material(item)
    elif material == "preset":
        assign_preset_material(item)

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
    item["UserData"] = userdata
    item["Timestamp"] = timestamp
    item["is_preset"] = is_preset
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

    return item

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
        at=None):
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
                material="preset"
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
def assign_preset_material(item):
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


def assign_white_material(item):
    transparent_name = "transparent_material"
    transparent_material = None
    for material in bpy.data.materials:
        if transparent_name == material.name:
            transparent_material = material

    # Ensure we have a transparent shader.
    if not transparent_material:
        transparent_material = bpy.data.materials.new(name=transparent_name) #set new material to variable
        transparent_material.alpha = 0.07
    # Assign Material
    item.data.materials.append(transparent_material) #add the material to the object
    return transparent_material





# Settings Class ---
class NMSSettings(PropertyGroup):

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


# ------------------------------------------------------------------------
#    my tool in objectmode
# ------------------------------------------------------------------------

class OBJECT_PT_my_panel(Panel):
    bl_idname = "OBJECT_PT_my_panel"
    bl_label = "No Mans Sky Base Builder"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "No Mans Sky"
    bl_context = "objectmode"   

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool
        col = context.scene.col
        idx = context.scene.col_idx

        button_row = layout.row()
        button_row.operator("nms.new_file")
        button_row.operator("nms.save_data")
        button_row.operator("nms.load_data")
        nms_row = layout.row()
        nms_row.operator("nms.import_nms_data")
        nms_row.operator("nms.export_nms_data")
        
        properties_box = layout.box()
        properties_box.label("Base Properties")
        properties_box.prop(nms_tool, "string_base")
        properties_box.prop(nms_tool, "string_address")
        properties_box.label("User Properties")
        properties_box.prop(nms_tool, "string_usn")
        properties_box.prop(nms_tool, "string_uid")
        properties_box.prop(nms_tool, "string_lid")
        properties_box.prop(nms_tool, "string_ts")

        layout.label("Tools")
        tools_box = layout.box()
        tools_box.operator("nms.toggle_room_visibility")
        tools_box.operator("nms.save_as_preset")

        layout.label("Parts")
        layout.template_list(
            "Actions_List",
            "",
            context.scene,
            "col",
            context.scene,
            "col_idx"
        )
        # row.operator("object.simple_operator" , text = "All")



    
class Actions_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            split = layout.split(0.7)
            if item.label:
                split.label(item.label)
            if item.description:
                operator = split.operator(
                    "object.list_action_operator",
                    text = item.description,
                )
                operator.part_id = item.description

                if item.description in get_presets():
                    sub_split = split.split(0.6)
                    edit_operator = sub_split.operator(
                        "object.list_edit_operator",
                        text = "Edit",
                    )
                    edit_operator.part_id = item.description

                    delete_operator = sub_split.operator(
                        "object.list_delete_operator",
                        text = "X",
                    )
                    delete_operator.part_id = item.description

        elif self.layout_type in {'GRID'}:
            pass

class MyColl(bpy.types.PropertyGroup):
    #name = bpy.props.StringProperty()
    label = bpy.props.StringProperty()
    description = bpy.props.StringProperty()

def collhack(scene):
    bpy.app.handlers.scene_update_pre.remove(collhack)
    refresh_part_list(scene)
    
def generate_part_data():
    """Generate a list of Blender UI friendly data of categories and parts."""
    coll_data = []
    
    # Presets
    coll_data.append(("Presets", ""))
    for preset in get_presets():
        coll_data.append(("", preset))
    # Parts
    for category in get_categories():
        coll_data.append((category, ""))
        parts = get_parts_from_category(category)
        for part in parts:
            coll_data.append(("", part))
    return coll_data

def refresh_part_list(scene):
    """Refresh the UI List."""
    try:
        scene.col.clear()
    except:
        pass

    part_data = generate_part_data()
    for i, (label, description) in enumerate(part_data, 1):
        item = scene.col.add()
        item.label = label.title().replace("_", " ")
        item.description = description
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
        print("Creating New File!")
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
        print("Creating New File!")
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
        print("Creating New File!")
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
        print("Creating New File!")
        refresh_part_list(scene)
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
            build_item(self.part_id)
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
            build_preset(self.part_id)
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
            delete_preset(self.part_id)
            refresh_part_list(scene)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


# Plugin Registeration ---
def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.nms_base_tool = PointerProperty(type=NMSSettings)
    bpy.types.Scene.col = bpy.props.CollectionProperty(type=MyColl)
    bpy.types.Scene.col_idx = bpy.props.IntProperty(default=0)
    bpy.app.handlers.scene_update_pre.append(collhack)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.nms_base_tool

if __name__ == "__main__":
    register()
