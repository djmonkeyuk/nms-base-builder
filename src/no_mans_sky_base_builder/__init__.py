# Header Info ---
bl_info = {
    "name": "No Mans Sky Base Builder",
    "description": "A tool to assist with base building in No Mans Sky",
    "author": "Charlie Banks",
    "version": (1, 3, 0),
    "blender": (2, 90, 0),
    "location": "3D View > Tools",
    "warning": "",  # used for warning icon and text in addons panel
    "wiki_url": "https://www.nexusmods.com/nomanssky/mods/984",
    "tracker_url": "",
    "category": "Game Engine",
}
import importlib
import json
import os
import sys
import webbrowser

import bpy
import bpy.utils
import bpy.utils.previews
import mathutils
import no_mans_sky_base_builder.builder as builder
import no_mans_sky_base_builder.part_overrides.line as line
import no_mans_sky_base_builder.preset as preset
import no_mans_sky_base_builder.utils.blend_utils as blend_utils
import no_mans_sky_base_builder.utils.curve as curve
import no_mans_sky_base_builder.utils.material as _material
import no_mans_sky_base_builder.utils.python as python_utils
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)
from bpy.types import Operator, Panel, PropertyGroup

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")

BUILDER = builder.Builder()
GHOSTED_JSON = os.path.join(FILE_PATH, "resources", "ghosted.json")
ghosted_reference = python_utils.load_dictionary(GHOSTED_JSON)
GHOSTED_ITEMS = ghosted_reference["GHOSTED"]

