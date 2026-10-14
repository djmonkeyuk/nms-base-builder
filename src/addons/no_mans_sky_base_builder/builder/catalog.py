import os

from .. import preset
from ..utils import python as python_utils
from . import paths


class Catalog(object):
    """Lookup of the part models and presets available on disk."""

    nice_name_dictionary = python_utils.load_dictionary(paths.NICE_JSON)

    def __init__(self):
        # Create default part pack.
        self.available_packs = [("Parts", paths.MODEL_PATH)]

        # Find any mods with model packs inside.
        if os.path.exists(paths.MODS_PATH):
            for mod_folder in os.listdir(paths.MODS_PATH):
                full_mod_path = os.path.join(paths.MODS_PATH, mod_folder)
                if "models" in os.listdir(full_mod_path):
                    full_model_path = os.path.join(full_mod_path, "models")
                    self.available_packs.append((mod_folder, full_model_path))

        # Find Parts and build a reference dictionary.
        self.part_reference = {}
        for pack_name, pack_folder in self.available_packs:
            search_path = pack_folder or paths.MODEL_PATH
            for category in self.get_categories(pack=pack_name):
                for part_file in self.get_objs_from_category(category, pack=pack_name):
                    unique_id = os.path.splitext(part_file)[0]
                    self.part_reference[unique_id] = {
                        "category": category,
                        "full_path": os.path.join(search_path, category, part_file),
                        "pack": pack_name,
                    }

    # Parts ---
    def get_categories(self, pack=None):
        """Get the list of categories.

        Args:
            pack (str): The model pack search under for categories.
                Use this for mod support. Defaults to vanilla 'Parts'.
        Returns:
            list: List of folders underneath category path.
        """
        search_path = self.get_model_path_from_pack(pack or "Parts")
        return os.listdir(search_path)

    def get_objs_from_category(self, category, pack=None):
        """Get a list of parts belonging to a category.

        Args:
            category (str): The name of the category.
            pack (str): The model pack search under for categories.
                Use this for mod support. Defaults to vanilla 'Parts'.
        """
        search_path = self.get_model_path_from_pack(pack or "Parts")
        category_path = os.path.join(search_path, category)
        return sorted(
            part_file
            for part_file in os.listdir(category_path)
            if part_file.endswith(".fbx")
        )

    def get_parts_from_category(self, category, pack=None):
        """Get all the parts from a specific category.

        Args:
            category (str): The category to search.
            pack (str): The model pack name. Defaults to vanilla 'Parts'.
        """
        pack = pack or "Parts"
        return sorted(
            item
            for item, value in self.part_reference.items()
            if value["pack"] == pack and value["category"] == category
        )

    def get_obj_path(self, part):
        """Get the path to the OBJ file from a part."""
        return self.part_reference.get(part, {}).get("full_path", None)

    def get_obj_parent_folder(self, part):
        """Get the path to the OBJ file from a part."""
        path = self.get_obj_path(part)
        return os.path.dirname(path).split(os.sep)[-1]

    def get_model_path_from_pack(self, pack_request):
        """Given a pack name, return it's associated path.

        Args:
            pack_request (str): The name of the pack

        Return:
            str: The model path of the pack.
        """
        for pack_name, pack_path in self.available_packs:
            if pack_name == pack_request:
                return pack_path

    def get_nice_name(self, part):
        """Get a nice version of the part id."""
        part = os.path.basename(part)
        nice_name = part.title().replace("_", " ")
        return self.nice_name_dictionary.get(part, nice_name)

    # Presets ---
    def get_preset_categories(self):
        """Get the list of preset categories.

        Returns:
            list: List of folders underneath preset path.
        """
        return [
            item
            for item in os.listdir(preset.Preset.PRESET_PATH)
            if os.path.isdir(os.path.join(preset.Preset.PRESET_PATH, item))
        ]

    def get_uncategorized_presets(self):
        return self._list_presets(preset.Preset.PRESET_PATH)

    def get_presets_from_category(self, category):
        """Get a list of presets underneath a category.

        Args:
            category (str): The name of the category.
        """
        return self._list_presets(os.path.join(preset.Preset.PRESET_PATH, category))

    @staticmethod
    def _list_presets(folder):
        return [
            os.path.splitext(preset_file)[0]
            for preset_file in os.listdir(folder)
            if preset_file.endswith((".json", ".nmsprefab"))
        ]
