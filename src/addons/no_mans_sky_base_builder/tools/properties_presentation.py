import bpy
from bpy.types import Panel

# Base Property Panel ---
class NMS_PT_base_prop_panel(Panel):
    bl_idname = "NMS_PT_base_prop_panel"
    bl_label = "Properties"
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
        
        #properties = context.scene.nms_properties
        properties = context.scene.nms_properties
        
        properties_box = layout.box()
        
        properties_column = properties_box.column(align=True)
        properties_column.label(text = "Base Properties")
        base_prop_split = properties_column.split(factor = 0.3)
        base_label_col = base_prop_split.column(align = True)
        base_label_col.label(text = "Base Name :")
        base_label_col.label(text = "User Data :")
        base_field_col = base_prop_split.column(align = True)
        base_field_col.prop(nms_tool, "string_base", text = "")
        base_field_col.prop(nms_tool, "string_userdata", text = "")
        
        #
        #properties_column.prop(nms_tool, "string_address")
        
        
        #curve tools
        if properties.show_gap_edit_field: # and properties.active_curve_is_highlighted()
            active_curve_box = layout.box()
            active_curve_box_col = active_curve_box.column(align = False)
            active_curve_box_col.label(text = "Edit Active-Curve parameters", icon = "NORMALIZE_FCURVES")
            
            active_curve_box_col_label_split = active_curve_box_col.split(factor = 0.7)
            active_curve_box_col_label, active_curve_box_col_delete = (active_curve_box_col_label_split.column(), active_curve_box_col_label_split.column())
            active_curve_box_col_label.label(text = f"Target : {properties.active_curve_name}")
            active_curve_box_col_delete.operator("object.nms_curve_delete", icon="TRASH",text = "Delete Curve and Children")
            #active_curve_box_col.separator()
            
            if properties.selected_curve_object_is_parent:
                curve_params_split = active_curve_box_col.split(factor=0.5)
                curve_gap_row, curve_radius_row = (curve_params_split.column(align = True), curve_params_split.column(align = True))
                curve_gap_row.label(text = "Number of Objects")
                curve_gap_row.label(text = "Objects Size")
                curve_radius_row.alert = True
                #Text fields for editing curv related params
                curve_radius_row.prop(properties,"active_curve_number_of_objects",text = "")
                curve_radius_row.prop(properties,"active_curve_radius_multiplier",text = "")
                active_curve_box_col.separator()
                show_box_buttons_row = active_curve_box_col.row(align = True)
                show_box_buttons_row.operator("object.nms_curve_break_apart", icon="UNLINKED",text = "Unlink Curve")
                show_box_buttons_row.operator("object.nms_select_children_of_curve", icon="MOD_OUTLINE",text = "Select Children")
                
            else :
                show_box_buttons_row = active_curve_box_col.row(align = True)
                show_box_buttons_row.operator("object.nms_selecte_object_parent_curve", icon="MOD_ENVELOPE",text = "Select Parent")
        
        """if properties.active_object is not None or True:
            active_object = properties.active_object
            object_box = layout.box()
            transformation_box = object_box.column(align = True)
            transformation_box.label(text = "Object Properties")
            transformation_box.label(text = active_object.name,  icon = "PROPERTIES")
            transformation_box.separator()
            pos_rot_row = transformation_box.row(align = True)
            
            padding_1 = pos_rot_row.row()
            padding_1.scale_x = 0.2
            padding_1.label(text = "")
        
            pos_col = pos_rot_row.column(align = True)
            pos_lable_val_split = pos_col.split(factor=0.15)
            pos_label_col = pos_lable_val_split.column(align=True)
            pos_val_col = pos_lable_val_split.column(align=True)
            
            pos_label_col.label(text = "", icon = "OBJECT_ORIGIN")
            pos_label_col.label(text = "X:")
            pos_label_col.label(text = "Y:")
            pos_label_col.label(text = "Z:")
            pos_val_col.label(text = "Position")
            pos_val_col.prop(nms_tool, "string_base",text = "")
            pos_val_col.prop(nms_tool, "string_base",text = "")
            pos_val_col.prop(nms_tool, "string_base",text = "")
            
            padding = pos_rot_row.row()
            padding.scale_x = 0.25
            padding.label(text = "")
        
            rot_col = pos_rot_row.column(align = True)
            rot_lable_val_split = rot_col.split(factor=0.15)
            rot_label_col = rot_lable_val_split.column(align=True)
            rot_val_col = rot_lable_val_split.column(align=True)
            
            rot_label_col.label(text = "", icon = "ORIENTATION_GIMBAL")
            rot_label_col.label(text = "X:")
            rot_label_col.label(text = "Y:")
            rot_label_col.label(text = "Z:")
            rot_val_col.label(text = "Rotation")
            rot_val_col.prop(nms_tool, "string_base",text = "")
            rot_val_col.prop(nms_tool, "string_base",text = "")
            rot_val_col.prop(nms_tool, "string_base",text = "")
            
            padding = pos_rot_row.row()
            padding.scale_x = 0.2
            padding.label(text = "")
            
            transformation_box.separator()
            scale_row = transformation_box.row(align = True)
            scale_row.label(text = "", icon = "DRIVER_DISTANCE")#
            scale_row.label(text = " Scale")
            scale_prop_row = scale_row.row()
            scale_prop_row.scale_x = 1.6
            scale_prop_row.prop(nms_tool, "string_base",text = "")
            scale_row.label(text = "")"""