# Setting Support Methods ---
def ShowMessageBox(message="", title="Message Box", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def part_switch(self, context):
    """Toggle method for switching between parts and presets."""
    scene = context.scene
    part_list = "presets" if self.enum_switch == {"PRESETS"} else "parts"

    if self.enum_switch not in [{"PRESETS"}]:
        refresh_ui_part_list(scene, part_list, pack=list(self.enum_switch)[0])
    else:
        refresh_ui_part_list(scene, part_list)


# Core Settings Class
class NMSSettings(PropertyGroup):
    # Build Array of base part types. (Vanilla Parts - Mods - Presets)
    enum_items = []
    for pack, _ in BUILDER.available_packs:
        enum_items.append((pack, pack, "View {0}...".format(pack)))
    enum_items.append(("PRESETS", "Presets", "View Presets..."))

    # Blender Properties.
    enum_switch : EnumProperty(
        name="enum_switch",
        description="Toggle to display between parts and presets.",
        items=enum_items,
        options={"ENUM_FLAG"},
        default=None,
        update=part_switch,
    )

    material_switch : EnumProperty(
        name="material_switch",
        description="Decide what type of material to apply",
        items=[
            ("CONCRETE", "Concrete", "Concrete"),
            ("RUST", "Rust", "Rust"),
            ("STONE", "Stone", "Stone"),
            ("WOOD", "Wood", "Wood"),
        ],
        options={"ENUM_FLAG"},
        default={"CONCRETE"},
    )

    preset_name : StringProperty(
        name="preset_name", description="The of a preset.", default="", maxlen=1024
    )

    string_base : StringProperty(
        name="Base Name",
        description="The name of the base set in game.",
        default="",
        maxlen=1024,
    )

    string_address : StringProperty(
        name="Galactic Address",
        description="The galactic address.",
        default="",
        maxlen=1024,
    )

    string_base_type : StringProperty(
        name="The base type",
        description="Planet or Freighter.",
        default="HomePlanetBase",
        maxlen=1024,
    )

    string_usn : StringProperty(
        name="USN", description="The username attribute.", default="", maxlen=1024
    )

    string_uid : StringProperty(
        name="UID", description="A user ID.", default="", maxlen=1024
    )

    string_lid : StringProperty(
        name="LID", description="Not sure what this is.", default="", maxlen=1024
    )

    string_ptk : StringProperty(
        name="PTK", description="Not sure what this is.", default="", maxlen=1024
    )

    string_ts : StringProperty(
        name="TS",
        description="Timestamp.",
        default="",
        maxlen=1024,
    )

    string_last_ts : StringProperty(
        name="LastUpdatedTimestamp",
        description="Timestamp - last updated timestamp.",
        default="",
        maxlen=1024,
    )

    float_pos_x : FloatProperty(
        name="X", description="The X position of the base in planet space.", default=0.0
    )

    float_pos_y : FloatProperty(
        name="Y", description="The Y position of the base in planet space.", default=0.0
    )

    float_pos_z : FloatProperty(
        name="Z", description="The Z position of the base in planet space.", default=0.0
    )

    float_ori_x : FloatProperty(
        name="X",
        description="The X orientation vector of the base in planet space.",
        default=0.0,
    )

    float_ori_y : FloatProperty(
        name="Y",
        description="The Y orientation vector of the base in planet space.",
        default=0.0,
    )

    float_ori_z : FloatProperty(
        name="Z",
        description="The Z orientation vector of the base in planet space.",
        default=0.0,
    )

    # Unimportant details...
    LastEditedById : StringProperty(
        name="LastEditedByID",
        description="LastEditedByID.",
        default="",
        maxlen=1024,
    )
    LastEditedByUsername_value : StringProperty(
        name="LastEditedByUsername",
        description="LastEditedByUsername.",
        default="",
        maxlen=1024,
    )
    original_base_version : IntProperty(
        name="OriginalBaseVersion",
        description="OriginalBaseVersion.",
        default=3
    )

    screenshot_at_x : FloatProperty(
        name="SAX",
        description="The X orientation vector of the screenshot.",
        default=1.0,
    )

    screenshot_at_y : FloatProperty(
        name="SAY",
        description="The Y orientation vector of the screenshot.",
        default=0.0,
    )

    screenshot_at_z : FloatProperty(
        name="SAZ",
        description="The Z orientation vector of the screenshot.",
        default=0.0,
    )

    screenshot_pos_x : FloatProperty(
        name="SPX",
        description="The X pos vector of the screenshot.",
        default=1.0,
    )

    screenshot_pos_y : FloatProperty(
        name="SPY",
        description="The Y pos vector of the screenshot.",
        default=1.0,
    )

    screenshot_pos_z : FloatProperty(
        name="SUZ",
        description="The Z pos vector of the screenshot.",
        default=0.0,
    )

    game_mode : StringProperty(
        name="GameMode",
        description="GameMode.",
        default="Unspecified"
    )

    platform_token : StringProperty(
        name="PlatformToken",
        description="PlatformToken.",
        default=""
    )

    is_reported : BoolProperty(
        name="IsReported",
        description="Is Reported.",
        default=False
    )

    is_featured : BoolProperty(
        name="IsFeatured",
        description="Is Featured.",
        default=False
    )

    room_vis_switch : IntProperty(name="room_vis_switch", default=0)

    def deserialise_from_data(self, nms_data):
        # Start new file
        self.new_file()

        # Start bringing the data in.
        if "GalacticAddress" in nms_data:
            self.string_address = str(nms_data["GalacticAddress"])
        if "BaseType" in nms_data:
            self.string_base_type = str(nms_data["BaseType"]["PersistentBaseTypes"])
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
        if "LastUpdateTimestamp" in nms_data:
            self.string_last_ts = str(nms_data["LastUpdateTimestamp"])
        if "Owner" in nms_data:
            Owner_details = nms_data["Owner"]
            self.string_uid = str(Owner_details.get("UID", ""))
            self.string_ts = str(Owner_details.get("TS", ""))
            self.string_lid = str(Owner_details.get("LID", ""))
            self.string_usn = str(Owner_details.get("USN"))
            self.string_ptk = str(Owner_details.get("PTK"))
        # Extras/Unimportant
        if "LastEditedById" in nms_data:
            self.LastEditedById = str(nms_data["LastEditedById"])
        if "LastEditedByUsername" in nms_data:
            self.LastEditedByUsername_value = str(nms_data["LastEditedByUsername"])
        if "OriginalBaseVersion" in nms_data:
            self.original_base_version = nms_data["OriginalBaseVersion"]
        if "ScreenshotAt" in nms_data:
            self.screenshot_at_x = nms_data["ScreenshotAt"][0]
            self.screenshot_at_y = nms_data["ScreenshotAt"][1]
            self.screenshot_at_z = nms_data["ScreenshotAt"][2]
        if "ScreenshotPos" in nms_data:
            self.screenshot_pos_x = nms_data["ScreenshotPos"][0]
            self.screenshot_pos_y = nms_data["ScreenshotPos"][1]
            self.screenshot_pos_z = nms_data["ScreenshotPos"][2]
        if "GameMode" in nms_data:
            self.game_mode = nms_data["GameMode"]["PresetGameMode"]
        if "PlatformToken" in nms_data:
            self.platform_token = nms_data["PlatformToken"]
        if "IsReported" in nms_data:
            self.is_reported = nms_data["IsReported"]
        if "IsFeatured" in nms_data:
            self.is_featured = nms_data["IsFeatured"]

    def serialise(self, get_presets=False):
        """Export the data in the blender scene to NMS compatible data.
        
        This will slot the data into the clip-board so you can easy copy
        and paste data back and forth between the tool.
        """
        # Try making the address an int, if not it should be a string.
        data = {
            "BaseVersion": 4,
            "OriginalBaseVersion":self.original_base_version,
            "GalacticAddress": python_utils.prefer_int(self.string_address),
            "Position": [
                self.float_pos_x,
                self.float_pos_y,
                self.float_pos_z
            ],
            "Forward": [
                self.float_ori_x,
                self.float_ori_y,
                self.float_ori_z
            ],
            "UserData": 0,
            "LastUpdateTimestamp":python_utils.prefer_int(self.string_last_ts),
            "RID": "",
            "Owner": {
                "UID": self.string_uid,
                "LID": self.string_lid,
                "USN": self.string_usn,
                "PTK": self.string_ptk,
                "TS": python_utils.prefer_int(self.string_ts),
            },
            "Name": self.string_base,
            "BaseType": {"PersistentBaseTypes": self.string_base_type},
            "LastEditedById": self.LastEditedById,
            "LastEditedByUsername": self.LastEditedByUsername_value,
            "ScreenshotAt": [
                self.screenshot_at_x,
                self.screenshot_at_y,
                self.screenshot_at_z
            ],
            "ScreenshotPos": [
                self.screenshot_pos_x,
                self.screenshot_pos_y,
                self.screenshot_pos_z
            ],
            "GameMode":{
                "PresetGameMode": self.game_mode
            },
            "PlatformToken":self.platform_token,
            "IsReported":self.is_reported,
            "IsFeatured":self.is_featured
        }
        # Capture Individual Objects
        data.update(BUILDER.serialise(get_presets=get_presets))

        return data

    # Import and Export Methods ---
    def import_nms_data(self):
        """Import and build a base based on the contents of user clipboard.

        The clipboard should contain a copy of the base data found in the
        No Man's Sky Save Editor.
        """
        # Read clipboard data.
        clipboard_data = bpy.context.window_manager.clipboard
        try:
            nms_import_data = json.loads(clipboard_data)
        except:
            message = (
                "Could not import base data, are you sure you copied "
                "the data to the clipboard? (Ctrl+C from No Man's Sky Save Editor)"
            )
            ShowMessageBox(message=message, title="Import")
            return

        # Start a new file
        self.deserialise_from_data(nms_import_data)
        BUILDER.deserialise_from_data(nms_import_data)


    def export_nms_data(self):
        """Generate data and place it into the user's clipboard.
        
        This generates a flat set of individual base parts for NMS to read.
        All preset information is lost in this process.
        """
        data = self.serialise()
        bpy.context.window_manager.clipboard = json.dumps(data, indent=4)

    # Save and Load Methods ---
    def save_nms_data(self, file_path):
        """Generate data and place it into a json file.
        
        This preserves any presets built in scene.

        Args:
            file_path (str): The path to the json file.
        """
        data = self.serialise(get_presets=True)
        # Add .json if it's not specified.
        if not file_path.endswith(".json"):
            file_path += ".json"
        # Save to file path
        with open(file_path, "w") as stream:
            json.dump(data, stream, indent=4)

    def load_nms_data(self, file_path):
        # First load
        with open(file_path, "r") as stream:
            try:
                save_data = json.load(stream)
            except BaseException:
                message = (
                    "Could not load base data, are you sure you chose the "
                    "correct file? (.json)"
                )
                ShowMessageBox(message=message, title="Import")
                return
        # Build from Data
        self.deserialise_from_data(save_data)
        BUILDER.deserialise_from_data(save_data)

    def new_file(self):
        """Reset's the entire Blender scene to default.
        
        Note:
            * Removes all base information in the Blender properties.
            * Resets the build part order in the part builder.
            * Removes all items with ObjectID, PresetID and NMS_LIGHT properties.
            * Resets the room visibility switch to default.
        """
        BUILDER.clear_caches()
        
        # Remove basic blender default items.
        blend_utils.remove_object("Cube")
        blend_utils.remove_object("Light")
        blend_utils.remove_object("Camera")

        self.string_address = ""
        self.string_base = ""
        self.string_lid = ""
        self.string_ts = ""
        self.string_uid = ""
        self.string_usn = ""
        self.string_ptk = ""
        self.float_pos_x = 0
        self.float_pos_y = 0
        self.float_pos_z = 0
        self.float_ori_x = 0
        self.float_ori_y = 0
        self.float_ori_z = 0
        self.string_last_ts = ""
        self.LastEditedById = ""
        self.original_base_version = 3
        self.LastEditedByUsername_value = ""
        self.screenshot_at_x = 1
        self.screenshot_at_y = 0
        self.screenshot_at_z = 0
        self.screenshot_up_x = 0
        self.screenshot_up_y = 1
        self.screenshot_up_z = 0
        self.game_mode = "Unspecified"
        self.platform_token = ""
        self.is_reported = False
        self.is_featured = False

        # Remove all no mans sky items from scene.
        # Deselect all
        bpy.ops.object.select_all(action="DESELECT")
        # Select NMS Items
        for bpy_object in bpy.data.objects:
            id_check = "ObjectID" in bpy_object
            preset_check = "PresetID" in bpy_object
            light_check = "NMS_LIGHT" in bpy_object
            rig_check = "rig_item" in bpy_object
            if any ([id_check, preset_check, light_check, rig_check]):
                blend_utils.remove_object(bpy_object.name)

        # Reset room vis
        self.room_vis_switch = 0

    def toggle_room_visibility(self):
        """Cycle through room visibilities.
        
        Note:
            Visibility types are...
                0: Normal
                1: Ghosted
                2: Invisible
        """
        # Increment Room Vis
        if self.room_vis_switch < 2:
            self.room_vis_switch += 1
        else:
            self.room_vis_switch = 0

        # Set Shading.
        if self.room_vis_switch in [0, 1, 2]:
            bpy.context.space_data.shading.type = "SOLID"
            bpy.context.scene.render.engine = "BLENDER_EEVEE"


        # Set Hide
        hidden = True
        if self.room_vis_switch in [0, 1]:
            hidden = False

        # Transparency.
        show_transparent = False
        if self.room_vis_switch in [1]:
            show_transparent = True

        # Hide Select.
        hide_select = False
        if self.room_vis_switch in [1]:
            hide_select = True
        
        # Iterate materials for transparency.
        # NOTE: Seems in 2.8 you can't set per object alpha toggling anymore :/
        for material in bpy.data.materials:
            if "transparent" in material.name:
                material.diffuse_color[3] = 0.07 if show_transparent else 1.0
        
        # Iterate object for selection.
        for ob in bpy.data.objects:
            if "ObjectID" in ob:
                if ob["ObjectID"] in GHOSTED_ITEMS:
                    is_preset = ob.get("belongs_to_preset", False)
                    # Normal
                    ob.hide_viewport = hidden
                    # ob.show_transparent = show_transparent
                    if not is_preset:
                        ob.hide_select = hide_select
                    ob.select_set(False)

    def delete(self):
        """Delete the selected object and everything below."""
        # Store selection.
        selected_objects = bpy.context.selected_objects
        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Select an item to delete from the scene.",
                title="Delete"
            )
            return

        for item in selected_objects:
            blend_utils.delete(item)

    def duplicate(self):
        """Snaps one object to another based on selection."""
        # Store selection.
        selected_objects = bpy.context.selected_objects

        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.",
                title="Duplicate"
            )
            return

        # Get Selected item.
        target = blend_utils.get_current_selection()

        if "ObjectID" not in target and "PresetID" not in target:
            message = (
                "This item can not be duplicated via the No Man's Sky tool. "
                "Try using Blender hotkey instead (Shift-D)."
            )
            ShowMessageBox(message=message, title="Duplicate")
            return

        # Part
        if "ObjectID" in target:
            object_id = target["ObjectID"]
            user_data = target["UserData"]
            # Build Item.
            new_item = BUILDER.add_part(object_id, user_data=user_data)
            new_item.select()
        if "PresetID" in target:
            preset_id = target["PresetID"]
            # Build Item.
            new_item = BUILDER.add_preset(preset_id)
            new_item.select()

        # Build Rig if need to.
        if hasattr(new_item, "build_rig"):
            new_item.build_rig()
        # Snap.
        target = BUILDER.get_builder_object_from_bpy_object(target)
        new_item.snap_to(target)

    def duplicate_along_curve(self, distance_percentage):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects

        if len(selected_objects) != 2:
            message = (
                "Make sure you have two items selected. Select the item to"
                " duplicate, then the curve you want to snap to."
            )
            ShowMessageBox(message=message, title="Duplicate Along Curve")
            return {"FINISHED"}

        # Validate gap_distance.
        range_message = "Please choose a value between 0 and 1."
        if distance_percentage <= 0.0:
            ShowMessageBox(message=range_message, title="Duplicate Along Curve")
            return {"FINISHED"}

        if distance_percentage >= 1.0:
            ShowMessageBox(message=range_message, title="Duplicate Along Curve")
            return {"FINISHED"}

        # Figure out selection.
        if "ObjectID" in selected_objects[0] or "PresetID" in selected_objects[0]:
            curve_object = selected_objects[1]
            dup_object = selected_objects[0]
        else:
            curve_object = selected_objects[0]
            dup_object = selected_objects[1]
        
        # Perform duplication along curve.
        curve.duplicate_along_curve(
            BUILDER, dup_object, curve_object, distance_percentage
        )

    def apply_colour(self, colour_index=0, material=None):
        """Gives an item a new colour."""
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.",
                title="Apply Colour"
            )
            return {"FINISHED"}

        # Apply Colour Material.
        for obj in selected_objects:
            _material.assign_material(obj, colour_index, material)

        # Refresh the viewport.
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

    def snap(
            self,
            next_source=False,
            prev_source=False,
            next_target=False,
            prev_target=False):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects
        
        source = None
        target = None
        # If only one item is selected, see if it has a snapped_to variable to
        # use.
        if len(selected_objects) == 1:
            source = bpy.context.view_layer.objects.active
            if "snapped_to" in source:
                target = bpy.data.objects[source["snapped_to"]]
            else:
                message = (
                    "This item has not been snapped to anything. Please select "
                    "the item you want to snap it to"
                )
                ShowMessageBox(message=message, title="Snap")
                return {"FINISHED"}

        # If 2 are selected, use them as the snapping items.
        elif len(selected_objects) == 2:
            target = bpy.context.view_layer.objects.active
            source = [obj for obj in selected_objects if obj != target][0]

        # If otherwise, we should skip and warn the user.
        else:
            message = (
                "Make sure you have two items selected. Select the item you"
                " want to snap to, then the item you want to snap."
            )
            ShowMessageBox(message=message, title="Snap")
            return {"FINISHED"}

        # Perform Snap
        source = BUILDER.get_builder_object_from_bpy_object(source)
        target = BUILDER.get_builder_object_from_bpy_object(target)
        if source and target:
            source.snap_to(
                target,
                next_source=next_source,
                prev_source=prev_source,
                next_target=next_target,
                prev_target=prev_target,
            )


