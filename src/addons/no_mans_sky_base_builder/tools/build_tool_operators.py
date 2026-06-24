import bpy
from ..utils import blend_utils, curve
from ..utils.mirror_utils import ShowMessageBox

from mathutils import Vector

class MirrorAcrossX(bpy.types.Operator):
    """Mirror the object along the X axis."""

    bl_idname = "object.nms_universal_mirror_x"
    bl_label = "Mirror Across X"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.mirror( axis = "X", center = Vector((0,0,0)))
        return {"FINISHED"}
    
    
class MirrorAcrossY(bpy.types.Operator):
    """Mirror the object along the Y axis."""

    bl_idname = "object.nms_universal_mirror_y"
    bl_label = "Mirror Across Y"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.mirror( axis = "Y", center = Vector((0,0,0)))
        return {"FINISHED"}
    
class MirrorAcrossZ(bpy.types.Operator):
    """Mirror the object along the Z axis."""

    bl_idname = "object.nms_universal_mirror_z"
    bl_label = "Mirror Across Z"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.mirror( axis = "Z", center = Vector((0,0,0)))
        return {"FINISHED"}
    

class PeformAdvancedMirrorButton(bpy.types.Operator):
    """Perform Mirroring according to options selected."""

    bl_idname = "object.nms_advanced_mirror"
    bl_label = "Perform Mirror"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.advanced_mirror()
        return {"FINISHED"}
    

class Mirror(bpy.types.Operator):
    """Mirror the object local to itself."""

    bl_idname = "object.nms_mirror"
    bl_label = "Mirror"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.mirror("X", change_orientation = True)
        return {"FINISHED"}
    
class Flip(bpy.types.Operator):
    """Flip the object along the Y axis (Only available on certain Corvette pieces)"""

    bl_idname = "object.nms_flip"
    bl_label = "Flip"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.mirror("Z", change_orientation = True)
        return {"FINISHED"}
    
    
class Turn(bpy.types.Operator):
    """Turn the object along the Z axis (Only available on certain Corvette pieces)"""

    bl_idname = "object.nms_turn"
    bl_label = "Turn"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.mirror("Y", change_orientation = True)
        return {"FINISHED"}

    
class SelectDuplicates(bpy.types.Operator):
    """Select duplicate objects, leaving one object duplicated unselected, so that deletion is safe"""

    bl_idname = "object.nms_select_duplicates"
    bl_label = "Cleanup Scene"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        result = blend_utils.find_duplicates()
        self.report({'INFO'}, f"Found {result} duplicates")
        return {"FINISHED"}
    
    
# Tool Operators ---
class ToggleRoom(bpy.types.Operator):
    bl_idname = "object.nms_toggle_room_visibility"
    bl_label = "Toggle Room Visibility: Normal"
    bl_options = {
        "UNDO",
        "REGISTER",
    }  # I think this must pass "UNDO" because it changes objects, but it probably doesn't interact correctly with the plugin?

    def execute(self, context):
        scene = context.scene
        nms_base_tool = scene.nms_base_tool
        nms_base_tool.toggle_room_visibility()
        return {"FINISHED"}
    
    
# Tool Operators ---
class Duplicate(bpy.types.Operator):
    """Duplicate the selected part."""

    bl_idname = "object.nms_duplicate"
    bl_label = "Duplicate"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.duplicate()
        return {"FINISHED"}


class Delete(bpy.types.Operator):
    """Remove the selected part from the scene."""

    bl_idname = "object.nms_delete"
    bl_label = "Delete"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.delete()
        return {"FINISHED"}


class DuplicateAlongCurve(bpy.types.Operator):
    
    """Select two objects, one of them must be a curve and other an object. """

    bl_idname = "object.nms_duplicate_along_curve"
    bl_label = "Duplicate Along Curve"
    bl_options = {"UNDO", "REGISTER"}
    
    number_of_objects: bpy.props.IntProperty(
        name="Number of Objects",
        default = 10,
        
        min=1,       # Absolute lowest value allowed
        max=1000,      # Absolute highest value allowed
        soft_min=5,  # Slider UI floor
        soft_max=500  # Slider UI ceiling
    )
    
    overall_Radius: bpy.props.FloatProperty(
        name="Overall Radius",
        default = 1.0,
        
        min=0.0,       # Absolute lowest value allowed
        max=100.0,      # Absolute highest value allowed
        soft_min=0.01,  # Slider UI floor
        soft_max=5.0   # Slider UI ceiling
    )

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.duplicate_along_curve(self.number_of_objects, self.overall_Radius)
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        selected_objects = bpy.context.selected_objects

        # make sure that there are only two objects selected
        # One must be curve, other must be an object for duplication
        if len(selected_objects) != 2:
            message = (
                "Make sure you have two items selected. Select the item to"
                " duplicate, then the curve you want to snap to."
            )
            ShowMessageBox(message=message, title="Duplicate Along Curve")
            return {"CANCELLED"}
        
        #Make sure that there is only one curve in selection
        curve_objs = [obj for obj in selected_objects if curve.is_bezier_or_nurbs_path(obj)]
        if len(curve_objs) != 1:
            message = (
                "Make sure you have two items selected.\n"
                "One of them must be a curve and other must be object for dupication."
            )
            ShowMessageBox(message=message, title="Duplicate Along Curve")
            return {"CANCELLED"}
        
        return wm.invoke_props_dialog(self)
    

