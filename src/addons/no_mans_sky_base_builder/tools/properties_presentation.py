import bpy
from bpy.types import Panel



# Base Property Panel ---
class NMS_PT_base_prop_panel(Panel):
    bl_idname = "NMS_PT_base_prop_panel"
    bl_label = "📋 Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
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
        properties_column.label(text = "Base Properties", icon = "HOME")
        base_prop_split = properties_column.split(factor = 0.3)
        base_label_col = base_prop_split.column(align = True)
        base_label_col.label(text = "Base Name :")
        base_label_col.label(text = "User Data :")
        base_field_col = base_prop_split.column(align = True)
        base_field_col.prop(nms_tool, "string_base", text = "")
        base_field_col.prop(nms_tool, "string_userdata", text = "")