# UI ---
# File Buttons Panel ---
class NMS_PT_file_buttons_panel(Panel):
    bl_idname = "NMS_PT_file_buttons_panel"
    bl_label = "No Man's Sky Base Builder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        first_column = layout.column(align=True)
        button_row = first_column.row(align=True)
        button_row.operator("nms.new_file")
        save_load_row = first_column.row(align=True)
        save_load_row.operator("nms.save_data", icon="FILE_TICK")
        save_load_row.operator("nms.load_data", icon="FILE_FOLDER")
        nms_row = first_column.row(align=True)
        nms_row.operator("nms.import_nms_data", icon="PASTEDOWN")
        nms_row.operator("nms.export_nms_data", icon="COPYDOWN")


# Base Property Panel ---
class NMS_PT_base_prop_panel(Panel):
    bl_idname = "NMS_PT_base_prop_panel"
    bl_label = "Base Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
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


# Snap Panel ---
class NMS_PT_snap_panel(Panel):
    bl_idname = "NMS_PT_snap_panel"
    bl_label = "Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool

        # Split into two columns of equal widths.
        split = layout.split(factor=0.5)
        tools_column, snap_column = (
            split.column(),split.column()
        )

        tools_box = tools_column.box()
        tools_col = tools_box.column(align=True)
        
        tools_col.label(text="Visibility")
        # Room Vis Button.
        label = "Normal"
        if nms_tool.room_vis_switch == 1:
            label = "Ghosted"
        elif nms_tool.room_vis_switch == 2:
            label = "Invisible"

        tools_col.operator(
            "nms.toggle_room_visibility", icon="CUBE", text=label
        )

        tools_col.label(text="Duplicate")
        tools_col.operator("nms.duplicate", icon="DUPLICATE")
        dup_along_curve = tools_col.operator(
            "nms.duplicate_along_curve", icon="CURVE_DATA"
        )
        tools_col.label(text="Delete")
        tools_col.operator("nms.delete", icon="CANCEL")

        # Create Part Count Box.
        part_box = snap_column.box()
        splitter = part_box.split(factor=0.7)
        splitter.label(text="Part Count:")
        part_count = len([obj for obj in bpy.data.objects if "ObjectID" in obj])
        splitter.label(text="{}".format(part_count))

        # Create Snapping box.
        snap_box = snap_column.box()
        snap_col = snap_box.column(align=True)
        snap_col.label(text="Snap")
        snap_op = snap_col.operator("nms.snap", icon="SNAP_ON")

        target_row = snap_col.row(align=True)
        target_row.label(text="Target")
        snap_target_prev = target_row.operator("nms.snap", icon="TRIA_LEFT", text="Prev")
        snap_target_next = target_row.operator("nms.snap", icon="TRIA_RIGHT", text="Next")

        source_row = snap_col.row(align=True)
        source_row.label(text="Source")
        snap_source_prev = source_row.operator("nms.snap", icon="TRIA_LEFT", text="Prev")
        snap_source_next = source_row.operator("nms.snap", icon="TRIA_RIGHT", text="Next")

        # Set Snap Operator assignments.
        # Default
        snap_op.prev_source = False
        snap_op.next_source = False
        snap_op.prev_target = False
        snap_op.next_target = False
        # Previous Target.
        snap_target_prev.prev_source = False
        snap_target_prev.next_source = False
        snap_target_prev.prev_target = True
        snap_target_prev.next_target = False
        # Next Target.
        snap_target_next.prev_source = False
        snap_target_next.next_source = False
        snap_target_next.prev_target = False
        snap_target_next.next_target = True
        # Previous Source.
        snap_source_prev.prev_source = True
        snap_source_prev.next_source = False
        snap_source_prev.prev_target = False
        snap_source_prev.next_target = False
        # Next Source.
        snap_source_next.prev_source = False
        snap_source_next.next_source = True
        snap_source_next.prev_target = False
        snap_source_next.next_target = False

