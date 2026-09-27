"""Access to the builder shared by the whole addon.

Other addons can swap the builder, add part classes or supply their own
materials from their register():

    nms_builder.set_builder(MyBuilder())             # MyBuilder subclasses Builder
    nms_builder.register_override(MyPart, ["CUBEROOM"])
    nms_builder.set_material_provider(MyMaterials()) # MyMaterials subclasses MaterialProvider

and undo them from unregister() with set_builder(None), unregister_override()
and set_material_provider(None).
"""

from ..utils.material_provider import (MaterialProvider, get_material_provider,
                                       set_material_provider)
from .builder import Builder
from .overrides import register_override, unregister_override

__all__ = [
    "Builder",
    "get_builder",
    "set_builder",
    "register_override",
    "unregister_override",
    "MaterialProvider",
    "get_material_provider",
    "set_material_provider",
]

_default_builder = None
_active_builder = None


def get_builder():
    global _default_builder, _active_builder
    if _active_builder is None:
        if _default_builder is None:
            _default_builder = Builder()
        _active_builder = _default_builder
    return _active_builder


def set_builder(builder_object):
    # None restores the addon's own builder
    global _active_builder
    if builder_object is not None and not isinstance(builder_object, Builder):
        raise TypeError("set_builder expects a Builder instance or None")
    _active_builder = builder_object
