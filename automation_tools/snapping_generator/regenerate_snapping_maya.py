from maya import cmds

# Reconsutrct snap data in maya
data = {}

top_groups = data.keys()
for top_group in top_groups:
    if not cmds.objExists(top_group):
        cmds.group(name=top_group, empty=True, world=True)

    #parts
    for part in data[top_group]["parts"]:
        if not cmds.objExists(part):
            new_mesh = cmds.createNode("mesh", name=part+"Shape")
            new_mesh_transform = cmds.listRelatives(new_mesh, parent=True)[0]
            new_mesh_transform = cmds.rename(new_mesh_transform, part)
            new_mesh_transform = cmds.parent(new_mesh_transform, top_group)[0]

    #snap points
    for snap_point_name, snap_point_data in data[top_group]["snap_points"].items():
        if not cmds.objExists(top_group+"|"+snap_point_name):
            rows = snap_point_data["matrix"]

            maya_matrix_format = [
                rows[0][0], rows[1][0], rows[2][0], rows[3][0],
                rows[0][1], rows[1][1], rows[2][1], rows[3][1],
                rows[0][2], rows[1][2], rows[2][2], rows[3][2],
                rows[0][3], rows[1][3], rows[2][3], rows[3][3]
            ]

            new_loc = cmds.spaceLocator(name=snap_point_name)[0]
            new_loc = cmds.parent("|"+new_loc, top_group)[0]

            cmds.xform(new_loc, matrix=maya_matrix_format, worldSpace=True)

            if "opposite" in snap_point_data:
                cmds.addAttr(new_loc, ln="opposite", dt="string")
                cmds.setAttr(new_loc+".opposite", snap_point_data["opposite"], type="string")