# Colour Panel ---
class NMS_PT_colour_panel(Panel):
    bl_idname = "NMS_PT_colour_panel"
    bl_label = "Colour"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
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
        colour_area = layout.column(align=True)
        enum_row = colour_area.row(align=True)
        enum_row.prop(nms_tool, "material_switch", expand=True)
        colour_row_1 = colour_area.row(align=True)
        colour_row_1.scale_y = 1.3
        colour_row_1.scale_x = 1.3
        for idx in range(16):
            colour_icon = pcoll["{0}_colour".format(idx)]
            colour_op = colour_row_1.operator(
                "nms.apply_colour", text="", icon_value=colour_icon.icon_id
            )
            colour_op.colour_index = idx

# Colour Panel ---
class NMS_PT_logic_panel(Panel):
    bl_idname = "NMS_PT_logic_panel"
    bl_label = "Power and Logic"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        nms_tool = scene.nms_base_tool

        layout = self.layout
        box = layout.box()
        col = box.column()
        col.label(text="Wiring")
        row = col.row()
        row.operator("nms.point", icon="EMPTY_DATA")
        row.operator("nms.connect", icon="PARTICLES")
        divide_row = col.row()
        divide_row.operator("nms.divide", icon="LINCURVE")
        divide_row.operator("nms.split", icon="MOD_PHYSICS")

        col.label(text="Logic")
        logic_row = col.row(align=True)
        logic_row.operator("nms.logic_button")
        logic_row.operator("nms.logic_wall_switch")
        logic_row.operator("nms.logic_prox_switch")
        logic_row.operator("nms.logic_inv_switch")
        logic_row.operator("nms.logic_auto_switch")
        logic_row.operator("nms.logic_floor_switch")
        logic_row.operator("nms.logic_beat_switch")

