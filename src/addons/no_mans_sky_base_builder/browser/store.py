"""Browser settings: favourites, recents, category order and sizes.

Kept in the settings.json the earlier Qt browser used, so favourites, pinned
tabs and thumbnail size carry over. Writes are atomic and reads are cached on
the file's modification time.
"""

import json
import os
import sys
import tempfile
from pathlib import Path


APP_TITLE = "No Mans Sky Base Builder Blender"


def _user_data_folder(app_name):
    """Per-user app data folder. The folder name predates this browser, so
    favourites and settings saved by older versions are still found."""
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / app_name


FOLDER_PATH = str(_user_data_folder(APP_TITLE))
FILE_PATH = os.path.join(FOLDER_PATH, "settings.json")
MAX_RECENTS = 20

_cache = {"mtime": None, "data": {}}


def _defaults():
    return {
        "favourites": [],
        "pinned_tabs": [],
        "thumbnail_size_step": None,
        "recents": [],
        "category_order": [],
    }


def load():
    try:
        mtime = os.path.getmtime(FILE_PATH)
    except OSError:
        _cache["mtime"] = None
        _cache["data"] = _defaults()
        return _cache["data"]
    if mtime != _cache["mtime"]:
        data = _defaults()
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as stream:
                loaded = json.load(stream)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, ValueError) as error:
            print(f"NMS Base Builder: could not read {FILE_PATH}: {error}")
        _cache["mtime"] = mtime
        _cache["data"] = data
    return _cache["data"]


def save(data):
    os.makedirs(FOLDER_PATH, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=FOLDER_PATH, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4)
        os.replace(temp_path, FILE_PATH)
    except OSError as error:
        print(f"NMS Base Builder: could not save {FILE_PATH}: {error}")
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return
    _cache["mtime"] = os.path.getmtime(FILE_PATH)
    _cache["data"] = data


def _update(key, value):
    data = dict(load())
    data[key] = value
    save(data)


# Favourites ---
def favourites():
    return list(load().get("favourites") or [])


def is_favourite(item_id):
    return item_id in (load().get("favourites") or [])


def toggle_favourite(item_id):
    items = favourites()
    if item_id in items:
        items.remove(item_id)
    else:
        items.append(item_id)
    _update("favourites", items)
    return item_id in items


def move_favourite(item_id, offset):
    """Move a favourite by offset places, clamped to the list."""
    items = favourites()
    if item_id not in items:
        return
    index = items.index(item_id)
    new_index = max(0, min(len(items) - 1, index + offset))
    items.insert(new_index, items.pop(index))
    _update("favourites", items)


# Recents ---
def recents():
    return list(load().get("recents") or [])


def push_recent(item_id):
    items = [item for item in recents() if item != item_id]
    items.insert(0, item_id)
    _update("recents", items[:MAX_RECENTS])


def clear_recents():
    _update("recents", [])


# Category order and pins ---
def category_order():
    return list(load().get("category_order") or [])


def set_category_order(order):
    _update("category_order", list(order))


def pinned_categories():
    return list(load().get("pinned_tabs") or [])


def toggle_pinned_category(category):
    items = pinned_categories()
    if category in items:
        items.remove(category)
    else:
        items.append(category)
    _update("pinned_tabs", items)


def ordered_categories(all_categories):
    """Pinned categories first, then the saved order, then the rest."""
    pinned = [name for name in pinned_categories() if name in all_categories]
    order = [name for name in category_order() if name in all_categories and name not in pinned]
    rest = [name for name in all_categories if name not in pinned and name not in order]
    return pinned + order + rest


def move_category(category, offset, all_categories):
    order = [name for name in ordered_categories(all_categories)]
    if category not in order:
        return
    index = order.index(category)
    new_index = max(0, min(len(order) - 1, index + offset))
    order.insert(new_index, order.pop(index))
    set_category_order(order)


# Thumbnail size ---
THUMBNAIL_SIZES = (32, 48, 64, 80, 100, 128)
DEFAULT_THUMBNAIL_STEP = 3


def thumbnail_step():
    step = load().get("thumbnail_size_step")
    if not isinstance(step, int):
        return DEFAULT_THUMBNAIL_STEP
    return max(0, min(len(THUMBNAIL_SIZES), step))


def set_thumbnail_step(step):
    step = max(0, min(len(THUMBNAIL_SIZES), int(step)))
    if step != load().get("thumbnail_size_step"):
        _update("thumbnail_size_step", step)


def thumbnail_size(step=None):
    """Pixel size for a step. Step 0 is the Qt list view, drawn at the smallest size."""
    step = thumbnail_step() if step is None else step
    return THUMBNAIL_SIZES[max(0, step - 1)]


# Prefab Share detail panel width, in unscaled pixels.
SHARE_PANEL_WIDTH = (160, 240, 600)


def share_panel_width():
    low, default, high = SHARE_PANEL_WIDTH
    width = load().get("share_panel_width")
    if not isinstance(width, (int, float)):
        return default
    return max(low, min(high, int(width)))


def set_share_panel_width(width):
    low, _, high = SHARE_PANEL_WIDTH
    width = max(low, min(high, int(width)))
    if width != load().get("share_panel_width"):
        _update("share_panel_width", width)
