"""Native Blender asset browser.

- Pop-out window with a gpu-drawn grid (gpu_grid.py)
- Discord #prefab-share feed (prefab_share.py)
"""

import bpy

from . import gpu_grid, operators, prefab_share, space, state, thumbnails


def register():
    space.register()
    state.register()
    for cls in operators.classes:
        bpy.utils.register_class(cls)
    gpu_grid.register()


def unregister():
    gpu_grid.unregister()
    for cls in reversed(operators.classes):
        bpy.utils.unregister_class(cls)
    state.unregister()
    space.unregister()
    prefab_share.shutdown()
    thumbnails.clear()
