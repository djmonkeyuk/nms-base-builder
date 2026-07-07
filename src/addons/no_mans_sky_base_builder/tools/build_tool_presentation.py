import bpy
from bpy.types import Panel


# Snap Panel ---
class NMS_PT_tools_panel(Panel):
    bl_idname = "NMS_PT_snap_panel"
    bl_label = "🛠️ Builder Tools"
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
        scene = context.scene
        nms_tool = scene.nms_base_tool
        build_tool = context.scene.nms_build_tool

        # Split into two columns of equal widths.
        #split = layout.split(factor=0.5)
        #tools_column, snap_column = (split.column(align = True), split.column(align = True))
        build_tools_col = layout.column(align = True)
        tools_row = build_tools_col.row(align = True)
        tools_column = tools_row.column(align = True)
        tools_column.scale_x = 1.3333
        snap_column = tools_row.column(align = True)

        # Create Part Count Box.
        part_box = tools_column.box()
        splitter = part_box.split(factor=0.7)
        splitter.label(text="Part Count:" )# , icon = "GEOMETRY_NODES"
        part_count = len([obj for obj in bpy.data.objects if "ObjectID" in obj])
        splitter.label(text="{}".format(part_count))

        tools_box = tools_column.box()
        tools_col = tools_box.column()

        tools_col.label(text="Common Tools")
        tools_col.operator("object.nms_duplicate", icon="DUPLICATE")
        tools_col.operator("object.nms_delete", icon="TRASH")
        tools_col.label(text="Curve")
        tools_col.operator("object.nms_duplicate_along_curve", icon="MOD_DASH")
        

        # Create Snapping box.
        snap_box = snap_column.box()
        snap_col = snap_box.column(align=True)
        
        snap_button_row = snap_col.row(align = True)
        snap_button_split = snap_button_row.split(factor=0.23333)
        snap_label_col, snap_button_container = (snap_button_split.column(align = True), snap_button_split.column(align = True))
        
        snap_label_col.label(text="Snap")
        snap_label_col.separator()
        snap_label_col.label(text="Target")
        snap_label_col.label(text="Source")
        
        snap_op = snap_button_container.operator("object.nms_snap", icon="SNAP_ON")
        snap_button_container.separator()

        target_source_column = snap_button_container.column(align=True)
        source_row = target_source_column.row(align=True)
        target_row = target_source_column.row(align=True)
        
        snap_target_prev = target_row.operator( "object.nms_snap", icon="TRIA_LEFT", text="Prev" )
        snap_target_next = target_row.operator( "object.nms_snap", icon="TRIA_RIGHT", text="Next" )
        
        snap_source_prev = source_row.operator( "object.nms_snap", icon="TRIA_LEFT", text="Prev")
        snap_source_next = source_row.operator("object.nms_snap", icon="TRIA_RIGHT", text="Next")
        
        
        # Object orientation for corvette parts, mirror can work for non corvette parts too
        orientation_box = snap_column.box()
        mirror_col = orientation_box.column(align=True)
        mirror_col.label(text="Orientation") # icon = "ORIENTATION_GIMBAL"
        mirror_col.operator("object.nms_mirror", icon="ARROW_LEFTRIGHT")
        mirror_col.operator("object.nms_flip", icon="DECORATE_OVERRIDE")
        #mirror_col.operator("object.nms_turn", icon="GESTURE_ROTATE")
        
                    
        # Mirroring tools
        mirroring_box = build_tools_col.box()
        mirroring_box_column = mirroring_box.column(align = True)
        mirroring_box_column_label_row = mirroring_box_column.row(align = True)
        mirroring_box_column_label_row.label(text = "Mirroring", icon = "MOD_MIRROR")
        
        if not build_tool.check_show_advanced_options:
            mirroring_box_column_label_row.prop(build_tool,"check_show_advanced_options", text = "Show more options") # icon = "OPTIONS"
            #show simple options if advanced mirroring is unchecked
            mirroring_box_column.separator()
            mirroring_box_column.operator( "object.nms_universal_mirror_x", icon="ARROW_LEFTRIGHT" , text = "Mirror across X" )
        
        else :
            # show advanced options

            mirroring_box_column_label_row.prop(build_tool,"check_show_advanced_options", text = "Hide more options")
            # select center of reflection
            mirroring_box_column.label(text = "Center of Reflection")
            center_of_reflection_row = mirroring_box_column.row(align = True)
            center_of_reflection_row.prop(build_tool,"center_of_reflection",expand=True)
            
            # select mirror direction
            mirroring_box_column.label(text = "Direction")
            direction_row = mirroring_box_column.row(align = True)
            direction_row.prop(build_tool,"mirror_direction",expand=True)

            mirroring_box_column.separator()
            
            # displace field to select target object when "object" is selected as center of reflection
            if build_tool.center_of_reflection == "Object":
                mirroring_box_column.label(text = "Target Object")
                mirroring_box_column.prop(build_tool, "target_object", text = "")
                mirroring_box_column.separator()
                
            #check to auto duplicate objects before mirroring
            mirroring_box_column.prop(build_tool,"check_auto_duplicate")
            # perform mirror button
            mirroring_box_column.operator("object.nms_advanced_mirror", icon = "MOD_MIRROR", text = "Perform Mirror")
            

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
        
                        
