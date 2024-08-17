"""This Python script is used to automate the process of getting the part list up to date.

Requirements
    NMSDK
    Blender

How to use this file:
1. Unpack the latest No Mans Sky pak files (Using NMS Modding Station).
2. Convert BASEBUILDINGPARTSTABLE and NMS_REALITY_GCPRODUCTTABLE mbins to their exmls.
3. Run the following command to get two lists - one of known filepaths and one with unknown file paths to any missing parts in the plugin.

        known, unknown = list_missing_parts(
            "F:/Games/No Mans Sky/nms_modding_station/projects/BaseTables/METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML",
            "F:/Games/No Mans Sky/nms_modding_station/projects/BaseTables/METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML",
        )

4. For any unknown paths, find and place relavant mbin paths into the "DT_PartTable.csv" file. Unfortunately this is quite a manual process.
5. Keep running the above function until
 all paths fall in the "known" variable.
6. Using the known list, run the following function in Blender to automate the OBJ export.
7. With all OBJs exported, place them in their correct folder in the tool, and update the asset browser with the relevant info.

"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

BASEBUILDINGPARTSTABLE = "METADATA/REALITY/TABLES/BASEBUILDINGPARTSTABLE.EXML"
NMS_REALITY_GCPRODUCTTABLE = "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"

from automation_utils import (PATH_TO_MOD_PROJECT, bcolors,
                              get_unknown_category_parts,
                              get_unknown_subcategory_parts, ignore_items,
                              list_missing_parts, print_with_color)


def list_all_models_in_blender():
    dir = "G:/Apps/nms-base-builder/src/addons/no_mans_sky_base_builder/models"
    unreal_dir = "G:/Unreal Projects/NoMansSkyBaseBuilder/Content/NMSBaseBuilder/Features/Models"
    all_unreal = [uasset.replace(".uasset", "") for uasset in os.listdir(unreal_dir)]
    paths = os.listdir(dir)
    count = 0
    for path in paths:
        full_path = os.path.join(dir, path)
        part_files = os.listdir(full_path)
        for part_file in part_files:
            part_id = os.path.splitext(part_file)[0]
            if part_id not in all_unreal:
                print(part_id, "not found in unreal")
            count += 1
    return count

def print_report():
    BASEBUILDINGPARTSTABLE_path = os.path.join(PATH_TO_MOD_PROJECT, BASEBUILDINGPARTSTABLE)
    NMS_REALITY_GCPRODUCTTABLE_path = os.path.join(PATH_TO_MOD_PROJECT, NMS_REALITY_GCPRODUCTTABLE)
    known_parts, unknown_parts = list_missing_parts(
        BASEBUILDINGPARTSTABLE_path,
        NMS_REALITY_GCPRODUCTTABLE_path,
    )

    if not os.path.exists(BASEBUILDINGPARTSTABLE_path):
        raise RuntimeError(BASEBUILDINGPARTSTABLE_path + " does not exist")
    if not os.path.exists(NMS_REALITY_GCPRODUCTTABLE_path):
        raise RuntimeError(NMS_REALITY_GCPRODUCTTABLE_path + " does not exist")

    unknown_cats = get_unknown_category_parts() + get_unknown_subcategory_parts()
    all_parts = sorted(list(known_parts.keys())+list(unknown_parts.keys()))
    # Total
    print_with_color(
        "Total Missing Parts: {0}\n".format(len(known_parts) + len(unknown_parts)),
        bcolors.OKCYAN
    )

    # Ready
    if known_parts:
        print_with_color(
            "Parts Ready To Process: {0}".format(len(known_parts)),
            bcolors.OKGREEN
        )
        longest_known_part = max([len(x) for x in known_parts])
        print_with_color(
            "\n".join(["\t" + part.rjust(longest_known_part) + " : " + known_parts[part] for part in sorted(known_parts)]),
            bcolors.OKGREEN
        )

    # Not Ready
    if unknown_parts:
        print_with_color(
            "Parts NOT Ready To Process (please update the DT_PartTable): {0}".format(len(unknown_parts)),
            bcolors.FAIL
        )
        longest_unknown_part = max([len(x) for x in unknown_parts])
        print_with_color("\n".join([part for part in sorted(unknown_parts)]), bcolors.FAIL)
        #     "\n".join(["\t" + part.rjust(longest_unknown_part) + " : MISSING PATH" for part in sorted(unknown_parts)]),
        # )

    # Category.
    print_with_color(
        "\nThese parts do not have category information assigned. Giving categories will make the export process much nicer. (please update the DT_PartTable for the specific part):",
        bcolors.FAIL
    )

    for part in all_parts:
        if part in unknown_cats:
            print_with_color("\t"+part, bcolors.FAIL)

# Print Report.
print(print_report())
