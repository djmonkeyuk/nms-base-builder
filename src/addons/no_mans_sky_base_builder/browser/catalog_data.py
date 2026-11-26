"""Part and prefab data for the native asset browser.

Pure Python (no bpy) so it can be tested outside Blender.
"""

import os
import time
from collections import OrderedDict

from . import parts_definition

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CATEGORY_ICONS_DIR = os.path.join(ADDON_DIR, "images", "icons")
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")
PREFAB_SHARE_PATH = os.path.join(USER_PATH, "prefab-share")

MIN_SEARCH_LENGTH = 3

# Icon file per part category, from images/icons.
CATEGORY_ICON_FILES = {
    "Advanced Technology": "buildtab_othertech copy.png",
    "Alloy Structures": "buildtab_fibreglass copy.png",
    "Builder Structures": "buildtab_builders copy.png",
    "Corvette": "buildtab_freighter copy.png",
    "Decoration": "buildtab_decoration copy.png",
    "Deployable Technology": "buildtab_deployable copy.png",
    "Exotic Decorations": "buildtab_exoticdecoration copy.png",
    "Fossils": "T_Icon_Bone.png",
    "Furnishings": "buildtab_furniture copy.png",
    "Large Structures": "buildtab_structures copy.png",
    "Legacy Structures": "buildtab_basic.png",
    "Power and Industry": "T_Icon_Bolt.png",
    "Settlement": "T_Icon_House.png",
    "Stone Structures": "buildtab_stone copy.png",
    "Timber Structures": "buildtab_timber copy.png",
    "Wall Art": "buildtab_wallart copy.png",
    "Space Station": "T_Icon_StationExt.png",
}


class Part:
    __slots__ = ("id", "name", "category", "subcategory", "variants", "variant_of", "show")

    def __init__(self, part_id, name, category, subcategory, variant_of, show):
        self.id = part_id
        self.name = name or part_id
        self.category = category
        self.subcategory = subcategory
        self.variant_of = variant_of
        self.show = show
        self.variants = []

    def __repr__(self):
        return f"Part({self.id!r})"


class Catalog:
    """Category tree, part lookup and search over DT_PartDefinition.csv."""

    def __init__(self):
        self.parts = {}
        # category -> subcategory -> [base part ids shown as tiles]
        self.tree = OrderedDict()
        self._search_index = []
        self._build()

    def _build(self):
        definition = parts_definition.get_part_definition()
        for category, sub_categories in definition.items():
            for subcategory, rows in sub_categories.items():
                for row in rows:
                    variant_of = row["variantOf"]
                    variant_of = variant_of[1:] if variant_of not in ("", "None") else None
                    self.parts[row["id"]] = Part(
                        row["id"],
                        row["nice_name"].title() if row["nice_name"].isupper() else row["nice_name"],
                        category,
                        subcategory,
                        variant_of,
                        row["showInDrawer"] == "True",
                    )

        for part in self.parts.values():
            if part.variant_of and part.variant_of in self.parts:
                self.parts[part.variant_of].variants.append(part.id)

        for category, sub_categories in definition.items():
            category_tree = OrderedDict()
            for subcategory, rows in sub_categories.items():
                ids = [row["id"] for row in rows if self.parts[row["id"]].show]
                if ids:
                    category_tree[subcategory] = ids
            if category_tree:
                self.tree[category] = category_tree

        self._search_index = [
            (part.id, part.id.lower(), part.name.lower())
            for part in self.parts.values()
            if part.show
        ]

    # Queries ---
    def categories(self, order=None):
        """Category names, with any names in ``order`` first."""
        names = list(self.tree)
        if not order:
            return names
        ordered = [name for name in order if name in self.tree]
        return ordered + [name for name in names if name not in ordered]

    def subcategories(self, category):
        return list(self.tree.get(category, ()))

    def parts_in(self, category, subcategory=None):
        """Base part ids in a category, or one of its subcategories."""
        category_tree = self.tree.get(category, {})
        if subcategory:
            return list(category_tree.get(subcategory, ()))
        ids = []
        for sub_ids in category_tree.values():
            ids.extend(sub_ids)
        return ids

    def sections(self, category, subcategory=None):
        """[(subcategory, [ids])] for drawing grouped grids."""
        category_tree = self.tree.get(category, {})
        if subcategory:
            return [(subcategory, list(category_tree.get(subcategory, ())))]
        return [(name, list(ids)) for name, ids in category_tree.items()]

    def get(self, part_id):
        return self.parts.get(part_id)

    def name(self, part_id):
        part = self.parts.get(part_id)
        return part.name if part else part_id

    def search(self, text, limit=None):
        """Ranked search: name prefix, id prefix, then substring matches."""
        query = text.strip().lower()
        if len(query) < MIN_SEARCH_LENGTH:
            return []
        name_prefix, id_prefix, contains = [], [], []
        for part_id, lower_id, lower_name in self._search_index:
            if lower_name.startswith(query):
                name_prefix.append(part_id)
            elif lower_id.startswith(query):
                id_prefix.append(part_id)
            elif query in lower_name or query in lower_id:
                contains.append(part_id)
        results = name_prefix + id_prefix + contains
        return results[:limit] if limit else results


_CATALOG = None


def get_catalog():
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = Catalog()
    return _CATALOG


def category_icon_path(category):
    file_name = CATEGORY_ICON_FILES.get(category)
    if not file_name:
        return None
    path = os.path.join(CATEGORY_ICONS_DIR, file_name)
    return path if os.path.isfile(path) else None


# Prefabs ---
PREFAB_CACHE_SECONDS = 2.0
_prefab_cache = {"time": 0.0, "presets": {}}


def prefab_paths():
    """{prefab_id: path}, cached briefly as panels redraw often."""
    from .. import preset

    now = time.monotonic()
    if now - _prefab_cache["time"] > PREFAB_CACHE_SECONDS:
        _prefab_cache["presets"] = preset.Preset.get_presets()
        _prefab_cache["time"] = now
    return _prefab_cache["presets"]


def clear_prefab_cache():
    _prefab_cache["time"] = 0.0


def list_prefabs():
    """{category: [(prefab_id, path)]} for the user's local prefab folders.

    Uses the same rules as preset.Preset.get_presets so ids line up with what
    the builder can place.
    """
    result = OrderedDict()
    for prefab_id, path in sorted(prefab_paths().items(), key=lambda item: item[0].lower()):
        parent = os.path.dirname(path)
        if os.path.normcase(parent) in (
            os.path.normcase(PRESET_PATH),
            os.path.normcase(PREFAB_SHARE_PATH),
        ):
            category = "Prefab Share" if os.path.normcase(parent) == os.path.normcase(PREFAB_SHARE_PATH) else "Uncategorised"
        else:
            category = os.path.basename(parent)
        result.setdefault(category, []).append((prefab_id, path))
    return result


def search_prefabs(text):
    query = text.strip().lower()
    if len(query) < MIN_SEARCH_LENGTH:
        return []
    matches = []
    for prefabs in list_prefabs().values():
        matches.extend(prefab_id for prefab_id, _ in prefabs if query in prefab_id.lower())
    return matches
