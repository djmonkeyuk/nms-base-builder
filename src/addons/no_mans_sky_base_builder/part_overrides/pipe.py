import os

import bpy

from .. import part
from ..builder import paths
from ..utils import pipe_utils


ARROW_MATERIAL = "PIPE arrow"
ARROW_COLOUR = (1.0, 0.35, 0.0, 1.0)


class BASE_BUBPIPE(part.Part):
    """The bubble duct model is centred, it is moved so it shows where the game puts it."""

    def retrieve_object_from_id(self, object_id):
        bpy_object = super(BASE_BUBPIPE, self).retrieve_object_from_id(object_id)
        # duplicates share the mesh, so only the first one moves it
        pipe_utils.move_to_game_frame(bpy_object)
        return bpy_object


class PIPE(part.Part):
    """The game shows a pipe block as a straight, elbow, T or cross from what it joins, so it is shown the same."""

    def build_rig(self):
        update_pipe_shapes([self.object])


def update_pipe_shapes(bpy_objects=None):
    """Show each pipe block as the shape the game turns it into.

    Args:
        bpy_objects (list): The blocks to update, all of them when not given.
    """
    blocks = [o for o in bpy.context.scene.objects if o.get("ObjectID") == "PIPE"]
    for bpy_object in bpy_objects or blocks:
        sides = pipe_utils.get_joined_sides(bpy_object, blocks)
        # the part's colour is always the first slot, the arrows have the second
        material = bpy_object.data.materials[0] if bpy_object.data and bpy_object.data.materials else None
        shape_mesh = get_shape_mesh(sides, material)
        if shape_mesh and bpy_object.data != shape_mesh:
            bpy_object.data = shape_mesh


def get_shape_mesh(sides, material=None):
    """Get the mesh for a block with these sides joined, one is kept for each turn and material.

    Args:
        sides (tuple): The joined sides, from pipe_utils.get_joined_sides.
        material (bpy.types.Material): The colour the block keeps.
    """
    shape_id, turn = pipe_utils.get_block_shape(sides)
    if not shape_id:
        return None
    name = " ".join(["PIPE"] + list(sides) + ([material.name] if material else []))
    shape_mesh = bpy.data.meshes.get(name)
    if shape_mesh:
        return shape_mesh

    shape_mesh = load_shape_mesh(shape_id).copy()
    shape_mesh.name = name
    shape_mesh.transform(turn)
    # swapped into the slots rather than cleared, clearing would move the arrow faces to the first slot
    while len(shape_mesh.materials) < 2:
        shape_mesh.materials.append(None)
    shape_mesh.materials[0] = material
    shape_mesh.materials[1] = get_arrow_material()
    return shape_mesh


def get_arrow_material():
    """Get the bright material the turn arrows show in, so they stand out on any pipe colour."""
    material = bpy.data.materials.get(ARROW_MATERIAL)
    if not material:
        material = bpy.data.materials.new(ARROW_MATERIAL)
        material.diffuse_color = ARROW_COLOUR
    return material


def load_shape_mesh(shape_id):
    """Load a shape's model once, the straight is the pipe block's own model."""
    name = "PIPE shape " + shape_id
    shape_mesh = bpy.data.meshes.get(name)
    if shape_mesh:
        return shape_mesh

    folder = os.path.join(paths.MODEL_PATH, "decoration") if shape_id == "PIPE" else paths.PIPE_SHAPES_PATH
    view_layer = bpy.context.view_layer
    active_object = view_layer.objects.active
    selected_objects = [o for o in view_layer.objects if o.select_get()]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(folder, shape_id + ".glb"))
    for new_object in set(bpy.data.objects) - before:
        if new_object.type == "MESH":
            shape_mesh = new_object.data
        bpy.data.objects.remove(new_object)

    # the import takes the selection, give it back
    for bpy_object in selected_objects:
        bpy_object.select_set(True)
    view_layer.objects.active = active_object
    shape_mesh.name = name
    return shape_mesh
