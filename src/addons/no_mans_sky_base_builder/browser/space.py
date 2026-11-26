"""The editor the asset browser lives in.

The browser is a Node Editor showing a node tree type of its own. The tree is
never created, the editor just names the window and the editor type menu after
it ("No Man's Sky Asset Browser"), on every platform, and lets the browser be
docked into any area through the editor type menu.
"""

import bpy

TREE_IDNAME = "NMSAssetBrowserTree"
TITLE = "No Man's Sky Asset Browser"


class NMSAssetBrowserTree(bpy.types.NodeTree):
    """Browse and place No Man's Sky parts and prefabs"""

    bl_idname = TREE_IDNAME
    bl_label = TITLE
    bl_icon = "ASSET_MANAGER"


def is_browser_area(area):
    if area is None or area.type != "NODE_EDITOR":
        return False
    space = area.spaces.active
    return getattr(space, "tree_type", "") == TREE_IDNAME


def browser_areas(window_manager=None):
    """Yield (window, area) for every browser area."""
    window_manager = window_manager or getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if is_browser_area(area):
                yield window, area


def redraw():
    for _, area in browser_areas():
        area.tag_redraw()


# The node editor's toolbar (Select Box, Annotate, Links Cut...), sidebar and
# tool settings, none of which apply to the browser.
HIDDEN_REGIONS = ("show_region_toolbar", "show_region_ui", "show_region_tool_header")


def _shown_regions(space):
    return [name for name in HIDDEN_REGIONS if getattr(space, name, False)]


def hide_regions(area):
    space = area.spaces.active
    for name in _shown_regions(space):
        setattr(space, name, False)


def prepare_area(area):
    """Make an area a browser and hide the node editor's own regions."""
    area.ui_type = TREE_IDNAME
    hide_regions(area)


_pending_hide = set()


def hide_regions_later(area):
    """From a draw callback: hide shown regions once drawing is done.

    Covers browsers picked from the editor type menu, reopened from a file, or
    a toolbar toggled back on with T. Settings can't change while drawing, so a
    timer does it.
    """
    if not _shown_regions(area.spaces.active):
        return
    pointer = area.as_pointer()
    if pointer in _pending_hide:
        return
    _pending_hide.add(pointer)

    def run():
        _pending_hide.discard(pointer)
        for _, browser_area in browser_areas():
            if browser_area.as_pointer() == pointer:
                hide_regions(browser_area)
                browser_area.tag_redraw()
        return None

    bpy.app.timers.register(run, first_interval=0.0)


def register():
    bpy.utils.register_class(NMSAssetBrowserTree)


def unregister():
    bpy.utils.unregister_class(NMSAssetBrowserTree)
