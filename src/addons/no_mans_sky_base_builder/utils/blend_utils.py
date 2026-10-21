"""Convenient methods to perform common blender related tasks."""

import math

import addon_utils
import bmesh
import bpy
from ..utils import blend_utils


def ShowMessageBox(message="", title="Message Box", icon="INFO"):
    """Show a message in a popup, or print it when there is no window."""
    # popups crash blender when there is no window, e.g. in background mode
    if bpy.app.background or bpy.context.window_manager is None or not bpy.context.window_manager.windows:
        print(f"{title}: {message}")
        return

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def load_plugin(plugin_name):
    """Load a blender plugin."""
    is_enabled, _ = addon_utils.check(plugin_name)
    if not is_enabled:
        addon_utils.enable(plugin_name)


def add_to_scene(item, collection_name="Collection"):
    """Add an item to the main blender collection.

    A Collection is a concept introduced in Blender 2.8. Which can be seen
    as a group/scene of items.

    By default we should add all new items to the default "Collection".

    Args:
        item (bpy_types.Object): The blender object.
        collection_name(str): The name of the collection to place the item in.
    """
    # Validate collection existence.
    if collection_name not in bpy.data.collections:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    # Add the item to the collection.
    collection = bpy.data.collections[collection_name]
    if item.name not in collection.objects:
        collection.objects.link(item)

    # operators like the fbx importer also link to the active collection
    for other_collection in list(item.users_collection):
        if other_collection != collection:
            other_collection.objects.unlink(item)


def get_item_by_name(item_name):
    """Get a Blender object by specifying the name of the object.

    Args:
        item_name (str): The name of the item.

    Returns:
        bpy_types.Object: The Blender object.
    """
    return bpy.data.objects[item_name]


def item_exists_by_name(item_name):
    """Check for a Blender object by specifying the name of the object.

    Args:
        item_name (str): The name of the item.

    Returns:
        bool: True iff object exists.
    """
    return item_name in bpy.data.objects


def remove_object(name):
    """Remove an item from the scene by specifying it's name.

    Args:
        name (str): The name of the object to remove.
    """
    objs = bpy.data.objects
    if name in objs:
        objs.remove(objs[name], do_unlink=True)


# Force refresh of scene so the matrix values are correct.
def scene_refresh():
    """Force the dependency graph to update.

    This is sometimes required when adding and removing constraints on
    certain objects.
    """
    layer = bpy.context.view_layer
    layer.update()


def set_active_item(item):
    """Set the item to be the active item.

    This is similar to the selected state.

    Args:
        item (bpy_types.Object): The item to set as active.
    """
    bpy.context.view_layer.objects.active = item


def select(selection, add=False):
    """Select an item.

    The add flag determines if the item is appended to the current selection
    or if we should only select that particular item.

    Args:
        selection (bpy_types.Object, list): The item to be selected.
            This can be a singular object or a list of objects.
        add (bool): Appends the selection if `True` else select by itself.
    """
    # Deselect all.
    if not add:
        bpy.ops.object.select_all(action="DESELECT")
        set_active_item(None)

    # Ensure List.
    if not isinstance(selection, list):
        selection = [selection]

    for item in selection:
        item.select_set(True)

    # Make the last item the active one.
    selection[-1].select_set(True)
    set_active_item(selection[-1])


def get_selected_active_object():
    """The active object, only when it is also selected.

    Read from the view layer, context.active_object is missing in timers and
    other restricted contexts.
    """
    view_layer = getattr(bpy.context, "view_layer", None)
    if view_layer is None:
        return None
    try:
        active_object = view_layer.objects.active
        if active_object is None or not active_object.select_get(view_layer=view_layer):
            return None
        return active_object
    except (ReferenceError, RuntimeError):
        return None


def get_current_selection():
    """Get the current selected item.

    Returns:
        bpy_types.Object: The selected item.
    """
    selected_objects = [o for o in bpy.context.scene.objects if o.select_get()]
    if selected_objects:
        return selected_objects[-1]


def get_distance_between(matrix1, matrix2):
    """Get the distance between two matrices.

    Args:
        matrix1: First matrix input.
        matrix2: Second matrix input.

    Returns:
        float: The distance between the two.
    """
    translate1 = matrix1.decompose()[0]
    translate2 = matrix2.decompose()[0]
    return math.sqrt(
        (translate2.x - translate1.x) ** 2
        + (translate2.y - translate1.y) ** 2
        + (translate2.z - translate1.z) ** 2
    )


def delete(bpy_object):
    """Remove the item and everything below it."""
    # removed at data level, selecting fails for objects outside the view layer
    for part in list(bpy_object.children):
        bpy.data.objects.remove(part, do_unlink=True)
    bpy.data.objects.remove(bpy_object, do_unlink=True)
    
    
