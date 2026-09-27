import contextlib
import functools
import math
import uuid

import bpy

from ..builder import get_builder
from ..group import Group
from ..part import Part
from . import collection_utils, curve_utils, material, userdata


class Curve:
    # curve property names
    PROP_HAS_LINKED_OBJECTS = "has_linked_objects"
    PROP_RADIUS_MULTIPLIER = "radius_multiplier"
    PROP_INITIAL_CURVE_SCALE = "initial_curve_scale"
    PROP_OBJECTS_COUNT = "objects_count"
    PROP_CURVE_ID = "CurveID"
    PROP_PARENT_SELECTED = "parent_selected"
    PROP_IS_INITIALISED = "is_initialised"
    PROP_DENSITY_STEP = "density_step"

    # follower property names
    PROP_CURVE_PARENT = "curve_parent"
    PROP_BASE_SCALE = "base_scale"
    PROP_CURVE_FACTOR = "curve_factor"
    PROP_RADIUS = "radius"

    # the part duplicated along the curve
    PROP_DUP_OBJECT_ID = f"dup_{Part.PROP_OBJECT_ID}"
    PROP_DUP_USER_DATA = f"dup_{Part.PROP_USER_DATA}"

    # the group duplicated along the curve
    PROP_DUP_IS_GROUP = "is_group"
    PROP_DUP_GROUP_ID = f"dup_{Group.PROP_GROUP_ID}"
    PROP_GROUP_CHILD_CACHE = f"dup_{Group.PROP_CHILD_CACHE}"
    PROP_ORIGIN_MATRIX = f"dupe_{Group.PROP_ORIGIN_MATRIX}"
    GROUP_PROPS = (PROP_DUP_IS_GROUP, PROP_DUP_GROUP_ID, PROP_GROUP_CHILD_CACHE, PROP_ORIGIN_MATRIX)

    # properties from older versions of the curve tool
    LEGACY_PROPS = ("unique_id", "parent_col", "master_col")


# Rebuilding a curve can import fbx files, and every import fires the depsgraph handler
# mid rebuild. Entry points check this so a rebuild never starts another one.
_busy_depth = 0


def is_busy():
    return _busy_depth > 0


# hold off curve updates, e.g. while the panel sets both sliders
@contextlib.contextmanager
def suspend_updates():
    global _busy_depth
    _busy_depth += 1
    try:
        yield
    finally:
        _busy_depth -= 1