# Build Panel ---
class NMS_PT_build_panel(Panel):
    bl_idname = "NMS_PT_build_panel"
    bl_label = "Build"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
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
        col = layout.column(align=True)
        col.operator("nms.save_as_preset", icon="SCENE_DATA")
        row = col.row(align=True)
        row.operator("nms.get_more_presets", icon="WORLD_DATA")
        row.operator("nms.open_preset_folder", icon="FILE_FOLDER")
        part_list = layout.template_list(
            "NMS_UL_actions_list",
            "compact",
            context.scene,
            "col",
            context.scene,
            "col_idx"
        )

    
class NMS_UL_actions_list(bpy.types.UIList):
    previous_layout = None
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        self.use_filter_show = True
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Add a category item if the title is specified.
            if item.title:
                layout.label(text=item.title)

            # Draw Parts
            if item.item_type == "parts" and item.description:
                all_parts = [x for x in item.description.split(",") if x]
                part_row = layout.column_flow(columns=3)
                for part in all_parts:
                    operator = part_row.operator(
                        "object.list_build_operator",
                        text=BUILDER.get_nice_name(part),
                    )
                    operator.part_id = part

            # Draw Presets
            if item.item_type == "presets":
                if item.description in preset.Preset.get_presets():
                    # Create Sub layuts
                    build_area = layout.split(factor=0.7)
                    operator = build_area.operator(
                        "object.list_build_operator", text=item.description
                    )
                    edit_area = build_area.split(factor=0.6)
                    edit_operator = edit_area.operator(
                        "object.list_edit_operator", text="Edit"
                    )
                    delete_operator = edit_area.operator(
                        "object.list_delete_operator", text="X"
                    )
                    operator.part_id = item.description
                    edit_operator.part_id = item.description
                    delete_operator.part_id = item.description


