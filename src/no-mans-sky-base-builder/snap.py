"""Module level utilities for snapping objects together.

Author: Charlie Banks <@charliebanks>

"""

import json
import math
import os
from copy import copy

import mathutils

# File Paths.
file_path = os.path.dirname(os.path.realpath(__file__))
snap_matrix_json = os.path.join(file_path, "snapping_info.json")
snap_pair_json = os.path.join(file_path, "snapping_pairs.json")

# Load in the external dictionaries.
global snap_matrix_dictionary
global snap_pair_dictionary
snap_matrix_dictionary = {}
snap_pair_dictionary = {}

# Keep track of snap keys.
global per_item_snap_reference
per_item_snap_reference = {}

with open(snap_matrix_json, "r") as stream:
    snap_matrix_dictionary = json.load(stream)
with open(snap_pair_json, "r") as stream:
    snap_pair_dictionary = json.load(stream)


def get_snap_matrices_from_group(group):
    """Retrieve all snap points belonging to the snap group."""
    global snap_matrix_dictionary
    if group in snap_matrix_dictionary:
        if "snap_points" in snap_matrix_dictionary[group]:
            return snap_matrix_dictionary[group]["snap_points"]


def get_snap_group_from_part(part_id):
    """Search through the grouping dictionary and return the snap group.
    
    Args:
        part_id (str): The ID of the building part.
    """
    global snap_matrix_dictionary
    for group, value in snap_matrix_dictionary.items():
        parts = value["parts"]
        if part_id in parts:
            return group


def get_snap_pair_options(target_item_id, source_item_id):
    global snap_pair_dictionary
    # Get Groups.
    target_group = get_snap_group_from_part(target_item_id)
    source_group = get_snap_group_from_part(source_item_id)

    if not target_group and not source_group:
        return None

    # Get Pairing.
    if target_group in snap_pair_dictionary:
        snapping_dictionary = snap_pair_dictionary[target_group]
        if source_group in snapping_dictionary:
            return snapping_dictionary[source_group]


def cycle_keys(data, current, step="next"):
    # Sort the keys by the order sub-key.
    keys = data
    current_index = 0
    if current in keys:
        current_index = keys.index(current)
    if step == "next":
        next_index = current_index + 1
    elif step == "prev":
        next_index = current_index - 1

    if next_index > len(keys) - 1:
        next_index = 0

    if next_index < 0:
        next_index = len(keys) - 1

    return keys[next_index]


def snap_objects(
    source,
    target,
    next_source=False,
    prev_source=False,
    next_target=False,
    prev_target=False,
):
    """Given a source and a target, snap one to the other."""
    global per_item_snap_reference

    # Get Current Selection Object Type.
    source_key = None
    target_key = None

    if "objectID" not in target:
        return False

    if "objectID" not in source:
        return False

    # If anything, move the item to the target.
    source.matrix_world = copy(target.matrix_world)

    # Get Pairing options.
    snap_pairing_options = get_snap_pair_options(target["objectID"], source["objectID"])
    # IF no snap details are avaialbe then don't bother.
    if not snap_pairing_options:
        return False

    target_pairing_options = [
        part.strip() for part in snap_pairing_options[0].split(",")
    ]
    source_pairing_options = [
        part.strip() for part in snap_pairing_options[1].split(",")
    ]

    # Get the per item reference.
    target_item_snap_reference = per_item_snap_reference.get(target.name, {})
    # Get the target item type.
    target_id = target["objectID"]
    # Find corresponding dict in snap reference.
    target_snap_group = get_snap_group_from_part(target_id)
    target_local_matrix_datas = get_snap_matrices_from_group(target_snap_group)
    if target_local_matrix_datas:
        # Get the default target.
        default_target_key = target_pairing_options[0]
        target_key = target_item_snap_reference.get("target", default_target_key)

        # If the previous key is not in the available options
        # revert to default.
        if target_key not in target_pairing_options:
            target_key = default_target_key

        if next_target:
            target_key = cycle_keys(target_pairing_options, target_key, step="next")

        if prev_target:
            target_key = cycle_keys(target_pairing_options, target_key, step="prev")

    # Get the per item reference.
    source_item_snap_reference = per_item_snap_reference.get(source.name, {})
    # Get the source type.
    source_id = source["objectID"]
    # Find corresponding dict.
    source_snap_group = get_snap_group_from_part(source_id)
    source_local_matrix_datas = get_snap_matrices_from_group(source_snap_group)
    if source_local_matrix_datas:
        default_source_key = source_pairing_options[0]

        # If the source and target are the same, the source key can be
        # the opposite of target.
        if source_id == target_id:
            default_source_key = target_local_matrix_datas[target_key].get(
                "opposite", default_source_key
            )

        # Get the source key from the item reference, or use the default.
        if (source_id == target_id) and (prev_target or next_target):
            source_key = target_local_matrix_datas[target_key].get(
                "opposite", default_source_key
            )
        else:
            source_key = source_item_snap_reference.get("source", default_source_key)

        # If the previous key is not in the available options
        # revert to default.
        if source_key not in source_pairing_options:
            source_key = default_source_key

        if next_source:
            source_key = cycle_keys(source_pairing_options, source_key, step="next")

        if prev_source:
            source_key = cycle_keys(source_pairing_options, source_key, step="prev")

    if source_key and target_key:
        # Snap-point to snap-point matrix maths.
        # As I've defined X to be always outward facing, we snap the rotated
        # matrix to the point.
        # s = source, t = target, o = local snap matrix.
        # [(s.so)^-1 * (t.to)] * [(s.so) * 180 rot-matrix * (s.so)^-1]

        # First Create a Flipped Y Matrix based on local offset.
        start_matrix = copy(source.matrix_world)
        start_matrix_inv = copy(source.matrix_world)
        start_matrix_inv.invert()
        offset_matrix = mathutils.Matrix(
            source_local_matrix_datas[source_key]["matrix"]
        )

        # Target Matrix
        target_matrix = copy(target.matrix_world)
        target_offset_matrix = mathutils.Matrix(
            target_local_matrix_datas[target_key]["matrix"]
        )

        # Calculate the location of the target matrix.
        target_snap_matrix = target_matrix * target_offset_matrix

        # Calculate snap position.
        snap_matrix = start_matrix * offset_matrix
        snap_matrix_inv = copy(snap_matrix)
        snap_matrix_inv.invert()

        # Rotate by 180 around Y at the origin.
        origin_matrix = snap_matrix_inv * snap_matrix
        rotation_matrix = mathutils.Matrix.Rotation(math.radians(180.0), 4, "Y")
        origin_flipped_matrix = rotation_matrix * origin_matrix
        flipped_snap_matrix = snap_matrix * origin_flipped_matrix

        flipped_local_offset = start_matrix_inv * flipped_snap_matrix

        # Diff between the two.
        flipped_local_offset.invert()
        target_location = target_snap_matrix * flipped_local_offset

        source.matrix_world = target_location

        # Find the opposite source key and set it.
        next_target_key = target_key

        # If we are working with the same objects.
        next_target_key = source_local_matrix_datas[source_key].get("opposite", None)

        # Update source item refernece.
        source_item_snap_reference["source"] = source_key
        source_item_snap_reference["target"] = next_target_key

        # Update target item reference.
        target_item_snap_reference["target"] = target_key

        # Update per item reference.
        per_item_snap_reference[source.name] = source_item_snap_reference
        per_item_snap_reference[target.name] = target_item_snap_reference
        return True
