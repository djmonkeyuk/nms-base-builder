# Header Info ---
bl_info = {
    "name": "No Mans Sky Base Builder",
    "description": "A tool to assist with base building in No Mans Sky",
    "author": "Charlie Banks",
    "version": (0, 9, 5),
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
from . import parts, presets, snap, material
import bpy.utils.previews
import bpy
import bpy.utils
import mathutils
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)
from bpy.types import Operator, Panel, PropertyGroup

import logging

LOGGER = logging.getLogger(__name__)

# File Paths ---
file_path = os.path.dirname(os.path.realpath(__file__))
user_path = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
preset_path = os.path.join(user_path, "presets")

# Ensure custom paths are created.
for user_data_path in [user_path, preset_path]:
    if not os.path.exists(user_data_path):
        os.makedirs(user_data_path)

def get_builders(context):
    scene = context.scene
    nms_tool = scene.nms_base_tool
    return nms_tool, nms_tool.part_builder, nms_tool.preset_builder, nms_tool.snapper

# Settings Class ---
def part_switch(self, context):
    """Toggle method for switching between parts and presets."""
    scene = context.scene
    part_list = "presets" if self.enum_switch == {'PRESETS'} else "parts"

    if self.enum_switch not in [{'PRESETS'}, {'PARTS'}]:
        refresh_part_list(scene, part_list, mod_pack=list(self.enum_switch)[0])
    else:    
        refresh_part_list(scene, part_list)