class PartCollection(bpy.types.PropertyGroup):
    title : bpy.props.StringProperty()
    description : bpy.props.StringProperty()
    item_type : bpy.props.StringProperty()

def create_sublists(input_list, n=3):
    """Create a list of sub-lists with n elements."""
    total_list = [input_list[x : x + n] for x in range(0, len(input_list), n)]
    # Fill in any blanks.
    last_list = total_list[-1]
    while len(last_list) < n:
        last_list.append("")
    return total_list

def generate_ui_list_data(item_type="parts", pack=None):
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
        for _preset in preset.Preset.get_presets():
            ui_list_data.append(("", _preset))
    else:
        # Packs/Parts
        for category in BUILDER.get_categories(pack=pack):
            ui_list_data.append((category, ""))
            category_parts = BUILDER.get_parts_from_category(
                category,
                pack=pack
            )
            category_parts = sorted(category_parts, key=BUILDER.get_nice_name)
            new_parts = create_sublists(category_parts)
            for part in new_parts:
                joined_list = ",".join(part)
                ui_list_data.append(("", joined_list))
    return ui_list_data


def refresh_ui_part_list(scene, item_type="parts", pack=None):
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
    ui_list_data = generate_ui_list_data(item_type=item_type, pack=pack)
    # Create items with labels and descriptions.
    for i, (label, description) in enumerate(ui_list_data, 1):
        item = scene.col.add()
        item.title = label.title().replace("_", " ")
        item.description = description
        item.item_type = item_type
        item.name = " ".join((str(i), label, description))


# Operators ---
# File Operators ---
class NewFile(bpy.types.Operator):
    bl_idname = "nms.new_file"
    bl_label = "New"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.new_file()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class SaveData(bpy.types.Operator):
    bl_idname = "nms.save_data"
    bl_label = "Save"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.save_nms_data(self.filepath)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class LoadData(bpy.types.Operator):
    bl_idname = "nms.load_data"
    bl_label = "Load"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.load_nms_data(self.filepath)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ImportData(bpy.types.Operator):
    bl_idname = "nms.import_nms_data"
    bl_label = "Import NMS"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.import_nms_data()
        return {"FINISHED"}


class ExportData(bpy.types.Operator):
    bl_idname = "nms.export_nms_data"
    bl_label = "Export NMS"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.export_nms_data()
        return {"FINISHED"}


# Tool Operators ---
class ToggleRoom(bpy.types.Operator):
    bl_idname = "nms.toggle_room_visibility"
    bl_label = "Toggle Room Visibility: Normal"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.toggle_room_visibility()
        return {"FINISHED"}


class SaveAsPreset(bpy.types.Operator):
    """Save the current scene contents as a new Preset"""
    bl_idname = "nms.save_as_preset"
    bl_label = "Save As Preset"
    preset_name: bpy.props.StringProperty(name="Preset Name")

    def execute(self, context):
        # Save Preset.
        BUILDER.save_preset_to_file(self.preset_name)
        # Refresh Preset List.
        scene = context.scene
        nms_tool = scene.nms_base_tool
        if nms_tool.enum_switch == {"PRESETS"}:
            refresh_ui_part_list(scene, "presets")
        # Reset string variable.
        self.preset_name = ""
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class GetMorePresets(bpy.types.Operator):
    """Load the No Man's Sky Presets web page to find more community presets."""
    bl_idname = "nms.get_more_presets"
    bl_label = "Get More Presets..."

    def execute(self, context):
        # Load web page.
        webbrowser.open_new("https://charliebanks.github.io/nms-base-builder-presets/")
        return {"FINISHED"}

class OpenPresetFolder(bpy.types.Operator):
    """Open the folder containing your presets."""
    bl_idname = "nms.open_preset_folder"
    bl_label = "Open Preset Folder"

    def execute(self, context):
        # Load web page.
        os.startfile(PRESET_PATH)
        return {"FINISHED"}

