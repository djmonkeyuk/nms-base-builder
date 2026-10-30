import math
import os

import mathutils

from . import python as python_utils

# snap points read from the game's placement scenes, stored with the addon
GAME_SNAP_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "resources", "snapping_info_game.json"
)
GAME_SNAP_DICTIONARY = python_utils.load_dictionary(GAME_SNAP_JSON) if os.path.exists(GAME_SNAP_JSON) else {}
GAME_PARTS = GAME_SNAP_DICTIONARY.get("parts", {})
HAND_PARTS = GAME_SNAP_DICTIONARY.get("hand_parts", {})
GAME_POINTS = GAME_SNAP_DICTIONARY.get("points", {})
PROP_GROUP = "PROPS"

# hand made points with the game ones added, per part
_MERGED_POINTS = {}


def add_game_props(snap_dictionary):
    """Add the decorations that have no points of their own to the props.

    Args:
        snap_dictionary (dict): The hand made snapping info.
    """
    props = snap_dictionary.get(PROP_GROUP)
    if props is not None:
        props["parts"] = props["parts"] + [p for p in GAME_SNAP_DICTIONARY.get("props", []) if p not in props["parts"]]
    return snap_dictionary


def is_game_part(object_id):
    """Check if a part only snaps by the points read from the game."""
    return object_id in GAME_PARTS


def get_game_group(object_id):
    """Get the group of a part that only snaps by the points read from the game."""
    return GAME_PARTS.get(object_id)


def get_snap_points(object_id, hand_points=None):
    """Get a part's points, the hand made ones with the game's added as GAME_ points.

    Args:
        object_id (str): The part.
        hand_points (dict): The points of the part's hand made group.
    """
    if object_id in GAME_PARTS:
        return GAME_POINTS[GAME_PARTS[object_id]]
    if object_id not in HAND_PARTS:
        return hand_points
    if object_id not in _MERGED_POINTS:
        merged = dict(hand_points or {})
        merged.update(GAME_POINTS[HAND_PARTS[object_id]])
        _MERGED_POINTS[object_id] = merged
    return _MERGED_POINTS[object_id]


def sockets_fit(target_point, source_point):
    """Check if the source point can land on the target point, a point with no sockets fits anything."""
    target_sockets = target_point.get("sockets")
    source_sockets = source_point.get("sockets")
    if not target_sockets or not source_sockets:
        return True
    return bool(
        set(target_sockets["out"]) & set(source_sockets["in"])
        or set(target_sockets["in"]) & set(source_sockets["out"])
    )


def get_landing(target_matrix, target_point, source_point):
    """Get where a part goes when its source point lands on the target point.

    Args:
        target_matrix (mathutils.Matrix): The target part's world matrix.
        target_point (dict): The target's point.
        source_point (dict): The source's point, flipped round its up axis as it lands.
    """
    flipped = mathutils.Matrix(source_point["matrix"]) @ mathutils.Matrix.Rotation(math.radians(180.0), 4, "Y")
    return target_matrix @ mathutils.Matrix(target_point["matrix"]) @ flipped.inverted()


def get_overlap(source_object, landing, target_object):
    """Get how much of the source's box sits inside the target's box, both in world space."""
    source_corners = [landing @ mathutils.Vector(corner) for corner in source_object.bound_box]
    target_corners = [target_object.matrix_world @ mathutils.Vector(corner) for corner in target_object.bound_box]
    overlap = 1.0
    for axis in range(3):
        low = max(min(c[axis] for c in source_corners), min(c[axis] for c in target_corners))
        high = min(max(c[axis] for c in source_corners), max(c[axis] for c in target_corners))
        overlap *= max(high - low, 0.0)
    return overlap


def get_best_turn(source_object, target_object, target_point, source_key, source_points):
    """Get the source point that lands on the same spot turned to sit most inside the target.

    Only points read from the game are turned, a hand made pair is kept as it is.

    Args:
        source_object (bpy.types.Object): The part being snapped.
        target_object (bpy.types.Object): The part being snapped to.
        target_point (dict): The target's point.
        source_key (str): The source point picked so far.
        source_points (dict): The source points that can be picked.
    """
    if "sockets" not in target_point or "sockets" not in source_points.get(source_key, {}):
        return source_key
    target_matrix = target_object.matrix_world
    spot = get_landing(target_matrix, target_point, source_points[source_key]).translation
    best_key = source_key
    best_overlap = None
    for key, point in source_points.items():
        if "sockets" not in point or not sockets_fit(target_point, point):
            continue
        landing = get_landing(target_matrix, target_point, point)
        if (landing.translation - spot).length > 1e-3:
            continue
        overlap = get_overlap(source_object, landing, target_object)
        # the picked point wins a tie
        if best_overlap is None or overlap > best_overlap + 1e-4 or (key == source_key and overlap >= best_overlap - 1e-4):
            best_key, best_overlap = key, overlap
    return best_key


def get_socket_pairing(target_points, source_points):
    """Get the target and source points that fit each other, in the form of the pairs file.

    Args:
        target_points (dict): The points of the part being snapped to.
        source_points (dict): The points of the part being snapped.
    """
    if not target_points or not source_points:
        return None
    target_points = {k: p for k, p in target_points.items() if "sockets" in p}
    source_points = {k: p for k, p in source_points.items() if "sockets" in p}
    # how good the best pair a point is in, a pair of main points comes before one with an inner point
    target_ranks = {}
    source_ranks = {}
    for target_key, target_point in target_points.items():
        for source_key, source_point in source_points.items():
            if not sockets_fit(target_point, source_point):
                continue
            rank = target_point.get("secondary", False) + source_point.get("secondary", False)
            target_ranks[target_key] = min(rank, target_ranks.get(target_key, rank))
            source_ranks[source_key] = min(rank, source_ranks.get(source_key, rank))
    if not target_ranks or not source_ranks:
        return None
    # sorted keeps the scene's order between points of the same rank
    target_keys = sorted([k for k in target_points if k in target_ranks], key=target_ranks.get)
    source_keys = sorted([k for k in source_points if k in source_ranks], key=source_ranks.get)
    return [",".join(target_keys), ",".join(source_keys)]