class NMSSettings(PropertyGroup):
    # Create References to Builder objects.
    part_builder = parts.PartBuilder()
    preset_builder = presets.PresetBuilder(part_builder=part_builder)
    snapper = snap.Snapper()

    # Build Arrau of base part types. (Vanilla - Mods - Presets)
    enum_items = []
    enum_items.append(("PARTS" , "Parts" , "View Base Parts..."))
    enum_items.append(("PRESETS", "Presets", "View Presets..."))

    # Blender Properties.
    enum_switch = EnumProperty(
        name = "enum_switch",
        description = "Toggle to display between parts and presets.",
        items = enum_items,
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
            if "NMS_LIGHT" in ob:
                ob.hide = False
                ob.hide_select = False
                ob.select = True
        # Remove
        bpy.ops.object.delete() 
        # Reset room vis
        self.room_vis_switch = 0

    def toggle_room_visibility(self):
        """Cycle through room visibilities.
        
        0: Normal
        1: Ghosted
        2: Invisible
        3: Lighted
        """
        # Increment Room Vis
        if self.room_vis_switch < 3:
            self.room_vis_switch += 1
        else:
            self.room_vis_switch = 0

        # Select NMS Items
        invisible_objects = [
            "MAINROOM_WATER",
            "MAINROOMCUBE_W",
            "CORRIDOR_WATER",
            "CORRIDORL_WATER",
            "CORRIDORX_WATER",
            "CORRIDORT_WATER",
            "CORRIDORV_WATER",
            
            "CUBEROOM",
            "CUBEROOMCURVED",
            "CURVEDCUBEROOF",
            "CUBEGLASS",
            "CUBEFRAME",
            "CUBEWINDOW",

            "BUILDLANDINGPAD",

            "CORRIDORL",
            "CORRIDORX",
            "CORRIDORT",
            "CORRIDORV",
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
        # Set Shading.
        if self.room_vis_switch in [0, 1, 2]:
            bpy.context.space_data.viewport_shade = 'SOLID'
            bpy.context.scene.render.engine = 'CYCLES'
        elif self.room_vis_switch in [3]:
            bpy.context.space_data.viewport_shade = 'TEXTURED'
            bpy.context.scene.render.engine = 'BLENDER_RENDER'

        # Set Hide
        hidden = True
        if self.room_vis_switch in [0, 1, 3]:
            hidden = False

        # Transparency.
        show_transparent = False
        if self.room_vis_switch in [1]:
            show_transparent = True

        # Hide Select.
        hide_select = False
        if self.room_vis_switch in [1]:
            hide_select = True

        for ob in bpy.data.objects:
            if "objectID" in ob:
                if ob["objectID"] in invisible_objects:
                    is_preset = False
                    if "is_preset" in ob:
                        is_preset = ob["is_preset"]
                    # Normal
                    ob.hide = hidden
                    ob.show_transparent = show_transparent
                    if not is_preset:
                        ob.hide_select = hide_select    
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

        source_object = selected_objects[0]
        object_id = source_object["objectID"]
        userdata = source_object["UserData"]
        # Build Item.
        new_item = self.part_builder.build_item(object_id, userdata=userdata)
        # Snap.
        self.snapper.snap_objects(source_object, new_item)

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
            material.assign_material(obj, colour_index, starting_index)

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
            message = (
                "Make sure you have two items selected. Select the item you"
                " want to snap to, then the item you want to snap."
            )
            ShowMessageBox(
                message=message,
                title="Snap"
            )
            return

        # Perform Snap
        source_object = bpy.context.scene.objects.active
        target_object = [obj for obj in selected_objects if obj != source_object][0]
        self.snapper.snap_objects(
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
        tools_column = layout.column()
        scene = context.scene
        nms_tool = scene.nms_base_tool
        label = "Room Visibility: Normal"
        if nms_tool.room_vis_switch == 1:
            label = "Room Visibility: Ghosted"
        elif nms_tool.room_vis_switch == 2:
            label = "Room Visibility: Invisible"
        elif nms_tool.room_vis_switch == 3:
            label = "Room Visibility: Lighted"

        tools_column.operator(
            "nms.toggle_room_visibility",
            icon="OBJECT_DATA",
            text=label
        )
        tools_column.operator(
            "nms.save_as_preset",
            icon="SCENE_DATA"
        )


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
        nms_tool, parts, presets, _ = get_builders(context)
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Add a category item if the title is specified.
            if item.title:
                layout.label(item.title)

            # Draw Parts
            if item.item_type == "parts" and item.description:
                all_parts = [x for x in item.description.split(",") if x]
                part_row = layout.column_flow(columns=3)
                for part in all_parts:
                    operator = part_row.operator(
                        "object.list_action_operator",
                        text=parts.get_nice_name(part)
                    )
                    operator.part_id = part
            
            # Draw Presets
            if item.item_type == "presets":
                if item.description in presets.get_presets():
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


def generate_part_data(item_type="parts", mod_pack=None):
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
    part_builder = parts.PartBuilder()
    preset_builder = presets.PresetBuilder(part_builder)
    ui_list_data = []
    # Presets
    if "presets" in item_type:
        ui_list_data.append(("Presets", ""))
        for preset in preset_builder.get_presets():
            ui_list_data.append(("", preset))
    # Parts
    if "parts" in item_type:
        for category in part_builder.get_categories():
            ui_list_data.append((category, ""))
            category_parts = part_builder.get_parts_from_category(category)
            new_parts = create_sublists(category_parts)
            for part in new_parts:
                joined_list = ",".join(part)
                ui_list_data.append(("", joined_list))
    return ui_list_data


def refresh_part_list(scene, item_type="parts", mod_pack=None):
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
    ui_list_data = generate_part_data(item_type=item_type, mod_pack=mod_pack)
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
    bl_label = "Toggle Room Visibility: Normal"

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
            refresh_part_list(scene, "presets")
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
        _, parts, presets, _ = get_builders(context)
        if self.part_id in presets.get_presets():
            presets.build_preset(self.part_id)
        else:
            new_item = parts.build_item(self.part_id)
        return {'FINISHED'}


class ListEditOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.list_edit_operator"
    bl_label = "Edit Preset"
    
    part_id = StringProperty()

    def execute(self, context):
        nms_tool, _, presets, _ = get_builders(context)
        if self.part_id in presets.get_presets():
            nms_tool.new_file()
            presets.generate_preset(self.part_id)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class ListDeleteOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.list_delete_operator"
    bl_label = "Delete"
    
    part_id = StringProperty()

    def execute(self, context):
        scene = context.scene
        nms_tool, _, presets, _ = get_builders(context)
        if self.part_id in presets.get_presets():
            presets.delete_preset(self.part_id)
            if nms_tool.enum_switch == {'PRESETS'}:
                refresh_part_list(scene, "presets")
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
