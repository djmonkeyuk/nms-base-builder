import os
import zipfile
from os.path import basename
from zipfile import ZipFile

repo_dir = os.path.dirname(os.path.realpath(__file__))

python_package_dir = os.path.join(repo_dir, "src", "addons", "no_mans_sky_base_builder")


def build_recursive_file_list(dir_path):
    return_list = []
    for thing in os.listdir(dir_path):
        if thing == "__pycache__":
            continue

        full_path = os.path.join(dir_path, thing)
        if "icons" in full_path and full_path.endswith(".PNG"):
            continue
        if os.path.isfile(full_path):
            return_list.append(full_path)
        if os.path.isdir(full_path):
            return_list.extend(build_recursive_file_list(full_path))
    return return_list

def remove_root_path(in_path):
    last_bit = in_path.split("no_mans_sky_base_builder")[-1]
    path = "no_mans_sky_base_builder/" + last_bit
    return path

this_dir = os.path.dirname(os.path.realpath(__file__))
zip_out = os.path.join(this_dir, "no_mans_sky_base_builder.zip")
with ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zip_obj:
    # Add multiple files to the zip
    for item in build_recursive_file_list(python_package_dir):
        zip_obj.write(item, remove_root_path(item))

