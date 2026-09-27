"""Fast bulk import of parts from NMS data.

The import collection is excluded from the view layer while parts are created,
and parts with the same ObjectID and UserData share one mesh.
"""

import time

import bpy

from ..part import Part
from ..utils import collection_utils, material
from . import overrides

# name of collection to import objects to
IMPORT_COLLECTION_NAME = "Collection"


def import_objects(builder_object, objects_data, compensate_normal=True):
    unique_objects = {}
    unique_materials = {}

    import_collection = collection_utils.get_collection(IMPORT_COLLECTION_NAME)
    set_collection_excluded(import_collection.name, True)

    # a bad part must never leave the collection excluded
    try:
        for order, part_data in enumerate(objects_data):
            raw_object_id = part_data.get(Part.PROP_OBJECT_ID, None)
            if raw_object_id is None:
                continue

            object_id = raw_object_id.replace("^", "")
            user_data = part_data.get(Part.PROP_USER_DATA, 0)

            override_class = overrides.get_override_class(object_id)
            if override_class is not None:
                override_class.deserialise_from_data(
                    part_data, builder_object, compensate_normal=compensate_normal
                )
                continue

            bpy_object = build_fbx_part(
                builder_object,
                object_id,
                user_data,
                import_collection,
                unique_objects,
                unique_materials,
            )
            if bpy_object is None:
                continue

            restore_params(bpy_object, part_data, object_id)
            bpy_object.matrix_world = deserialise_matrix_world(part_data)
            bpy_object[Part.PROP_ORDER] = order
    finally:
        set_collection_excluded(import_collection.name, False)
        bpy.context.view_layer.update()


def set_collection_excluded(collection_name, excluded):
    layer_collection = bpy.context.view_layer.layer_collection.children.get(
        collection_name
    )
    if layer_collection:
        layer_collection.exclude = excluded


# colour is a flat material on the mesh, so objects can only share a mesh
# when their ObjectID AND UserData match
def build_fbx_part(
    builder_object, object_id, user_data, import_collection, unique_objects, unique_materials
):
    material_key = (object_id, user_data)

    # import object from disk when visiting that object_id for first time
    if object_id not in unique_objects:
        bpy_object = import_fbx_from_disk(builder_object, object_id)
        if bpy_object is None:
            return None

        collection_utils.move_object_into_collection(import_collection, bpy_object)
        material.restore_material(bpy_object, user_data)
        builder_object.add_to_part_cache(object_id, bpy_object)

        unique_objects[object_id] = bpy_object
        unique_materials[material_key] = bpy_object.data
        return bpy_object

    bpy_object = unique_objects[object_id].copy()
    import_collection.objects.link(bpy_object)

    if material_key in unique_materials:
        bpy_object.data = unique_materials[material_key]
    else:
        bpy_object.data = bpy_object.data.copy()
        material.restore_material(bpy_object, user_data)
        unique_materials[material_key] = bpy_object.data

    return bpy_object


def import_fbx_from_disk(builder_object, object_id):
    fbx_path = builder_object.get_obj_path(object_id)

    objects_before = set(bpy.data.objects)
    try:
        if fbx_path is None:
            bpy.ops.mesh.primitive_cube_add()
        else:
            bpy.ops.import_scene.fbx(filepath=fbx_path)
    except RuntimeError:
        pass
    new_objects = [item for item in bpy.data.objects if item not in objects_before]

    if not new_objects:
        # cube ops fail when the active collection is excluded
        if fbx_path is not None:
            return None
        bpy_object = bpy.data.objects.new(object_id, bpy.data.meshes.new(object_id))
    else:
        bpy_object = next(
            (item for item in new_objects if item.type == "MESH"), new_objects[0]
        )

    bpy_object.name = object_id
    if bpy_object.data is not None:
        bpy_object.data.materials.clear()

    try:
        bpy_object.select_set(False)
    except RuntimeError:
        pass

    return bpy_object


# copy params from part json to bpy_object
def restore_params(bpy_object, part_data, object_id):
    user_data = part_data.get(Part.PROP_USER_DATA, "")
    time_stamp = str(part_data.get(Part.PROP_TIMESTAMP, int(time.time())))
    message = part_data.get(Part.PROP_MESSAGE, None)

    bpy_object[Part.PROP_OBJECT_ID] = object_id
    bpy_object[Part.PROP_SNAP_ID] = object_id
    bpy_object[Part.PROP_USER_DATA] = str(user_data)
    bpy_object[Part.PROP_TIMESTAMP] = time_stamp
    bpy_object[Part.PROP_BELONGS_TO_PRESET] = False

    # copies carry the source's message, so clear it when this part has none
    if message:
        bpy_object[Part.PROP_MESSAGE] = message
    else:
        bpy_object.pop(Part.PROP_MESSAGE, None)

    return bpy_object


# convert position, up and at to matrix world for blender object
def deserialise_matrix_world(part_data):
    pos = part_data.get(Part.PROP_POSITION, [0.0, 0.0, 0.0])
    up = part_data.get(Part.PROP_UP, [0.0, 0.0, 0.0])
    at = part_data.get(Part.PROP_AT, [0.0, 0.0, 0.0])
    return Part.create_matrix_from_vectors(pos, up, at)
