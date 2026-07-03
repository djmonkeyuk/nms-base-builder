import bpy
from bpy.types import Panel

# Base Property Panel ---
class NMS_PT_batch_tools_panel(Panel):
    bl_idname = "NMS_PT_batch_tools_panel"
    bl_label = "Batch Tools"
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
        batch_tool = scene.nms_batch_tool
        
        top_row = layout.row(align = True)
        select_box = top_row.box()
        #select_box.scale_x = 1.3333
        select_box.label(text = "Batch Select", icon = "SELECT_INTERSECT")
        select_col = select_box.column(align = True)
        select_col.label(text = "Select objects with")
        select_col.operator("object.nms_select_same_colors", text = "Same Colour", icon = "MOD_SOFT")
        select_col.operator("object.nms_select_same_objects", text = "Same ObjectID", icon = "CON_SIZELIKE")
        
        more_options_box =  top_row.box()
        more_options_box.label(text = "More Options",)
        more_options_column = more_options_box.column(align = True)
        more_options_column.operator("object.nms_select_duplicates", text = "Find Duplicates", icon = "BRUSH_DATA")
        more_options_column.operator("object.nms_batch_select_random", text = "Select Random", icon = "MOD_NOISE")
        more_options_column.operator("object.nms_batch_select_pattern", text = "Select Pattern", icon = "MOD_OCEAN")
        
        batch_replace_box = layout.box()
        batch_replace_box.label(text = "Batch Replace", icon = "GROUP_VERTEX")
        batch_replace_col = batch_replace_box.column(align = True)
        #batch_replace_col.label(text = "Replace with :")
        batch_replace_col.row(align = True).prop(batch_tool,"nms_batch_replace_type", expand = True)
        batch_replace_col.separator()
        if batch_tool.nms_batch_replace_type == "target":
            batch_replace_col.label(text = "Replace with a target object")
            batch_replace_col.prop(batch_tool,"target_object", text = "")
        else :
            batch_replace_col.label(text = "Replace with ObjectId")
            batch_replace_col.prop(batch_tool,"object_id", text = "")
        batch_replace_col.separator()
        batch_replace_col.operator("object.nms_batch_replace_target", text = "Batch Replace", icon = "CON_FOLLOWPATH")