import bpy

from .transformation import Transformation


class ResetTransformations(bpy.types.Operator):
    """Reset Scale and Rotation of the selected objects"""

    bl_idname = "object.nms_reset_transformations"
    bl_label = "Reset Transformations"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({"WARNING"}, "Please select at least one object first")
            return {"CANCELLED"}

        Transformation.reset_transformations(selected_objects)
        return {"FINISHED"}


class CopyTransformations(bpy.types.Operator):
    """Copy Transformations of the active object"""

    bl_idname = "object.nms_copy_transformations"
    bl_label = "Copy Transformations"

    def execute(self, context):
        active_object = context.view_layer.objects.active
        if active_object is None:
            self.report({"WARNING"}, "Please select an object first")
            return {"CANCELLED"}

        context.scene.nms_transformation.copy_transformations(active_object)
        self.report({"INFO"}, "Copied Transformations")
        return {"FINISHED"}


class _PasteBase(bpy.types.Operator):
    bl_options = {"UNDO", "REGISTER"}

    paste_location = False
    paste_rotation = False
    paste_scale = False

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({"WARNING"}, "Please select at least one object first")
            return {"CANCELLED"}

        context.scene.nms_transformation.paste_transformations(
            selected_objects,
            location=self.paste_location,
            rotation=self.paste_rotation,
            scale=self.paste_scale,
        )
        return {"FINISHED"}


class PasteTransformations(_PasteBase):
    """Paste Copied Transformations onto the selected objects"""

    bl_idname = "object.nms_paste_transformations"
    bl_label = "Paste Transformations"

    paste_location = True
    paste_rotation = True
    paste_scale = True


class PasteLocation(_PasteBase):
    """Paste Copied Location onto the selected objects"""

    bl_idname = "object.nms_paste_location"
    bl_label = "Paste Location"

    paste_location = True


class PasteRotation(_PasteBase):
    """Paste Copied Rotation onto the selected objects"""

    bl_idname = "object.nms_paste_rotation"
    bl_label = "Paste Rotation"

    paste_rotation = True


class PasteScale(_PasteBase):
    """Paste Copied Scale onto the selected objects"""

    bl_idname = "object.nms_paste_scale"
    bl_label = "Paste Scale"

    paste_scale = True


classes = (
    ResetTransformations,
    CopyTransformations,
    PasteTransformations,
    PasteLocation,
    PasteRotation,
    PasteScale,
)