def find_duplicates(decimals = 4):
    """
    Removes duplicate objects based on:
        - name
        - world location
        - world rotation
        - world scale

    Keeps the first found object unselected and select subsequent duplicates.
    """

    seen_objects = {}
    duplicates = []

    for obj in bpy.data.objects:
        location_vector, rotation_quaternion, scale_vector = obj.matrix_world.decompose()
        
        location = (
            round(location_vector.x,decimals),
            round(location_vector.y,decimals),
            round(location_vector.z,decimals)
        )
        
        rotation_euler = rotation_quaternion.to_euler("XYZ")
        rotation = (
            round(rotation_euler.x, decimals),
            round(rotation_euler.y, decimals),
            round(rotation_euler.z, decimals)
        )
        
        scale = round(scale_vector.x, decimals)
        object_key = (
            obj.get("ObjectID",obj.name),
            location,
            rotation,
            scale,
        )
        
        if object_key in seen_objects:
            duplicates.append(obj.get("object", obj))
        else:
            seen_objects[object_key] = obj

    # select duplicates
    for obj in duplicates:
        blend_utils.select(duplicates)

    print(f"Selected {len(duplicates)} duplicate objects")
    return len(duplicates)

def duplicate_part(target):
    """ Duplicate an object and place it in same collection as original object
        Return duplicated object
    """
    new_item = target.copy()
    if new_item.data:
        new_item.data = target.data.copy()
    for collection in target.users_collection:
        collection.objects.link(new_item)
    return new_item


def deselect_all():
    """Clear the selection without going through bpy.ops."""
    view_layer = bpy.context.view_layer
    for item in view_layer.objects:
        if item.select_get(view_layer=view_layer):
            item.select_set(False, view_layer=view_layer)


def select_only(item):
    deselect_all()
    view_layer = bpy.context.view_layer
    if item.name in view_layer.objects:
        item.select_set(True)
        view_layer.objects.active = item


def needs_operator_join(objects):
    # vertex groups, shape keys and object linked materials are dropped by a bmesh merge
    for obj in objects:
        if obj.vertex_groups or obj.data.shape_keys:
            return True
        for slot in obj.material_slots:
            if slot.link != 'DATA':
                return True
    return False


# above this many vertices the join operator is faster than bmesh
BMESH_MERGE_VERT_LIMIT = 110000


def merge_objects_with_bmesh(objects, object_name):
    """Join meshes directly into the first object's space, without bpy.ops."""
    base = objects[0]
    base_inverse = base.matrix_world.inverted()

    # slots are pooled by material across every object, in first seen order
    materials = []
    material_indices = {}

    bm = bmesh.new()
    for obj in objects:
        slot_map = []
        for slot in obj.material_slots:
            material = slot.material
            if material is None:
                slot_map.append(0)
                continue
            index = material_indices.get(material.name)
            if index is None:
                index = len(materials)
                material_indices[material.name] = index
                materials.append(material)
            slot_map.append(index)

        needs_remap = slot_map != list(range(len(slot_map)))

        if obj is base and not needs_remap:
            bm.from_mesh(obj.data)
            continue

        # Mesh.transform also carries custom split normals, a vertex loop would not
        mesh_copy = obj.data.copy()
        if obj is not base:
            mesh_copy.transform(base_inverse @ obj.matrix_world)

        if needs_remap:
            last_slot = len(slot_map) - 1
            indices = [0] * len(mesh_copy.polygons)
            mesh_copy.polygons.foreach_get("material_index", indices)
            mesh_copy.polygons.foreach_set(
                "material_index",
                [slot_map[i if i <= last_slot else last_slot] for i in indices],
            )

        bm.from_mesh(mesh_copy)
        bpy.data.meshes.remove(mesh_copy)

    mesh = bpy.data.meshes.new(object_name)
    bm.to_mesh(mesh)
    bm.free()

    for material in materials:
        mesh.materials.append(material)

    merged = bpy.data.objects.new(object_name, mesh)
    for collection in base.users_collection:
        collection.objects.link(merged)
    merged.matrix_world = base.matrix_world.copy()
    return merged


def merge_objects_with_operator(objects, object_name):
    view_layer = bpy.context.view_layer
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    view_layer.objects.active = objects[0]

    # duplicate leaves its copy of the active object active, which is what gets joined into
    meshes_before = set(bpy.data.meshes)
    bpy.ops.object.duplicate(linked=False)
    bpy.ops.object.join()

    merged = view_layer.objects.active
    merged.name = object_name

    # join keeps only the active mesh, the other duplicated meshes are left unused
    orphans = [
        mesh for mesh in bpy.data.meshes
        if mesh.users == 0 and mesh not in meshes_before
    ]
    if orphans:
        bpy.data.batch_remove(orphans)

    for key in list(merged.keys()):
        del merged[key]

    return merged


def merge_objects(objects, object_name):
    """Merge mesh objects into a new object, leaving the originals untouched.

    Returns:
        bpy.types.Object | None
    """
    objects = [obj for obj in objects if obj and obj.type == 'MESH']
    if not objects:
        print("No objects to merge")
        return None

    try:
        total_verts = sum(len(obj.data.vertices) for obj in objects)
        if needs_operator_join(objects) or total_verts > BMESH_MERGE_VERT_LIMIT:
            merged = merge_objects_with_operator(objects, object_name)
        else:
            merged = merge_objects_with_bmesh(objects, object_name)

        merged.data.update()
        select_only(merged)
        return merged

    except Exception as error:
        print("Error Occured while grouping objects : ", str(error))
        return None