class CreateCurve(bpy.types.Operator):
    """Add a default Bezier curve to location of 3d cursor in scene"""

    bl_idname = "object.nms_create_curve"
    bl_label = "Create Curve"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        cursor = bpy.context.scene.cursor
        bpy.ops.curve.primitive_bezier_curve_add(
            radius=1.0,
            location=cursor.location,
            rotation=(0, 0, 0)
        )
        curve_obj = bpy.context.active_object
        self.report({'INFO'}, f"Created Bezier Curve ({curve_obj.name}) on 3d cursor")
        return {"FINISHED"}
    

class Snap(bpy.types.Operator):
    """Snap the selected object to another selected object."""

    bl_idname = "object.nms_snap"
    bl_label = "Snap"
    bl_options = {"UNDO", "REGISTER"}

    next_source: bpy.props.BoolProperty()
    prev_source: bpy.props.BoolProperty()
    next_target: bpy.props.BoolProperty()
    prev_target: bpy.props.BoolProperty()

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        
        
        kwargs = {
            "next_source": self.next_source,
            "prev_source": self.prev_source,
            "next_target": self.next_target,
            "prev_target": self.prev_target,
        }
        build_tool.snap(**kwargs)
        return {"FINISHED"}

    

class CurveBreakApart(bpy.types.Operator):
    """Break apart objects linked to curve."""

    bl_idname = "object.nms_curve_break_apart"
    bl_label = "Break Curve"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = "Break apart objects from curve and make them independent"

    def execute(self, context):
        active_object = bpy.context.active_object
        try:
            detached_count = curve.apply_curve_transforms_and_detach(active_object)
            self.report({'INFO'}, f"Created {detached_count} objects")
        except TypeError as error_message:
            self.report({'ERROR'}, str(error_message))
        return {"FINISHED"}
    

class CurveDelete(bpy.types.Operator):
    """Delete selected curve and objects linked to it"""

    bl_idname = "object.nms_curve_delete"
    bl_label = "Delete Curve"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        active_object = bpy.context.active_object
        try:
            deleted_count = curve.delete_curve_and_children(active_object)
            self.report({'INFO'}, f"Deleted curve and {deleted_count} objects linked to it")
        except TypeError as error_message:
            self.report({'ERROR'}, str(error_message))
        return {"FINISHED"}
    
class CurveMirror(bpy.types.Operator):
    """Mirror Curve along X-Axis"""

    bl_idname = "object.nms_curve_mirror"
    bl_label = "Mirror Curve"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        active_object = bpy.context.active_object
        try:
            curve.create_mirrored_curve_copy(active_object)
        except TypeError as error_message:
            self.report({'ERROR'}, str(error_message))
        return {"FINISHED"}
    

class SelectObjectParentCurve(bpy.types.Operator):
    """Select parent curve of object selected"""

    bl_idname = "object.nms_selecte_object_parent_curve"
    bl_label = "Break Curve"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = "Select parent curve of object selected"

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.select_parent_curve()
        return {"FINISHED"}
    
class SelectChildrenOfCurve(bpy.types.Operator):
    """Select duplicated objects linked to a curve"""

    bl_idname = "object.nms_select_children_of_curve"
    bl_label = "Break Curve"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = "Select duplicated objects linked to a curve"

    def execute(self, context):
        scene = context.scene
        build_tool = scene.nms_build_tool
        build_tool.select_children_of_curve()
        return {"FINISHED"}
    

class ShowCurveToolInfo(bpy.types.Operator):
    bl_idname = "object.nms_show_curve_info_popup"
    bl_label = "Info"
    bl_description = "Show tips on how to use curve tool"

    def execute(self, context):

        message = (
                "Select the curve and press Tab to enter Edit Mode.\n"
                "Click a curve point to select it.\n"
                "Press Ctrl + T and move the mouse to twist the selected point.\n"
                "Press Alt + S and move the mouse to make the point thicker or thinner.\n"
                "When you're done, press Tab again to return to the normal viewport."
            )
        
        def draw(self, context):
            for line in message.split("\n"):
                self.layout.label(text=line)

        bpy.context.window_manager.popup_menu(
            draw,
            title="How to Edit curve after duplication ?",
            icon='HELP'
        )

        return {'FINISHED'}

    
classes = (
    MirrorAcrossX,
    MirrorAcrossY,
    MirrorAcrossZ,
    PeformAdvancedMirrorButton,
    
    Duplicate,
    DuplicateAlongCurve,
    CreateCurve,
    CurveMirror,
    CurveBreakApart,
    CurveDelete,
    
    SelectObjectParentCurve,
    SelectChildrenOfCurve,
    ShowCurveToolInfo,
    
    Delete,
    Mirror,
    Flip,
    Turn,
    ToggleRoom,
    Snap,
    
    SelectDuplicates,
    
)