# List Operators ---
class ListBuildOperator(bpy.types.Operator):
    """Build the specified item."""

    bl_idname = "object.list_build_operator"
    bl_label = "Simple Object Operator"
    part_id: StringProperty()

    def execute(self, context):
        # Get Selection
        selection = blend_utils.get_current_selection()

        # Build item
        if self.part_id in preset.Preset.get_presets():
            new_item = BUILDER.add_preset(self.part_id)
        else:
            new_item = BUILDER.add_part(self.part_id)
            if hasattr(new_item, "build_rig"):
                new_item.build_rig()

        # Make this item the selected.
        new_item.select()

        # If there was a previous selection, snap the new item to it.
        if selection:
            builder_selection = BUILDER.get_builder_object_from_bpy_object(
                selection
            )
            if builder_selection:
                new_item.snap_to(builder_selection)
        return {"FINISHED"}


class ListEditOperator(bpy.types.Operator):
    """Edit the specified preset."""

    bl_idname = "object.list_edit_operator"
    bl_label = "Edit Preset"
    part_id: StringProperty()

    def execute(self, context):
        nms_tool = context.scene.nms_base_tool
        if self.part_id in preset.Preset.get_presets():
            nms_tool.new_file()
            preset.Preset(
                preset_id=self.part_id,
                builder_object=BUILDER,
                create_control=False,
                apply_shader=False,
                build_rigs=True
            )
            BUILDER.build_rigs()
            BUILDER.optimise_control_points()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class ListDeleteOperator(bpy.types.Operator):
    """Delete the specified preset."""

    bl_idname = "object.list_delete_operator"
    bl_label = "Delete"
    part_id: StringProperty()

    def execute(self, context):
        scene = context.scene
        nms_tool = context.scene.nms_base_tool
        if self.part_id in preset.Preset.get_presets():
            preset.Preset.delete_preset(self.part_id)
            if nms_tool.enum_switch == {"PRESETS"}:
                refresh_ui_part_list(scene, "presets")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

# Tool Operators ---
class Duplicate(bpy.types.Operator):
    bl_idname = "nms.duplicate"
    bl_label = "Duplicate"
    

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.duplicate()
        return {"FINISHED"}

class Delete(bpy.types.Operator):
    bl_idname = "nms.delete"
    bl_label = "Delete"

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.delete()
        return {"FINISHED"}

class DuplicateAlongCurve(bpy.types.Operator):
    bl_idname = "nms.duplicate_along_curve"
    bl_label = "Duplicate Along Curve"
    distance_percentage: bpy.props.FloatProperty(
        name="Distance Percentage Between Item."
    )

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        nms_tool.duplicate_along_curve(
            distance_percentage=self.distance_percentage
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
        
class ApplyColour(bpy.types.Operator):
    bl_idname = "nms.apply_colour"
    bl_label = "Apply Colour"
    colour_index: IntProperty(default=0)

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        material = nms_tool.material_switch
        nms_tool.apply_colour(
            colour_index=self.colour_index, material=material
        )
        return {"FINISHED"}


class Snap(bpy.types.Operator):
    bl_idname = "nms.snap"
    bl_label = "Snap"

    next_source : BoolProperty()
    prev_source : BoolProperty()
    next_target : BoolProperty()
    prev_target : BoolProperty()

    def execute(self, context):
        scene = context.scene
        nms_tool = scene.nms_base_tool
        kwargs = {
            "next_source": self.next_source,
            "prev_source": self.prev_source,
            "next_target": self.next_target,
            "prev_target": self.prev_target
        }
        nms_tool.snap(**kwargs)
        return {"FINISHED"}

# Logic Operators ---
class Point(bpy.types.Operator):
    bl_idname = "nms.point"
    bl_label = "New Point"

    def execute(self, context):
        # Get current selection.
        selection = blend_utils.get_current_selection()

        # Don't stack multiple for multiple clicks
        if context.scene.cursor.location == selection.location:
            return {"CANCELLED"}

        # Create a new point at the cursor.
        point = line.Line.create_point(BUILDER, name="ARBITRARY_POINT")
        point.location = context.scene.cursor.location

        # If another powerline was already selected, connect it
        if selection and "rig_item" in selection:
            line_object = selection.get("power_line", "U_POWERLINE").split(".")[0]
            power_line = BUILDER.add_part(line_object, build_rigs=False)
            # Create controls.
            power_line.build_rig(
                start=selection,
                end=point
            )

        # Now select the new point.
        blend_utils.select(point)
        return {"FINISHED"}

class Connect(bpy.types.Operator):
    bl_idname = "nms.connect"
    bl_label = "Connect"

    def execute(self, context):
        # Validate selection.
        selected_objects = bpy.context.selected_objects
        if len(selected_objects) != 2:
            message = (
                "Make sure you have two electric points selected."
            )
            ShowMessageBox(message=message, title="Connect")
            return {"FINISHED"}

        # Build and perform connection .
        start = selected_objects[0]
        end = selected_objects[1]

        start = BUILDER.get_builder_object_from_bpy_object(start)
        end = BUILDER.get_builder_object_from_bpy_object(end)
        # Validate points.
        start, end = line.Line.generate_control_points(start, end, BUILDER)
        if not start and not end:
            message = (
                "These two items are not compatible to connect."
            )
            ShowMessageBox(message=message, title="Connect")
            return {"FINISHED"}

        start_name = start.name
        end_name = end.name
        # Re-obtain objects
        start = blend_utils.get_item_by_name(start_name)
        end = blend_utils.get_item_by_name(end_name)
        # Create new power line.
        line_object = "U_POWERLINE"
        if "power_line" in start:
            line_object = start["power_line"].split(".")[0]
        power_line = BUILDER.add_part(line_object, build_rigs=False)
        # Create controls.
        power_line.build_rig(
            start=start,
            end=end
        )
        return {"FINISHED"}

class Divide(bpy.types.Operator):
    bl_idname = "nms.divide"
    bl_label = "Divide"

    def execute(self, context):
        # Get Selected item.
        target = blend_utils.get_current_selection()
        
        # Validate
        invalid_message = "Make sure you have a powerline item selected."
        title = "Split"
        if not target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        if "ObjectID" not in target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        valid_parts = ["U_POWERLINE", "U_PIPELINE", "U_PORTALLINE"]
        if target["ObjectID"] not in valid_parts:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        
        # Perform split.
        power_line = BUILDER.get_builder_object_from_bpy_object(target)
        power_line.divide()
        return {"FINISHED"}


class Split(bpy.types.Operator):
    bl_idname = "nms.split"
    bl_label = "Split"

    def execute(self, context):
        # Get Selected item.
        target = blend_utils.get_current_selection()

        # Validate
        invalid_message = "Make sure you have a powerline item selected."
        title = "Split"
        if not target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        if "ObjectID" not in target:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}
        valid_parts = ["U_POWERLINE", "U_PIPELINE", "U_PORTALLINE"]
        if target["ObjectID"] not in valid_parts:
            ShowMessageBox(message=invalid_message, title=title)
            return {"FINISHED"}

        # Perform split.
        power_line = BUILDER.get_builder_object_from_bpy_object(target)
        power_line.split()
        return {"FINISHED"}


