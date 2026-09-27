"""The Save Manager sidebar panel, and the save manager UI itself.

draw_save_manager() holds the whole UI. The "Save Manager" dropdown in the
viewport header (presentation/save_manager_menu.py) draws the same function
into its popover, so the sidebar and the dropdown cannot drift apart.
"""

import bpy
from bpy.types import Panel

from .. import addon_preferences, icons
from .save_editor_utils import BaseType
from .save_manager import SaveManager


def get_save_data(context):
    """The save editor's property group, or None if it is not registered yet."""
    return getattr(context.scene, "nms_save_data", None)


def draw_pinned_base(container, save_data, base_props):
    """Draw the pinned base UI section if a base is pinned."""
    if not save_data.pinned_base_check:
        return

    pinned_base_type = save_data.get_base_type_string(save_data.pinned_base_type)
    pinned_box = container

    pinned_content_row = pinned_box.row(align=False)
    pinned_text_col = pinned_content_row.column(align=False)
    pinned_buttons_col = pinned_content_row.column(align=True)

    pinned_text_col.label(
        text=f"{base_props.string_base} ({pinned_base_type})", icon="PINNED"
    )
    pinned_text_condensed_column = pinned_text_col.column(align=True)
    pinned_text_condensed_column.label(
        text=f"{save_data.pinned_save_slot_name}, (...{save_data.pinned_save_account[-3:]})"
    )

    pinned_buttons_col.scale_x = 0.7
    pinned_buttons_col.operator(
        "object.nms_unpin_base", icon="UNPINNED", text=f"Unpin {pinned_base_type}"
    )
    pinned_buttons_col.operator(
        "object.import_pinned_base", icon="IMPORT", text="Import from Save"
    )

    pinned_export_button_row = pinned_box.row(align=False)
    pinned_export_button_row.operator(
        "object.export_pinned_base", icon="FILE_TICK", text="Export to Save"
    )
    pinned_export_button_backup_row = pinned_export_button_row.row(align=True)
    pinned_export_button_backup_row.scale_x = 0.7
    pinned_export_button_backup_row.operator(
        "object.make_pinned_savefile_backup",
        icon="COLLECTION_NEW",
        text="Backup Save files",
    )
    
