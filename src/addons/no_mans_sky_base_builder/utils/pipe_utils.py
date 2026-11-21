import itertools
import math

import mathutils

# every pipe starts at its origin and runs up local Y, same as Position and Up in the base data
# fixed shapes, the game never joins these into a T
SHAPED_PIPES = ("PIPESHAPE", "CURVEPIPESHAPE")
# blocks that join on any side, the game picks the straight, elbow, T or cross from their neighbours
BLOCK_PIPES = ("PIPE", "BASE_BUBPIPE")

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
}

# a pipe or bubble duct block is 2m long centred 1m up, it joins on any side
for _object_id in BLOCK_PIPES:
    OPENINGS[_object_id] = {
        "TOP": _frame((0, 2, 0), (0, 1, 0), (0, 0, 1)),
        "BOTTOM": _frame((0, 0, 0), (0, -1, 0), (0, 0, 1)),
        "LEFT": _frame((-1, 1, 0), (-1, 0, 0), (0, 0, 1)),
        "RIGHT": _frame((1, 1, 0), (1, 0, 0), (0, 0, 1)),
    }

# a block's six sides, as directions out from its centre
BLOCK_CENTRE = mathutils.Vector((0, 1, 0))
BLOCK_SIDES = {
    "+X": mathutils.Vector((1, 0, 0)),
    "-X": mathutils.Vector((-1, 0, 0)),
    "+Y": mathutils.Vector((0, 1, 0)),
    "-Y": mathutils.Vector((0, -1, 0)),
    "+Z": mathutils.Vector((0, 0, 1)),
    "-Z": mathutils.Vector((0, 0, -1)),
}
# how far apart two openings can be and still join in game
JOIN_DISTANCE = 0.075

def is_pipe(bpy_object):
    return bpy_object is not None and bpy_object.get("ObjectID") in SHAPED_PIPES + BLOCK_PIPES


def get_extension(bpy_object, direction):
    """Get the piece to add next to a pipe, and where it goes.

    Blocks add a block on that side, the game shapes them from their neighbours.
    Shaped pipes carry on straight up or down, and turn with an elbow.
    Both turn towards -X, where the arrows on a straight point, spin the pipe to turn elsewhere.

    Args:
        direction (str): FRONT, BACK or TURN, in the frame of the pipe.

    Returns:
        tuple: The object ID and world matrix of the new piece.
    """
    object_id = bpy_object["ObjectID"]
    openings = OPENINGS[object_id]
    world = bpy_object.matrix_world

    if object_id in BLOCK_PIPES:
        key = {"FRONT": "TOP", "BACK": "BOTTOM", "TURN": "LEFT"}[direction]
        return object_id, world @ openings[key]

    if direction == "FRONT":
        return "PIPESHAPE", world @ openings["TOP"]
    if direction == "BACK":
        return "PIPESHAPE", world @ openings["BOTTOM"]
    # the elbow bends towards -X
    return "CURVEPIPESHAPE", world @ openings["TOP"]


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


def get_roll(bpy_object):
    """Get how far a pipe is spun around its run, from where its arrows point when it is added.

    The rest direction is the arrows of a new upright pipe, tipped over to lie along the pipe.
    Seen from the top end looking down the pipe, the angle goes anticlockwise.

    Returns:
        float: Radians, from 0 to a full turn.
    """
    world = bpy_object.matrix_world.to_3x3()
    up = world.col[1].normalized()
    arrow = -world.col[0].normalized()
    rest = mathutils.Vector((0, 0, 1)).rotation_difference(up) @ mathutils.Vector((-1, 0, 0))
    angle = math.atan2(rest.cross(arrow).dot(up), rest.dot(arrow))
    return angle % math.tau


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


def get_block_openings(bpy_object):
    """Get where each side of a block opens in the world.

    Returns:
        dict: The world position of each side's opening.
    """
    world = bpy_object.matrix_world
    return {side: world @ (BLOCK_CENTRE + direction) for side, direction in BLOCK_SIDES.items()}


def get_joined_sides(bpy_object, blocks):
    """Get the sides of a block that meet the opening of another block.

    Args:
        blocks (list): Every block it could join, it is skipped if in there.

    Returns:
        tuple: The joined sides, sorted.
    """
    others = [
        position
        for block in blocks
        if block != bpy_object
        for position in get_block_openings(block).values()
    ]
    joined = []
    for side, position in get_block_openings(bpy_object).items():
        if any((position - other).length <= JOIN_DISTANCE for other in others):
            joined.append(side)
    return tuple(sorted(joined))


# the joined sides each block model is built with, named after the game's own pieces
BLOCK_SHAPES = {
    "PIPE": ("+Y", "-Y"),
    "_PIPEL": ("-X", "-Y"),
    "_PIPET": ("+Y", "-X", "-Y"),
    "_PIPEX": ("+X", "+Y", "-X", "-Y"),
    "_PIPE3CORNER": ("+Z", "-X", "-Y"),
    "_PIPE4CORNER": ("+Y", "+Z", "-X", "-Y"),
    "_PIPESTARHALF": ("+Y", "+Z", "-X", "-Y", "-Z"),
    "_PIPESTAR": ("+X", "+Y", "+Z", "-X", "-Y", "-Z"),
}


def _get_cube_turns():
    # the 24 turns that land a cube's sides on its sides, without mirroring
    turns = []
    for order in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            matrix = mathutils.Matrix.Identity(3)
            for column, (row, sign) in enumerate(zip(order, signs)):
                matrix.col[column] = mathutils.Vector([sign if i == row else 0 for i in range(3)])
            if matrix.determinant() > 0:
                turns.append(matrix)
    # no turn first, so a shape already facing the right way stays as built
    return sorted(turns, key=lambda turn: turn != mathutils.Matrix.Identity(3))


CUBE_TURNS = _get_cube_turns()


def _get_side_name(direction):
    for side, side_direction in BLOCK_SIDES.items():
        if (side_direction - direction).length < 1e-3:
            return side
    return None


def get_block_shape(sides):
    """Get the model the game shows for a block with these sides joined, and how it is turned.

    A lone side, or none, runs straight through.

    Args:
        sides (tuple): The joined sides, from get_joined_sides.

    Returns:
        tuple: The shape's object ID and its turn around the block's centre.
    """
    if len(sides) < 2:
        direction = BLOCK_SIDES[sides[0]] if sides else BLOCK_SIDES["+Y"]
        sides = (_get_side_name(direction), _get_side_name(-direction))
    wanted = set(sides)
    for shape_id, shape_sides in BLOCK_SHAPES.items():
        if len(shape_sides) != len(wanted):
            continue
        for turn in CUBE_TURNS:
            if {_get_side_name(turn @ BLOCK_SIDES[side]) for side in shape_sides} == wanted:
                centre = mathutils.Matrix.Translation(BLOCK_CENTRE)
                return shape_id, centre @ turn.to_4x4() @ centre.inverted()
    return None, None
