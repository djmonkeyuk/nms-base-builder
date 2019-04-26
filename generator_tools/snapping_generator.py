from maya import cmds
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
    
import json    
with open("C:/Users/charl/AppData/Roaming/Blender Foundation/Blender/2.79/scripts/addons/no-mans-sky-base-builder/snapping_info.json", "w") as stream:
    json.dump(snap_dict, stream)
    
         