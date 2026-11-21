import bpy
from bpy.types import Panel

from .. import icons


# Base Property Panel ---
class NMS_PT_batch_tools_panel(Panel):
    bl_idname = "NMS_PT_batch_tools_panel"
    bl_label = "📦 Batch Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'} 

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        batch_column = layout.column(align = True)
        top_row = batch_column.row(align = True)
        select_box = top_row.box()
        select_col = select_box.column(align = True)
        select_col.label(text = "Select objects with")
        select_color_row = select_col.row(align = True)
        select_color_row.operator("object.nms_select_same_colors", text = "Same Colour", icon = "MOD_SOFT")
        # same colour on any part, not only the same part
        select_color_row.operator("object.nms_select_all_same_colors", text = "", icon = "TEXTURE")
        select_col.operator("object.nms_select_same_objects", text = "Same ObjectID", icon = "CON_SIZELIKE")
        select_col.operator("object.nms_select_all_groups", text = "Select all Groups", icon = "OUTLINER_OB_GROUP_INSTANCE")

        more_options_box = top_row.box()
        more_options_column = more_options_box.column(align = True)
        more_options_column.label(text = "Selection Tools")
        more_options_column.operator("object.nms_select_duplicates", text = "Find Duplicates", icon = "BRUSH_DATA")
        more_options_column.operator("object.nms_batch_select_random", text = "Select Random", icon = "MOD_NOISE")
        more_options_column.operator("object.nms_batch_select_pattern", text = "Select Pattern", icon = "MOD_OCEAN")

        # the replace options are in the operator's dialog
        batch_replace_box = batch_column.box().column(align = True)
        batch_replace_box.label(text = "Batch Replace")
        batch_replace_box.operator("object.nms_batch_replace_target", text = "Batch Replace", icon = "GROUP_VERTEX")