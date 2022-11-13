import json
import os

from maya import cmds

PLUGIN_PATH = "C:/Users/charl/AppData/Roaming/Blender Foundation/Blender/3.3/scripts/addons/no_mans_sky_base_builder/"

# Find missing parts.
scene_objects = cmds.ls(type="transform")
plugin_objects = {}
model_path = os.path.join(PLUGIN_PATH, "models")
cats = os.listdir(model_path)
for cat in cats:
    full_cat_path = os.path.join(model_path, cat)
    models = os.listdir(full_cat_path)
    for model in models:
        part_name = model.split(".")[0]
        plugin_objects[part_name] = os.path.join(full_cat_path, model)

missing = [x for x in plugin_objects.keys() if x not in scene_objects]
for miss in missing:
    cmds.file(plugin_objects[miss], i=True, type="OBJ", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, rpr=miss, options="mo=1")


# -------------------

# Generate Snapping Dictionary.
top_groups = [x for x in cmds.ls("|*", type="transform") if x not in ["front", "persp", "side", "top"]]
snap_dict = {}

for top_group in top_groups:
    category_dict = snap_dict[top_group] = {}
    category_dict["snap_points"] = {}

    transforms = cmds.listRelatives(top_group, c=True, f=True)
    meshes = []
    snaps = []
    for trans in transforms:
        shapes = cmds.listRelatives(trans, c=True, f=True)
        for shape in shapes:
            if cmds.objectType(shape) == "mesh":
                meshes.append(trans)
            if cmds.objectType(shape) == "locator":
                snaps.append(trans)

    meshes_key_items = [x.split("|")[-1] for x in meshes]
    parts = category_dict["parts"] = meshes_key_items
    meshes_key = top_group

    local_dict = {}
    for snap_key in snaps:
        world_matrix = cmds.xform(snap_key, ws=True, q=True, m=True)
        blender_matrix_format = [
            [world_matrix[0], world_matrix[4], world_matrix[8], world_matrix[12]],
            [world_matrix[1], world_matrix[5], world_matrix[9], world_matrix[13]],
            [world_matrix[2], world_matrix[6], world_matrix[10], world_matrix[14]],
            [world_matrix[3], world_matrix[7], world_matrix[11], world_matrix[15]]
        ]
        matrix_dict = {"matrix": blender_matrix_format}
        short_snap_key = snap_key.split("|")[-1]
        if cmds.attributeQuery("opposite", node=snap_key, exists=True):
            matrix_dict["opposite"] = cmds.getAttr(snap_key+".opposite")
        category_dict["snap_points"][short_snap_key] = matrix_dict

    snap_dict[meshes_key] = category_dict


with open(PLUGIN_PATH+"/resources/snapping_info.json", "w") as stream:
    json.dump(snap_dict, stream)
