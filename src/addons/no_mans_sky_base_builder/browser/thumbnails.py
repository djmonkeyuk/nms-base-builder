"""Thumbnail loading for the native asset browser.

Part icons are loose PNGs in images/part_icons (extracted from the old Qt
resource module by tools/extract_qrc_icons.py). Previews are registered
lazily the first time an id is drawn, and GPU textures for the pop-out grid
are made from those previews and kept in a small LRU cache.
"""

import os
from array import array
from collections import OrderedDict

import bpy
import bpy.utils.previews

from .catalog_data import ADDON_DIR, category_icon_path

PART_ICONS_DIR = os.path.join(ADDON_DIR, "images", "part_icons")
GPU_CACHE_SIZE = 240

_collections = {}
_textures = OrderedDict()
_missing = set()


def _collection(name):
    pcoll = _collections.get(name)
    if pcoll is None:
        pcoll = bpy.utils.previews.new()
        _collections[name] = pcoll
    return pcoll


def _preview(collection, key, path):
    pcoll = _collection(collection)
    preview = pcoll.get(key)
    if preview is None:
        if not path or not os.path.isfile(path):
            return None
        try:
            preview = pcoll.load(key, path, "IMAGE")
        except (KeyError, RuntimeError):
            return pcoll.get(key)
    return preview


def part_icon_path(part_id):
    return os.path.join(PART_ICONS_DIR, part_id + ".png")


def part_preview(part_id):
    if part_id in _missing:
        return None
    preview = _preview("parts", part_id, part_icon_path(part_id))
    if preview is None:
        _missing.add(part_id)
    return preview


def part_icon_id(part_id):
    """icon_value for UILayout, 0 when the part has no icon."""
    preview = part_preview(part_id)
    return preview.icon_id if preview else 0


def category_icon_id(category):
    preview = _preview("categories", category, category_icon_path(category))
    return preview.icon_id if preview else 0


def image_preview(key, path):
    """Preview for an arbitrary image file (prefab-share thumbnails)."""
    return _preview("images", key, path)


def image_icon_id(key, path):
    preview = image_preview(key, path)
    return preview.icon_id if preview else 0


def reload_image(key):
    """Forget a cached image preview so a new file at the same key is picked up."""
    pcoll = _collections.get("images")
    if pcoll is not None and key in pcoll:
        del pcoll[key]
    texture_key = ("images", key)
    _textures.pop(texture_key, None)


# GPU textures ---
def _texture_from_preview(preview):
    import gpu

    width, height = preview.image_size
    if not width or not height:
        return None
    pixels = array("f", [0.0]) * (width * height * 4)
    preview.image_pixels_float.foreach_get(pixels)
    buffer = gpu.types.Buffer("FLOAT", len(pixels), pixels)
    return gpu.types.GPUTexture((width, height), format="RGBA32F", data=buffer)


def _cached_texture(texture_key, preview_getter):
    texture = _textures.get(texture_key)
    if texture is not None:
        _textures.move_to_end(texture_key)
        return texture
    preview = preview_getter()
    if preview is None:
        return None
    try:
        texture = _texture_from_preview(preview)
    except Exception as error:  # GPU unavailable or bad image.
        print(f"NMS Base Builder: could not make texture for {texture_key}: {error}")
        texture = None
    if texture is None:
        return None
    _textures[texture_key] = texture
    while len(_textures) > GPU_CACHE_SIZE:
        _textures.popitem(last=False)
    return texture


def part_texture(part_id):
    return _cached_texture(("parts", part_id), lambda: part_preview(part_id))


def image_texture(key, path):
    return _cached_texture(("images", key), lambda: image_preview(key, path))


def clear():
    _textures.clear()
    _missing.clear()
    for pcoll in _collections.values():
        bpy.utils.previews.remove(pcoll)
    _collections.clear()