class LogicButton(bpy.types.Operator):
    bl_idname = "nms.logic_button"
    bl_label = "BTN"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        # Build button.
        button = BUILDER.add_part("U_SWITCHBUTTON")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)

        # Select new item.
        button.select()
        return {"FINISHED"}

class LogicWallSwitch(bpy.types.Operator):
    bl_idname = "nms.logic_wall_switch"
    bl_label = "SWITCH"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_SWITCHWALL")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}

class LogicProxSwitch(bpy.types.Operator):
    bl_idname = "nms.logic_prox_switch"
    bl_label = "PROX"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_SWITCHPROX")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}

class LogicInvSwitch(bpy.types.Operator):
    bl_idname = "nms.logic_inv_switch"
    bl_label = "INV"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_TRANSISTOR1")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}

class LogicAutoSwitch(bpy.types.Operator):
    bl_idname = "nms.logic_auto_switch"
    bl_label = "AUTO"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_TRANSISTOR2")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}

class LogicFloorSwitch(bpy.types.Operator):
    bl_idname = "nms.logic_floor_switch"
    bl_label = "FLOOR"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("U_SWITCHPRESS")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}

class LogicBeatSwitch(bpy.types.Operator):
    bl_idname = "nms.logic_beat_switch"
    bl_label = "BEAT"

    def execute(self, context):
        # Get Selected item.
        selection = blend_utils.get_current_selection()
        button = BUILDER.add_part("BYTEBEATSWITCH")
        # Snap to selection.
        if selection:
            selection = BUILDER.get_builder_object_from_bpy_object(selection)
            button.snap_to(selection)
        # Select new item.
        button.select()
        return {"FINISHED"}

# We can store multiple preview collections here,
# however in this example we only store "main"
preview_collections = {}

# Plugin Registration ---

classes = (
    NMSSettings, 
    
    Snap,
    Point,
    Connect,
    Divide,
    Split,

    LogicButton,
    LogicWallSwitch,
    LogicProxSwitch,
    LogicInvSwitch,
    LogicAutoSwitch,
    LogicFloorSwitch,
    LogicBeatSwitch,

    ApplyColour,
    Duplicate,
    DuplicateAlongCurve,
    Delete,
    
    SaveAsPreset,
    GetMorePresets,
    OpenPresetFolder,
    ToggleRoom,
    
    NewFile, 
    SaveData,
    LoadData,

    ExportData,
    ImportData,
    
    PartCollection,

    ListDeleteOperator,
    ListEditOperator,
    ListBuildOperator,
    NMS_UL_actions_list,

    NMS_PT_file_buttons_panel,
    NMS_PT_base_prop_panel,
    NMS_PT_snap_panel,
    NMS_PT_colour_panel,
    NMS_PT_logic_panel,
    NMS_PT_build_panel
)

def register():
    # Load Dependencies.
    obj_addon = "io_scene_obj"
    blend_utils.load_plugin(obj_addon)

    # Ensure User data folder structure exists
    for data_path in [USER_PATH, PRESET_PATH]:
        if not os.path.exists(data_path):
            os.makedirs(data_path)

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
            "IMAGE",
        )

    preview_collections["main"] = pcoll

    # Register Plugin
    for _class in classes:
        bpy.utils.register_class(_class)
    bpy.types.Scene.nms_base_tool = PointerProperty(type=NMSSettings)
    bpy.types.Scene.col = bpy.props.CollectionProperty(type=PartCollection)
    bpy.types.Scene.col_idx = bpy.props.IntProperty(default=0)

def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    for _class in reversed(classes):
        bpy.utils.unregister_class(_class)
    del bpy.types.Scene.nms_base_tool


if __name__ == "__main__":
    register()
