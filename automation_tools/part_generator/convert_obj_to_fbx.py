
import os

import bpy.ops

root_model_path = "G:/Apps/nms-base-builder/src/addons/no_mans_sky_base_builder/models"
fbx_model_path = "G:/Apps/nms-base-builder/src/addons/no_mans_sky_base_builder/models/fbx"
category_paths = [os.path.join(root_model_path, x) for x in os.listdir(root_model_path)]

count = 0
for category in category_paths:
    models = [os.path.join(category, model) for model in os.listdir(category) if model.endswith(".obj")]
    for obj_model in models:
        fbx_path = obj_model.replace(".obj", ".fbx")
        fbx_path = fbx_path.replace(root_model_path, fbx_model_path)

        fbx_dir = os.path.dirname(fbx_path)
        if not os.path.exists(fbx_dir):
            os.mkdir(fbx_dir)

        # Blender operation
        bpy.ops.import_scene.obj(filepath=obj_model, split_mode="OFF")
        bpy.ops.export_scene.fbx(filepath=fbx_path, object_types={'MESH'}, use_selection=True)

        count += 1