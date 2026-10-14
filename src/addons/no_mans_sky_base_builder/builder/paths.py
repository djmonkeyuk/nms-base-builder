import os

ADDON_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")

MODEL_PATH = os.path.join(ADDON_PATH, "models")
FOSSIL_PARTS_PATH = os.path.join(MODEL_PATH, "fossil_parts")
NICE_JSON = os.path.join(ADDON_PATH, "resources", "nice_names.json")

MODS_PATH = os.path.join(USER_PATH, "mods")
PRESET_PATH = os.path.join(USER_PATH, "presets")
