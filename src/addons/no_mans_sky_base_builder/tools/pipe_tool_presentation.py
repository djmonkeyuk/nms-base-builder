import math

import bpy

from ..utils import pipe_utils


def draw_pipes(layout, nms_tool):
    """Draw the pipes and ducts tools, Cables & Logic shows them in place of its cable tools.

    Args:
        layout (bpy.types.UILayout): The column inside the panel's box.
        nms_tool (NMSSettings): The settings holding the chosen pipe type.
    """
    # Add ---
    layout.separator()
    layout.label(text="Pipe Type")
    layout.row(align=True).prop(nms_tool, "pipe_type", expand=True)
    layout.operator("object.nms_add_pipe_piece", icon="ADD")

    # Extend ---
    layout.separator()
    layout.label(text="Extend")
    along_row, side_row = split_halves(layout)
    along_row.operator("object.nms_extend_pipe", text="Front", icon="TRIA_UP").direction = "FRONT"
    along_row.operator("object.nms_extend_pipe", text="Back", icon="TRIA_DOWN").direction = "BACK"
    # spin the pipe with the rotate buttons to choose where it turns
    side_row.operator("object.nms_extend_pipe", text="Turn", icon="FORWARD").direction = "TURN"

    # Rotate ---
    layout.separator()
    layout.label(text="Rotate")
    angle_row, turn_row = split_halves(layout)
    # shows the selected pipe's spin, typing an angle spins it there
    angle_row.enabled = pipe_utils.is_pipe(bpy.context.view_layer.objects.active)
    angle_row.prop(nms_tool, "pipe_angle", text="")
    # seen from the top end looking down the pipe, a positive angle turns anticlockwise
    turn_row.operator("object.nms_rotate_pipe", text="90°", icon="LOOP_BACK").angle = math.radians(90.0)
    turn_row.operator("object.nms_rotate_pipe", text="90°", icon="LOOP_FORWARDS").angle = math.radians(-90.0)


def split_halves(layout):
    """Split a row into two equal halves with a gap between, so rows below line up.

    Returns:
        tuple: The left and right rows.
    """
    split = layout.split(factor=0.5)
    return split.row(align=True), split.row(align=True)
