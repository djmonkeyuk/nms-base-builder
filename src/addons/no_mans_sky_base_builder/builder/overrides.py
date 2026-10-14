import os

from ..part import Part
from ..part_overrides import (bone, bone_replacer, locked, message,
                              power_control, turret, u_bytebeatline, u_pipeline,
                              u_portalline, u_powerline)
from . import paths

# parts that need their own class to be built, checked in order
OVERRIDE_CLASSES = {
    bone_replacer.BONE_REPLACER: [
        "FOS_HEAD",
        "FOS_SKULL",
        "FOS_LIMBS",
        "FOS_TAIL",
        "FOS_BODY",
    ],
    bone.BONE: [
        os.path.splitext(filename)[0]
        for filename in os.listdir(paths.FOSSIL_PARTS_PATH)
    ],
    turret.TURRET: ["B_TUR_A", "B_TUR_B", "B_TUR_C", "B_TUR_D", "B_TUR_E"],
    u_powerline.U_POWERLINE: ["U_POWERLINE"],
    u_pipeline.U_PIPELINE: ["U_PIPELINE"],
    u_portalline.U_PORTALLINE: ["U_PORTALLINE"],
    u_bytebeatline.U_BYTEBEATLINE: ["U_BYTEBEATLINE"],
    power_control.POWER_CONTROL: ["POWER_CONTROL"],
    locked.LOCKED: [
        "BASE_FLAG",
        "BRIDGECONNECTOR",
        "AIRLCKCONNECTOR",
        "FREIGHTER_CORE",
    ],
    message.MESSAGE: [
        "MESSAGEMODULE",
        "BYTEBEAT",
        "BYTEBEATSWITCH",
        "HOLO_DISCO_0",
        "FOS_BI",
        "FOS_BIRD",
        "FOS_BIRD_DIS",
        "FOS_BI_DIS",
        "FOS_BODY",
        "FOS_BODY_DISP",
        "FOS_BODY_MNT",
        "FOS_GRUN",
        "FOS_GRUN_DIS",
        "FOS_LIMBS",
        "FOS_LIMBS_DISP",
        "FOS_LIMBS_MNT",
        "FOS_QUAD",
        "FOS_QUAD_DIS",
        "FOS_SKULL",
        "FOS_SKULL_DISP",
        "FOS_SKULL_MNT",
        "FOS_TAIL",
        "FOS_TAIL_DISP",
        "FOS_TAIL_MNT",
        "FOS_WORM",
        "FOS_WORM_DIS",
    ],
}

# flattened {object_id: class}, the first class listing an id wins
_CLASS_BY_ID = {}
for _class_ref, _part_list in OVERRIDE_CLASSES.items():
    for _object_id in _part_list:
        _CLASS_BY_ID.setdefault(_object_id, _class_ref)


# classes added by other addons, these win over the built in table
_REGISTERED_BY_ID = {}


def register_override(class_ref, object_ids):
    for object_id in object_ids:
        _REGISTERED_BY_ID[object_id.replace("^", "")] = class_ref


def unregister_override(object_ids):
    for object_id in object_ids:
        _REGISTERED_BY_ID.pop(object_id.replace("^", ""), None)


def get_override_class(object_id):
    return _REGISTERED_BY_ID.get(object_id) or _CLASS_BY_ID.get(object_id)


def get_part_class(object_id):
    return get_override_class(object_id) or Part
