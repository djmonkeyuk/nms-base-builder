import os

import yaml


def get_nice_ui_parts():
    data = []
    file_read = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "resources/asset_data.yaml")
    with open(file_read) as stream:
        data = yaml.safe_load(stream)

    all_listed_items = []
    for top_data in data:
        for top, top_sub_data in top_data.items():
            if not top_sub_data:
                continue
            for cat in top_sub_data:
                print(cat)
                for cat_name, items in cat.items():
                    if not items:
                        continue
                    all_listed_items.extend(items)
    return all_listed_items

def list_models():
    model_dir = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..", "models")
    # model_dir = "N:/Documents/dev/nms-base-builder/src/addons/no_mans_sky_base_builder/models"
    all_models = []
    for sub_dir in os.listdir(model_dir):
        full_dir = os.path.join(model_dir, sub_dir)
        models = [x.split(".")[0] for x in os.listdir(full_dir)]
        all_models.extend(models)
    return all_models


def list_missing_parts():
    nice_parts = get_nice_ui_parts()
    models = list_models()
    return [x for x in models if x not in nice_parts]

def list_missing_models():
    nice_parts = get_nice_ui_parts()
    models = list_models()
    return [x for x in nice_parts if x not in models]


def list_parts_in_folder():
    folder = "N:/OneDrive/NMSBaseBuildShare/models/decorations"
    for item in os.listdir(folder):
        print ("- {}".format(item.replace(".blend", "")))


def convert_blend_to_obj():
    import os

    import bpy
    file_path = "N:/OneDrive/NMSBaseBuildShare/models/alloy"
    all_files = os.listdir(file_path)
    for f in all_files:
        if not f.endswith(".blend"):
            continue
        full_file = os.path.join(file_path, f)
        bpy.ops.wm.open_mainfile(filepath=full_file)
        target_file = os.path.join(file_path, "OBJ", f.replace(".blend", ".obj"))
        bpy.ops.export_scene.obj(filepath=target_file)


def import_folder_into_maya():
    from maya import cmds
    folder_path = "N:/OneDrive/NMSBaseBuildShare/models/alloy/OBJ/"
    for sub_file in os.listdir(folder_path):
        if not sub_file.endswith(".obj"):
            continue
        id = sub_file.split(".")[0]
        pre = cmds.ls("|*")
        cmds.file("N:/OneDrive/NMSBaseBuildShare/models/alloy/OBJ/{}.obj".format(id), i=True, type="OBJ", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, rpr="F_ARCH", options="mo=1", pr=True, importTimeRange="combine")
        post = cmds.ls("|*")
        mesh = [x for x in post if x not in pre]
        cmds.rename(mesh[0], id)

def write_qrc_contents():
    folder_dir = os.path.dirname(os.path.realpath(__file__))
    icons_dir = os.path.join(folder_dir, "icons")
    file_path = os.path.join(folder_dir, "icons", "icons.qrc")

    return_string = "<!DOCTYPE RCC><RCC version=\"1.0\">\n"
    return_string += "<qresource>\n"
    for part in get_nice_ui_parts():
        if os.path.exists(os.path.join(icons_dir, part+".png")):
            return_string += "    <file alias=\"{0}\">{0}.PNG</file>\n".format(part)
    return_string += "    <file alias=\"TOP_BAR_REFRESH\">TOP_BAR_REFRESH.PNG</file>\n".format(part)
    return_string += "</qresource>\n"
    return_string += "</RCC>\n"

    folder_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(folder_dir, "icons", "icons.qrc")
    with open(file_path, "w") as stream:
        stream.write(return_string)


def list_unused_icons():
    folder_dir = os.path.dirname(os.path.realpath(__file__))
    icons_dir = os.path.join(folder_dir, "icons")
    all_icons = os.listdir(icons_dir)
    all_parts = get_nice_ui_parts()
    all_parts_icon = [part + ".PNG" for part in all_parts]
    unused = [part for part in all_icons if part not in all_parts_icon]
    return unused

def remove_unused_icons():
    folder_dir = os.path.dirname(os.path.realpath(__file__))
    icons_dir = os.path.join(folder_dir, "icons")
    exclusions = ["icons.py", "icons.qrc", "TOP_BAR_REFRESH.png"]
    for icon in list_unused_icons():
        if icon in exclusions:
            continue
        try:
            os.remove("{}/{}".format(icons_dir, icon))
        except:
            pass


parts = list_missing_parts()
for part in parts:
    print ("- {}".format(part))