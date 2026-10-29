import math

import mathutils

# every pipe starts at its origin and runs up local Y, same as Position and Up in the base data
NORMAL_PIPES = ("PIPESHAPE", "CURVEPIPESHAPE")
BUBBLE_PIPES = ("BASE_BUBPIPE",)

# set on a mesh once it has been moved into the game's frame, so shared meshes move once
GAME_FRAME_KEY = "nms_game_frame"


def _frame(position, up, at):
    """Build a local matrix for an opening, the new piece's origin sits on it and runs along up.

    Args:
        position (tuple): Where the opening is.
        up (tuple): The direction leaving the opening.
        at (tuple): The facing kept by the new piece.
    """
    up = mathutils.Vector(up)
    at = mathutils.Vector(at)
    matrix = mathutils.Matrix.Identity(4)
    matrix.col[0][:3] = up.cross(at)
    matrix.col[1][:3] = up
    matrix.col[2][:3] = at
    matrix.col[3][:3] = position
    return matrix


# openings of each piece in its local frame
OPENINGS = {
    "PIPESHAPE": {
        "TOP": _frame((0, 2, 0), (0, 1, 0), (0, 0, 1)),
        "BOTTOM": _frame((0, 0, 0), (0, -1, 0), (0, 0, 1)),
    },
    # the elbow bends from heading up to heading towards -X
    "CURVEPIPESHAPE": {
        "TOP": _frame((-1, 1, 0), (-1, 0, 0), (0, 0, 1)),
        "BOTTOM": _frame((0, 0, 0), (0, -1, 0), (0, 0, 1)),
    },
    # a bubble duct is a 2m block centred 1m up, it joins on any side
    "BASE_BUBPIPE": {
        "TOP": _frame((0, 2, 0), (0, 1, 0), (0, 0, 1)),
        "BOTTOM": _frame((0, 0, 0), (0, -1, 0), (0, 0, 1)),
        "LEFT": _frame((-1, 1, 0), (-1, 0, 0), (0, 0, 1)),
        "RIGHT": _frame((1, 1, 0), (1, 0, 0), (0, 0, 1)),
    },
}

# turns an elbow around its own run so it bends the other way
FLIP_MATRIX = mathutils.Matrix.Rotation(math.radians(180.0), 4, "Y")


def is_pipe(bpy_object):
    return bpy_object is not None and bpy_object.get("ObjectID") in NORMAL_PIPES + BUBBLE_PIPES


def get_extension(bpy_object, direction):
    """Get the piece to add next to a pipe, and where it goes.

    Normal pipes carry on straight up or down, and turn left or right with an elbow.
    Bubble ducts add a duct on that side, the game shapes them from their neighbours.

    Args:
        direction (str): FRONT, BACK, LEFT or RIGHT, in the frame of the pipe.

    Returns:
        tuple: The object ID and world matrix of the new piece.
    """
    object_id = bpy_object["ObjectID"]
    openings = OPENINGS[object_id]
    world = bpy_object.matrix_world

    if object_id in BUBBLE_PIPES:
        key = {"FRONT": "TOP", "BACK": "BOTTOM"}.get(direction, direction)
        return object_id, world @ openings[key]

    if direction == "FRONT":
        return "PIPESHAPE", world @ openings["TOP"]
    if direction == "BACK":
        return "PIPESHAPE", world @ openings["BOTTOM"]
    # the elbow bends to its left, flipped it bends right
    matrix = world @ openings["TOP"]
    if direction == "RIGHT":
        matrix = matrix @ FLIP_MATRIX
    return "CURVEPIPESHAPE", matrix


def rotate(bpy_objects, pivot_object, angle):
    """Spin pipes around the run of the pivot pipe, through its bottom end so it stays on what it grew from.

    Args:
        bpy_objects (list): The pipes to turn, the pivot pipe included.
        angle (float): Radians to turn by.
    """
    pivot = pivot_object.matrix_world
    axis = pivot.to_3x3().col[1].normalized()
    origin = pivot.translation.copy()
    matrix = (
        mathutils.Matrix.Translation(origin)
        @ mathutils.Matrix.Rotation(angle, 4, axis)
        @ mathutils.Matrix.Translation(-origin)
    )
    for bpy_object in bpy_objects:
        bpy_object.matrix_world = matrix @ bpy_object.matrix_world


def move_to_game_frame(bpy_object):
    """Stand a mesh built along Z around the origin up local Y from the origin.

    The bubble duct model is centred on Z, but the game places it from its bottom end
    like every other pipe, so the mesh is moved to show where it really is.
    """
    mesh = bpy_object.data
    if mesh is None or mesh.get(GAME_FRAME_KEY):
        return
    matrix = mathutils.Matrix.Translation((0.0, 1.0, 0.0)) @ mathutils.Matrix.Rotation(
        math.radians(-90.0), 4, "X"
    )
    mesh.transform(matrix)
    mesh[GAME_FRAME_KEY] = True