def _marks_busy(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with suspend_updates():
            return func(*args, **kwargs)
    return wrapper


# weights start neutral, done before any spacing is measured from them
def ensure_initialised(curve_obj):
    if curve_obj.get(Curve.PROP_IS_INITIALISED, False):
        return
    curve_utils.half_the_weight_points(curve_obj)
    curve_obj[Curve.PROP_IS_INITIALISED] = True
    # a step measured with the old weights would give the wrong count
    curve_obj.pop(Curve.PROP_DENSITY_STEP, None)


# curves saved by older versions used unique_id and per curve collections
def migrate_legacy_curve(curve_obj):
    if not curve_obj.get(Curve.PROP_HAS_LINKED_OBJECTS, False):
        return
    if Curve.PROP_CURVE_ID not in curve_obj:
        curve_obj[Curve.PROP_CURVE_ID] = curve_obj.get("unique_id") or str(uuid.uuid4())
    for prop in Curve.LEGACY_PROPS:
        curve_obj.pop(prop, None)


def get_follower_objects():
    # the whole scene, users move followers into their own collections
    return bpy.context.scene.objects


def get_curve_children_map(objects=None):
    """Group every follower by its curve in one pass.

    Returns:
        dict: {curve name: [child objects]}
    """
    objects = objects if objects is not None else get_follower_objects()

    children_by_curve = {}
    for obj in objects:
        parent_name = obj.get(Curve.PROP_CURVE_PARENT)
        if parent_name is not None:
            children_by_curve.setdefault(parent_name, []).append(obj)
    return children_by_curve


@_marks_busy
def update_curves(updated_curves, children_by_curve=None):
    if not updated_curves:
        return

    properties = bpy.context.scene.nms_properties

    # sliders apply as relative changes, so every selected curve keeps its own values
    count_delta = properties.active_curve_number_of_objects - properties.prev_curve_number_of_objects
    radius_delta = properties.active_curve_radius_multiplier - properties.prev_curve_radius_multiplier

    for curve_obj in updated_curves:
        if curve_obj is None or Curve.PROP_CURVE_ID not in curve_obj:
            continue

        try:
            ensure_initialised(curve_obj)
            current_count = curve_obj.get(Curve.PROP_OBJECTS_COUNT, 0)
            current_radius = curve_obj.get(Curve.PROP_RADIUS_MULTIPLIER, 1.0)

            new_number_of_objects = max(1, current_count + count_delta)
            new_radius_multiplier = max(0.001, current_radius + radius_delta)

            total_density = curve_utils.get_total_curve_density(curve_obj, current_count)

            if count_delta != 0 or Curve.PROP_DENSITY_STEP not in curve_obj:
                # count changed from the UI, remember the spacing it gives
                curve_obj[Curve.PROP_DENSITY_STEP] = total_density / max(1, new_number_of_objects - 1)
            else:
                # weights changed, keep the spacing and work out the count from it
                density_step = curve_obj[Curve.PROP_DENSITY_STEP]
                if density_step > 0:
                    new_number_of_objects = max(1, int(round((total_density / density_step) + 1)))
                    if (bpy.context.active_object == curve_obj
                            and properties.active_curve_number_of_objects != new_number_of_objects):
                        # prev first, or the slider callback applies this again
                        properties.prev_curve_number_of_objects = new_number_of_objects
                        properties.active_curve_number_of_objects = new_number_of_objects

            children = (
                children_by_curve.get(curve_obj.name)
                if children_by_curve is not None else None
            )

            if new_number_of_objects != current_count:
                # this also reflows the followers, so the curve is finished here
                duplicate_along_curve(
                    None, curve_obj, new_number_of_objects, new_radius_multiplier,
                    existing_objs=children,
                )
                curve_obj[Curve.PROP_OBJECTS_COUNT] = new_number_of_objects
                continue

            update_curve_children(curve_obj, new_radius_multiplier, children)

        except ReferenceError as error:
            print(error)
            continue

    properties.prev_curve_number_of_objects = properties.active_curve_number_of_objects
    properties.prev_curve_radius_multiplier = properties.active_curve_radius_multiplier


# apply the curve sliders to every selected curve
def update_selected_curves():
    # a rebuild writing the sliders back must not apply them again
    if is_busy():
        return

    properties = bpy.context.scene.nms_properties
    if (properties.active_curve_number_of_objects == properties.prev_curve_number_of_objects
            and properties.active_curve_radius_multiplier == properties.prev_curve_radius_multiplier):
        return

    curves = [
        obj for obj in (getattr(bpy.context, "selected_objects", None) or [])
        if Curve.PROP_CURVE_ID in obj
    ]
    active_object = bpy.context.view_layer.objects.active
    if active_object is not None and Curve.PROP_CURVE_ID in active_object and active_object not in curves:
        curves.append(active_object)

    if curves:
        update_curves(curves, children_by_curve=get_curve_children_map())
    else:
        properties.prev_curve_number_of_objects = properties.active_curve_number_of_objects
        properties.prev_curve_radius_multiplier = properties.active_curve_radius_multiplier


# update children on curve
def update_curve_children(curve_obj, new_radius_multiplier=None, curve_children=None):
    """Refreshes transformations for all objects assigned to this curve."""
    if not curve_obj.get(Curve.PROP_HAS_LINKED_OBJECTS):
        return

    val_data, total_length = curve_utils.build_curve_eval_data(curve_obj, resolution=16)

    if new_radius_multiplier is not None:
        curve_obj[Curve.PROP_RADIUS_MULTIPLIER] = new_radius_multiplier

    if curve_children is None:
        children = get_all_curve_children(curve_obj, require_id=False)
    else:
        children = curve_children

    if not children:
        return

    curve_utils.calculate_curve_factors(curve_obj, children)
    curve_context = curve_utils.build_curve_context(curve_obj)
    curve_name = curve_obj.name
    for obj in children:
        if obj.get(Curve.PROP_CURVE_PARENT) == curve_name:
            curve_utils.update_obj_transformations(
                obj, curve_obj, val_data, total_length, curve_context
            )


@_marks_busy
def duplicate_along_curve(bpy_object, curve, number_of_duplicates=10, radius_multiplier=1.0, existing_objs=None):
    if curve.get(Curve.PROP_HAS_LINKED_OBJECTS, False):
        curve_utils.normalise_curve_scale(curve)

    ensure_initialised(curve)

    curve[Curve.PROP_HAS_LINKED_OBJECTS] = True
    curve[Curve.PROP_RADIUS_MULTIPLIER] = radius_multiplier

    if Curve.PROP_INITIAL_CURVE_SCALE not in curve:
        curve[Curve.PROP_INITIAL_CURVE_SCALE] = curve.scale.x

    if bpy_object is not None:
        store_duplicate_source(curve, bpy_object)

    # callers that already grouped followers by curve can pass them in and skip the scan
    if existing_objs is None:
        existing_objs = get_all_curve_children(curve, require_id=False) or []
    current_count = len(existing_objs)

    if number_of_duplicates < current_count:
        remove_objects_from_curve(current_count - number_of_duplicates, existing_objs)
    elif number_of_duplicates > current_count:
        add_objects_to_curve(number_of_duplicates - current_count, curve, existing_objs, bpy_object)

    update_curve_children(curve, radius_multiplier, existing_objs)
    curve[Curve.PROP_OBJECTS_COUNT] = len(existing_objs)
    return existing_objs


# remember what the curve duplicates, a part or a group
def store_duplicate_source(curve, source_obj):
    if Group.PROP_GROUP_ID in source_obj:
        curve[Curve.PROP_DUP_IS_GROUP] = True
        curve[Curve.PROP_DUP_GROUP_ID] = source_obj[Group.PROP_GROUP_ID]
        curve[Curve.PROP_GROUP_CHILD_CACHE] = source_obj[Group.PROP_CHILD_CACHE]
        curve[Curve.PROP_ORIGIN_MATRIX] = source_obj.get(Group.PROP_ORIGIN_MATRIX, "")
        curve.pop(Curve.PROP_DUP_OBJECT_ID, None)
        if Part.PROP_USER_DATA in source_obj:
            curve[Curve.PROP_DUP_USER_DATA] = source_obj[Part.PROP_USER_DATA]
        else:
            curve.pop(Curve.PROP_DUP_USER_DATA, None)
    else:
        for prop in Curve.GROUP_PROPS:
            curve.pop(prop, None)
        curve[Curve.PROP_DUP_IS_GROUP] = False
        curve[Curve.PROP_DUP_OBJECT_ID] = source_obj[Part.PROP_OBJECT_ID]
        curve[Curve.PROP_DUP_USER_DATA] = source_obj[Part.PROP_USER_DATA]


def is_group_curve(curve):
    return bool(curve.get(Curve.PROP_DUP_IS_GROUP, False)) and Curve.PROP_GROUP_CHILD_CACHE in curve


# colour one follower, a group has one material slot per colour so every slot is painted
def paint_follower(obj, user_data):
    if Group.PROP_GROUP_ID not in obj:
        material.restore_material(obj, user_data)
        return
    try:
        user_data = int(user_data)
    except (TypeError, ValueError):
        return
    Group.apply_colour(obj, userdata.get_colour(user_data), userdata.get_material(user_data))


def build_group_follower(curve):
    origin_matrix = Group.str_to_matrix(curve.get(Curve.PROP_ORIGIN_MATRIX)) or Group.get_default_origin_matrix()
    new_obj = Group.deserialise_to_group(get_builder(), curve[Curve.PROP_GROUP_CHILD_CACHE], origin_matrix)
    if new_obj is not None:
        new_obj[Group.PROP_GROUP_ID] = curve.get(Curve.PROP_DUP_GROUP_ID, new_obj[Group.PROP_GROUP_ID])
    return new_obj


def remove_objects_from_curve(number_to_remove, existing_objs):
    if number_to_remove <= 0:
        return

    # trim the tail, keeping the order of what is left
    keep_count = max(0, len(existing_objs) - number_to_remove)
    doomed = existing_objs[keep_count:]
    del existing_objs[keep_count:]

    # one batch, a remove() per object re-syncs the whole scene each time
    if doomed:
        bpy.data.batch_remove(doomed)


def add_objects_to_curve(number_to_add, curve, existing_objs, bpy_object=None):
    linked_curve_obj_col = collection_utils.get_collection(collection_utils.LINKED_CURVE_OBJ_COL)
    for _ in range(number_to_add):
        if existing_objs:
            new_obj = existing_objs[-1].copy()
            new_obj[Curve.PROP_CURVE_PARENT] = curve.name
            linked_curve_obj_col.objects.link(new_obj)
            existing_objs.append(new_obj)
            continue

        if bpy_object is not None:
            new_obj = bpy_object.copy()
            # colour lives on the mesh material, so recolouring the curve must not touch the source
            new_obj.data = bpy_object.data.copy()
            for constraint in list(new_obj.constraints):
                new_obj.constraints.remove(constraint)
        elif is_group_curve(curve):
            new_obj = build_group_follower(curve)
            if new_obj is None:
                return
        elif Curve.PROP_DUP_OBJECT_ID in curve:
            new_item = get_builder().add_part(
                curve[Curve.PROP_DUP_OBJECT_ID], user_data=curve.get(Curve.PROP_DUP_USER_DATA, 0)
            )
            new_obj = new_item.object
        else:
            return

        if Curve.PROP_DUP_USER_DATA in curve:
            paint_follower(new_obj, curve[Curve.PROP_DUP_USER_DATA])
            if Group.PROP_GROUP_ID in new_obj:
                new_obj[Part.PROP_USER_DATA] = curve[Curve.PROP_DUP_USER_DATA]

        constraint = new_obj.constraints.new(type='FOLLOW_PATH')
        constraint.target = curve
        constraint.use_fixed_location = True
        constraint.use_curve_follow = True

        new_obj[Curve.PROP_CURVE_PARENT] = curve.name
        new_obj[Curve.PROP_BASE_SCALE] = 1.0
        new_obj.rotation_euler = (math.pi, 0, 0)
        new_obj.location = (0, 0, 0)
        new_obj.hide_select = True

        collection_utils.move_object_into_collection(linked_curve_obj_col, new_obj)
        existing_objs.append(new_obj)


# check if given object is a supported curve or not
def is_bezier_or_nurbs_path(curve):
    if not curve or curve.type != 'CURVE':
        return False
    for spline in curve.data.splines:
        if spline.type in {'BEZIER', 'NURBS'}:
            return True
    return False


@_marks_busy
def apply_curve_transforms_and_detach(curve):
    """Bake the FOLLOW_PATH transforms into the followers and free them from the curve."""
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")

    duplicates = []

    # matrix_world is stale until the scene is evaluated
    bpy.context.view_layer.update()

    unlinked_curve_obj_col = collection_utils.get_collection(collection_utils.UNLINKED_CURVE_OBJ_COL)

    child_props_to_delete = (
        Curve.PROP_BASE_SCALE,
        Curve.PROP_CURVE_FACTOR,
        Curve.PROP_RADIUS,
        Curve.PROP_CURVE_PARENT,
    )

    for obj in get_all_curve_children(curve, require_id=False):
        for prop in child_props_to_delete:
            obj.pop(prop, None)

        baked_matrix = obj.matrix_world.copy()
        for constraint in [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]:
            obj.constraints.remove(constraint)
        # re-apply so the object doesn't move when the constraint drops
        obj.matrix_world = baked_matrix

        # followers share a mesh, a detached part needs its own to be recoloured alone
        obj.data = obj.data.copy()
        obj.hide_select = False
        obj.lock_location = (False, False, False)
        duplicates.append(obj)

        collection_utils.move_object_into_collection(unlinked_curve_obj_col, obj)

    curve_props_to_delete = (
        Curve.PROP_CURVE_ID,
        Curve.PROP_HAS_LINKED_OBJECTS,
        Curve.PROP_DUP_OBJECT_ID,
        Curve.PROP_DUP_USER_DATA,
        Curve.PROP_RADIUS_MULTIPLIER,
        Curve.PROP_OBJECTS_COUNT,
        Curve.PROP_DENSITY_STEP,
    ) + Curve.GROUP_PROPS + Curve.LEGACY_PROPS

    for prop in curve_props_to_delete:
        curve.pop(prop, None)

    return curve, duplicates


# make all objects linked to a curve unselectable
def lock_all_objects(curve_obj):
    for obj in get_all_curve_children(curve_obj, require_id=False):
        obj.hide_select = True


# make all objects linked to a curve selectable
def unlock_all_objects(curve_obj):
    for obj in get_all_curve_children(curve_obj, require_id=False):
        obj.hide_select = False


# make the curve of a follower selectable and its followers not, returns the curve
def select_parent_curve(obj):
    parent_curve_name = obj.get(Curve.PROP_CURVE_PARENT, None)
    if parent_curve_name is None:
        return None

    parent_curve = bpy.data.objects.get(parent_curve_name)
    if parent_curve is not None and not parent_curve.get(Curve.PROP_PARENT_SELECTED, False):
        parent_curve.hide_select = False
        parent_curve[Curve.PROP_PARENT_SELECTED] = True
        lock_all_objects(parent_curve)
    return parent_curve


# make the followers of a curve selectable and the curve not, returns the followers
def select_children_of_curve(curve):
    if not is_bezier_or_nurbs_path(curve):
        return None

    children = get_all_curve_children(curve, require_id=False)
    for obj in children:
        obj.hide_select = False

    curve_utils.normalise_curve_scale(curve)
    curve.hide_select = True
    curve[Curve.PROP_PARENT_SELECTED] = False
    return children


def get_all_curve_children(curve_obj, require_id=True):
    if curve_obj is None:
        return None
    if require_id and Curve.PROP_CURVE_ID not in curve_obj:
        return None

    return [
        obj for obj in get_follower_objects()
        if obj.get(Curve.PROP_CURVE_PARENT) == curve_obj.name
    ]


# the curve itself, or the curve an object follows
def get_curve_or_linked_curve(obj):
    if obj is None:
        return None

    if is_bezier_or_nurbs_path(obj) and obj.get(Curve.PROP_HAS_LINKED_OBJECTS, False):
        return obj
    if Curve.PROP_CURVE_PARENT in obj:
        return bpy.data.objects.get(obj[Curve.PROP_CURVE_PARENT])
    return None


# delete selected curve and children linked to it
def delete_curve_and_children(curve):
    if curve is None:
        raise TypeError("Selected object is None")

    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Object is not a curve")

    if not curve.get(Curve.PROP_HAS_LINKED_OBJECTS, False):
        raise TypeError("Object has no linked children")

    doomed = [
        obj for obj in bpy.data.objects
        if obj.get(Curve.PROP_CURVE_PARENT) == curve.name
    ]
    if doomed:
        bpy.data.batch_remove(doomed)

    try:
        bpy.data.objects.remove(curve, do_unlink=True)
    except ReferenceError:
        pass

    return len(doomed)


# replace the objects on a curve with source_obj
def replace_curve_object(curve_obj, source_obj):
    new_curve_obj = curve_obj.copy()
    new_curve_obj.data = curve_obj.data.copy()
    new_curve_obj[Curve.PROP_CURVE_ID] = str(uuid.uuid4())

    for collection in curve_obj.users_collection:
        collection.objects.link(new_curve_obj)

    store_duplicate_source(new_curve_obj, source_obj)

    sync_curves(new_curve_obj, curve_obj, duping_object_source=source_obj)

    return new_curve_obj, curve_obj


# reset a curve to its default state and delete all children on it
def reset_curve(curve):
    if curve is None:
        raise TypeError("curve is None")

    if not is_bezier_or_nurbs_path(curve) or Curve.PROP_HAS_LINKED_OBJECTS not in curve:
        raise TypeError("object is not a valid curve")

    curve_obj, duplicates = apply_curve_transforms_and_detach(curve)
    if duplicates:
        bpy.data.batch_remove(duplicates)
    return curve_obj


def _copy_curve(curve_obj):
    new_curve_obj = curve_obj.copy()
    new_curve_obj.data = curve_obj.data.copy()
    new_curve_obj[Curve.PROP_CURVE_ID] = str(uuid.uuid4())
    parent_collection = collection_utils.get_parent_collection(curve_obj) or bpy.context.scene.collection
    parent_collection.objects.link(new_curve_obj)
    return new_curve_obj


def duplicate_curve(curve_obj):
    if curve_obj is None:
        return None

    new_curve_obj = _copy_curve(curve_obj)
    sync_curves(new_curve_obj, curve_obj)
    return new_curve_obj


# mirror a curve and the objects duplicated along it
def mirror_curve(curve_obj, axis="Z", center=None, auto_duplicate=False):
    if not is_bezier_or_nurbs_path(curve_obj):
        return None

    new_curve_obj = _copy_curve(curve_obj) if auto_duplicate else curve_obj

    curve_utils.mirror_curve(new_curve_obj, axis, center)

    if is_group_curve(new_curve_obj):
        # mirror the group's cache, followers are rebuilt from it
        new_child_cache, new_origin_matrix = Group.mirror_cache_data(
            new_curve_obj[Curve.PROP_GROUP_CHILD_CACHE],
            Group.str_to_matrix(new_curve_obj.get(Curve.PROP_ORIGIN_MATRIX)),
            axis,
            center,
        )
        if new_child_cache is not None:
            new_curve_obj[Curve.PROP_GROUP_CHILD_CACHE] = new_child_cache
            new_curve_obj[Curve.PROP_ORIGIN_MATRIX] = Group.matrix_to_str(new_origin_matrix)
    else:
        # switch to the mirror part when one exists
        object_id = new_curve_obj.get(Curve.PROP_DUP_OBJECT_ID)
        mirror_obj_id = Part.get_mirror_part_id(object_id) if object_id else None
        if mirror_obj_id in get_builder().nice_name_dictionary:
            new_curve_obj[Curve.PROP_DUP_OBJECT_ID] = mirror_obj_id

    sync_curves(new_curve_obj, curve_obj, True, axis, from_mirror=True)
    return new_curve_obj


@_marks_busy
def sync_curves(target_curve, source_curve, do_mirror=False, axis=None, from_mirror=False, duping_object_source=None):
    """Rebuild target_curve's followers to match source_curve's, optionally mirrored.

    Followers are matched by index, so per object edits made by the user carry over.
    """
    target_curve[Curve.PROP_CURVE_ID] = str(uuid.uuid4())

    source_dupe_objects = get_all_curve_children(source_curve, require_id=False)

    radius_multiplier = target_curve[Curve.PROP_RADIUS_MULTIPLIER]
    number_of_objects = target_curve[Curve.PROP_OBJECTS_COUNT]

    if duping_object_source is not None:
        duping_object = duping_object_source
    elif source_dupe_objects and not from_mirror:
        duping_object = source_dupe_objects[0]
    else:
        duping_object = None

    target_dupe_objects = duplicate_along_curve(
        duping_object, target_curve, number_of_objects, radius_multiplier
    )

    target_is_group = is_group_curve(target_curve)
    if target_dupe_objects and not target_is_group:
        target = target_dupe_objects[0]
        material.restore_material(target, target.get(Part.PROP_USER_DATA, 0))

    if Curve.PROP_DUP_USER_DATA in source_curve:
        apply_color(target_curve, source_curve[Curve.PROP_DUP_USER_DATA])

    for source, target in zip(source_dupe_objects, target_dupe_objects):
        target.rotation_euler = source.rotation_euler.copy()
        target.scale = source.scale.copy()
        target.location = source.location.copy()
        target[Curve.PROP_BASE_SCALE] = source.get(Curve.PROP_BASE_SCALE, 1.0)

        if do_mirror:
            target.location.x = -target.location.x
            target.rotation_euler.y = -target.rotation_euler.y
            target.rotation_euler.z = -target.rotation_euler.z

            if axis == "Z" and target_is_group:
                target.rotation_euler.x += math.pi
                target.rotation_euler.z += math.pi


# scale of a follower before the curve's radius and scale are applied
def calculate_base_scale(curve, obj):
    curve_scale_multiplier = curve.scale.x / curve.get(Curve.PROP_INITIAL_CURVE_SCALE, curve.scale.x)
    radius_multiplier = curve.get(Curve.PROP_RADIUS_MULTIPLIER, 1.0)
    point_radius = obj.get(Curve.PROP_RADIUS, 1.0)
    return obj.scale.x / (point_radius * radius_multiplier * curve_scale_multiplier)


# change color of objects on curve
def apply_color(curve_obj, user_data):
    if curve_obj is None:
        return None

    if Curve.PROP_HAS_LINKED_OBJECTS in curve_obj and is_bezier_or_nurbs_path(curve_obj):
        curve_obj[Curve.PROP_DUP_USER_DATA] = user_data
        children = get_all_curve_children(curve_obj, require_id=False)
        if not children:
            return None

        # followers share one mesh, so painting the first colours them all,
        # but each one saves its own UserData
        paint_follower(children[0], user_data)
        painted_user_data = children[0].get(Part.PROP_USER_DATA, str(user_data))
        for child_obj in children:
            child_obj[Part.PROP_USER_DATA] = painted_user_data