def draw_base_picker(container, save_data):
    
    save_folder_path = addon_preferences.get_save_folder_path()
    
    # Make a separate section to display elements related to selecting bases.
    save_folder_box = container
    sf_column = save_folder_box.column(align=True)
    sf_enable_row = sf_column.row(align=True)
    sf_enable_row.label(text="Select Save")

    # Game Pass accounts are found on their own, so they can be used without a Steam save folder
    is_save_folder_valid = save_data.validate_save_folder(save_folder_path)

    # This row will contain a field where location of save folder is displayed.
    if save_data.check_plugin_enabled and (is_save_folder_valid or save_data.has_accounts()):
        # Button to choose path to save folder.
        sf_enable_row.operator(
            "object.nms_select_save_folder", text="", icon="FILE_FOLDER"
        )

    # A button to enable the save editor, this will also install additional
    # dependencies required when pressed.
    sf_enable_row.separator()
    sf_enable_button_row = sf_enable_row.row(align=True)
    sf_enable_button_row.scale_x = 0.7 if not save_data.check_plugin_enabled else 1.0
    sf_enable_icon = "TRIA_DOWN" if not save_data.check_plugin_enabled else "TRIA_UP"
    sf_enable_text = "Enable" if not save_data.check_plugin_enabled else ""
    sf_enable_button_row.prop(
        save_data, "check_plugin_enabled", icon=sf_enable_icon, text=sf_enable_text
    )

    # Everything below is the Select Save section, which only applies once the
    # save editor is switched on.
    if not save_data.check_plugin_enabled:
        return

    if not is_save_folder_valid and not save_data.has_accounts():
        sf_column.separator()
        select_folder_info_col = sf_column.column(align=True)
        select_folder_info_col.scale_y = 0.8
        select_folder_info_col.label(text=" Save Folder should end with")
        select_folder_info_col.label(text=r' path like : "...\HelloGames\NMS"')
        sf_column.separator()
        select_folder_button_col = sf_column.column(align=True)
        select_folder_button_col.alert = True
        select_folder_button_col.operator(
            "object.nms_select_save_folder",
            text="Select Save Folder",
            icon="FILE_FOLDER",
        )
        return

    sf_column.separator()
    # Display list of accounts, will display steam ids for recognition.
    sf_column.label(text="Account / Save Slot")
    sf_column.prop(save_data, "nms_account_selected", icon="COMMUNITY")
    # Display save slots present within an account.
    sf_column.prop(save_data, "nms_save_slot", icon="LINENUMBERS_ON")

    # Section where bases can be selected to import/update/pin. This section
    # will only be visible when the base list has been loaded.
    if not save_data.is_base_data_loaded():
        return

    # Display backup buttons when a slot is selected.
    base_type = save_data.get_base_type_string(save_data.nms_base_type)
    backup_row = sf_column.row(align=True)
    backup_row.operator(
        "object.make_savefile_backup", icon="COLLECTION_NEW", text="Backup Saves"
    )
    backup_row.operator(
        "object.open_backup_folder", icon="FOLDER_REDIRECT", text="Open Backup Folder"
    )

    sf_column.separator()
    sf_column.label(text=f"\U0001F4E6 Total Parts : {save_data.get_total_parts_count()}")
    se_column = sf_column.column(align=True)
    se_column.label(text="Base Type:")
    # Radio buttons to select type of base.
    base_type_row = se_column.row(align=True)
    base_type_row.prop(save_data, "nms_base_type", expand=True, text="base type")
    se_column.separator()

    # List of bases/corvettes.
    se_column.label(text=f"{base_type} Selected:")

    # Show the base list in red when no base/corvette is selected.
    base_index_row = se_column.row(align=True)
    base_index_row.alert = not SaveManager.is_base_selected

    if not SaveManager.is_base_selected:
        # List of bases for selection.
        base_index_row.prop(
            save_data, "nms_base_index", text="", icon="GEOMETRY_SET"
        )
        return

    # List of bases for selection.
    base_index_row.prop(save_data, "nms_base_index", text="")

    # Display buttons when a base is selected from the list.
    if save_data.nms_base_type != BaseType.EXTERNAL_BASE:
        # Pin a base without importing it to the scene, so that save data can
        # be updated to the location marked by it.
        base_index_pin_row = base_index_row.row(align=True)
        base_index_pin_row.scale_x = 0.6
        base_index_pin_row.operator(
            "object.nms_pin_base", icon="PINNED", text=" Pin for easy-access"
        )

    se_column.separator()
    import_export_row = se_column.row(align=True)
    # Import button, this button will import the base to the scene.
    import_export_row.operator(
        "object.nms_import_base_from_save", icon="IMPORT", text="Import from Save"
    )

    if save_data.nms_base_type != BaseType.EXTERNAL_BASE:
        import_export_row.operator(
            "object.nms_export_base_to_save", icon="EXPORT", text="Export to Save"
            )


def draw_save_manager(layout, context):
    """The entire save manager UI, drawn into whatever layout is passed in.

    Shared by the sidebar panel below and the header dropdown in
    presentation/save_manager_menu.py, so it takes a layout rather than
    reading self.layout off a particular panel.
    """
    save_data = get_save_data(context)
    base_props = getattr(context.scene, "nms_base_tool", None)
    save_folder_path = addon_preferences.get_save_folder_path()

    if save_data is None or base_props is None or save_folder_path is None:
        layout.label(text="Save Manager unavailable", icon="ERROR")
        return

    # Display data related to a pinned base on top if there is any within a
    # blend file.
    if save_data.pinned_base_check:
        draw_pinned_base(layout.box(),save_data,base_props)

    draw_base_picker(layout.box(), save_data)


# Save Editor Panel ---
class NMS_PT_save_editor_panel(Panel):
    bl_idname = "NMS_PT_save_editor_panel"
    bl_label = "💾 Save Manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        draw_save_manager(self.layout, context)
