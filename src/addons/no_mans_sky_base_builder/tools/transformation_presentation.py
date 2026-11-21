import bpy
from bpy.types import Panel

from .. import icons


# Transformation Panel ---
class NMS_PT_transformation_panel(Panel):
    bl_idname = "NMS_PT_transformation_panel"
    bl_label = "⛬ Transformations"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        properties = context.scene.nms_properties
        transformation = context.scene.nms_transformation
        active_object = context.view_layer.objects.active

        # with nothing active the fields show greyed out zeros instead
        has_active = active_object is not None
        location_owner, location_prop = (active_object, "location") if has_active else (transformation, "placeholder_vector")
        rotation_owner, rotation_prop = (active_object, "rotation_euler") if has_active else (transformation, "placeholder_vector")

        transformations_box = layout.box()
        transformations_box.enabled = has_active
        transformations_row = transformations_box.row(align = True)
        title_col = transformations_row.column(align = True)
        values_col = transformations_row.column(align = True)
        values_col.scale_x = 1.5
        paste_col = transformations_row.column(align = True)

        title_col.label(text = "Position")
        location_row = values_col.row(align = True)
        for index in range(3):
            location_row.prop(location_owner, location_prop, index=index, text = "")
        paste_col.operator("object.nms_paste_location", icon="PASTEDOWN", text = "")

        title_col.label(text = "Rotation")
        rotation_row = values_col.row(align = True)
        for index in range(3):
            rotation_row.prop(rotation_owner, rotation_prop, index=index, text = "")
        paste_col.operator("object.nms_paste_rotation", icon="PASTEDOWN", text = "")

        title_col.label(text = "Scale")
        values_col.row(align = True).prop(transformation, "uniform_scale", text = "")
        paste_col.operator("object.nms_paste_scale", icon="PASTEDOWN", text = "")

        values_col.separator()
        copy_paste_row = values_col.row(align = True)
        copy_paste_row.operator("object.nms_copy_transformations", icon="COPYDOWN", text = "Copy")
        copy_paste_row.operator("object.nms_paste_transformations", icon="PASTEDOWN", text = "Paste")
        copy_paste_row.operator("object.nms_reset_transformations", icon="DECORATE_OVERRIDE", text = "Reset")

        if has_active and properties.show_gap_edit_field:
            self.draw_active_curve(layout, properties)

    @staticmethod
    def draw_active_curve(layout, properties):
        curve_icon = icons.get_icons_pscroll()["curve"]

        active_curve_box = layout.box()
        active_curve_box_col = active_curve_box.column(align = False)
        active_curve_box_col.label(text = "Edit Active-Curve Parameters", icon_value = curve_icon.icon_id)

        active_curve_box_col_label_split = active_curve_box_col.split(factor = 0.7)
        active_curve_box_col_label, active_curve_box_col_delete = (active_curve_box_col_label_split.column(), active_curve_box_col_label_split.column())
        active_curve_box_col_label.label(text = f"Target : {properties.active_curve_name}")
        active_curve_box_col_delete.operator("object.nms_curve_delete", icon="TRASH",text = "Delete Curve and Children")

        if properties.selected_curve_object_is_parent:
            curve_params_split = active_curve_box_col.split(factor=0.5)
            curve_gap_row, curve_radius_row = (curve_params_split.column(align = True), curve_params_split.column(align = True))
            curve_gap_row.label(text = "Number of Objects")
            curve_gap_row.label(text = "Objects Size")
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
