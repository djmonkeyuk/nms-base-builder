import math

import bpy
from bpy.props import EnumProperty, FloatProperty

from ..builder import get_builder
from ..utils import blend_utils, pipe_utils
from ..utils.blend_utils import ShowMessageBox


def get_selected_pipe():
    """Get the active pipe, or tell the user to select one."""
    active_object = blend_utils.get_selected_active_object()
    if pipe_utils.is_pipe(active_object):
        return active_object
    ShowMessageBox(message="Make sure you have a pipe selected.", title="Pipes & Ducts")
    return None


class AddPipe(bpy.types.Operator):
    """Add a pipe of the chosen type at the 3D cursor."""

    bl_idname = "object.nms_add_pipe_piece"
    bl_label = "Add Pipe"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        nms_tool = context.scene.nms_base_tool
        object_id = "BASE_BUBPIPE" if nms_tool.pipe_type == "BUBBLE" else "PIPESHAPE"
        new_pipe = get_builder().add_part(object_id)
        new_pipe.location = context.scene.cursor.location
        new_pipe.select()
        return {"FINISHED"}


class ExtendPipe(bpy.types.Operator):
    """Add the next piece to the selected pipe in this direction."""

    bl_idname = "object.nms_extend_pipe"
    bl_label = "Extend Pipe"
    bl_options = {"UNDO", "REGISTER"}

    direction: EnumProperty(
        items=[
            ("FRONT", "Front", "Carry on from the top end"),
            ("BACK", "Back", "Carry on from the bottom end"),
            ("LEFT", "Left", "Turn to the left of the pipe"),
            ("RIGHT", "Right", "Turn to the right of the pipe"),
        ],
    )

    def execute(self, context):
        pipe = get_selected_pipe()
        if not pipe:
            return {"FINISHED"}

        object_id, matrix = pipe_utils.get_extension(pipe, self.direction)
        new_pipe = get_builder().add_part(object_id)
        new_pipe.matrix_world = matrix
        # selected so the next click carries on from this piece
        new_pipe.select()
        return {"FINISHED"}


class RotatePipe(bpy.types.Operator):
    """Spin the selected pipes around the run of the active pipe."""

    bl_idname = "object.nms_rotate_pipe"
    bl_label = "Rotate Pipe"
    bl_options = {"UNDO", "REGISTER"}

    angle: FloatProperty(subtype="ANGLE", default=math.radians(90.0))

    def execute(self, context):
        pipe = get_selected_pipe()
        if not pipe:
            return {"FINISHED"}

        # every selected pipe turns with the active one, so a whole branch can be turned
        pipes = [o for o in context.selected_objects if pipe_utils.is_pipe(o)]
        pipe_utils.rotate(pipes, pipe, self.angle)
        return {"FINISHED"}


classes = (AddPipe, ExtendPipe, RotatePipe)
