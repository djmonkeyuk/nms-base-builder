"""Browser UI state, kept on the WindowManager so it is not saved into .blend files."""

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from . import store
from .catalog_data import get_catalog
from .prefab_share import SORT_OPTIONS, get_feed

ALL_SUBCATEGORIES = "__ALL__"

MODES = (
    ("FAVOURITES", "Favourites", "Favourite parts and prefabs", "SOLO_ON", 0),
    ("RECENT", "Recent", "Recently placed parts and prefabs", "TIME", 1),
    ("PREFABS", "Prefabs", "Prefabs saved in your prefab folder", "PACKAGE", 2),
    ("SHARE", "#prefab-share", "Prefabs shared on the Discord #prefab-share channel", "URL", 3),
    ("CATEGORY", "Parts", "Browse parts by category", "MESH_CUBE", 4),
)

# Blender keeps pointers to the strings returned from dynamic enum callbacks,
# so the lists are cached here to keep them alive.
_enum_cache = {"categories": None, "categories_key": None, "subcategories": {}}

# Bumped whenever browser content changes, views compare it to know when to redraw.
_revision = [0]


def revision():
    return _revision[0] + get_feed().revision


def bump(context=None):
    _revision[0] += 1
    redraw(context)


def redraw(context=None):
    from .space import browser_areas

    context = context or bpy.context
    for _, area in browser_areas(getattr(context, "window_manager", None)):
        area.tag_redraw()


def ordered_categories():
    return store.ordered_categories(get_catalog().categories())


def _category_items(self, context):
    categories = ordered_categories()
    key = tuple(categories)
    if _enum_cache["categories_key"] != key:
        from . import thumbnails

        # Numbers follow the catalog order, not the user's order, so the stored
        # value still points at the same category after reordering.
        numbers = {name: index for index, name in enumerate(get_catalog().categories())}
        _enum_cache["categories"] = [
            (name, name, "", thumbnails.category_icon_id(name), numbers[name])
            for name in categories
        ]
        _enum_cache["categories_key"] = key
    return _enum_cache["categories"]


def _subcategory_items(self, context):
    category = self.category_name()
    items = _enum_cache["subcategories"].get(category)
    if items is None:
        items = [(ALL_SUBCATEGORIES, "All", "Show every sub category", 0)]
        for index, name in enumerate(get_catalog().subcategories(category), start=1):
            items.append((name, name, "", index))
        _enum_cache["subcategories"][category] = items
    return items


def _on_category(self, context):
    self.mode = "CATEGORY"
    self.scroll = 0
    if self.get("subcategory") is not None:
        self["subcategory"] = 0
    bump(context)


def _on_view_change(self, context):
    self.scroll = 0
    bump(context)


def _on_mode(self, context):
    self.scroll = 0
    if self.mode == "SHARE":
        get_feed().ensure_loaded()
    bump(context)


def _on_share_query(self, context):
    get_feed().refresh(sort=self.share_sort, search=self.share_search)


def _get_thumbnail_step(self):
    return store.thumbnail_step()


def _set_thumbnail_step(self, value):
    store.set_thumbnail_step(value)
    bump()


class NMSBrowserState(PropertyGroup):
    mode: EnumProperty(name="Mode", items=MODES, default="CATEGORY", update=_on_mode)
    category: EnumProperty(name="Category", items=_category_items, update=_on_category)
    subcategory: EnumProperty(
        name="Sub Category", items=_subcategory_items, update=_on_view_change
    )
    search: StringProperty(
        name="Search",
        description="Search parts and prefabs by name or id (3 or more characters)",
        options={"TEXTEDIT_UPDATE"},
        update=_on_view_change,
    )
    # Pop-out grid scroll offset in pixels.
    scroll: IntProperty(default=0, min=0)
    thumbnail_step: IntProperty(
        name="Thumbnail Size",
        description="Thumbnail size, the smallest setting shows a list",
        min=0,
        max=len(store.THUMBNAIL_SIZES),
        get=_get_thumbnail_step,
        set=_set_thumbnail_step,
    )
    share_sort: EnumProperty(name="Sort", items=SORT_OPTIONS, update=_on_share_query)
    share_search: StringProperty(
        name="Search Prefab Share",
        description="Search #prefab-share thread titles, press Enter to search",
        update=_on_share_query,
    )

    def category_name(self):
        categories = ordered_categories()
        if not categories:
            return ""
        try:
            value = self.category
        except (TypeError, ValueError):
            value = ""
        return value if value in categories else categories[0]

    def subcategory_name(self):
        try:
            value = self.subcategory
        except (TypeError, ValueError):
            return None
        if value == ALL_SUBCATEGORIES:
            return None
        return value if value in get_catalog().subcategories(self.category_name()) else None

    def set_category(self, category):
        """Show a whole category (sub category reset to All)."""
        if category in ordered_categories():
            self.category = category
            self.subcategory = ALL_SUBCATEGORIES
            self.mode = "CATEGORY"

    def searching(self):
        return len(self.search.strip()) >= 3


def _known_items(ids, prefab_ids):
    catalog = get_catalog()
    return [item_id for item_id in ids if catalog.get(item_id) or item_id in prefab_ids]


def sections(browser):
    """[(title, [item ids])] for what the browser should show.

    Ids are part ids or prefab ids. SHARE mode is drawn separately from the prefab-share feed.
    """
    from .catalog_data import list_prefabs, prefab_paths, search_prefabs

    catalog = get_catalog()
    if browser.searching():
        result = [("Parts", catalog.search(browser.search))]
        prefabs = search_prefabs(browser.search)
        if prefabs:
            result.append(("Prefabs", prefabs))
        return result
    mode = browser.mode
    if mode in {"FAVOURITES", "RECENT"}:
        prefab_ids = prefab_paths()
        ids = store.favourites() if mode == "FAVOURITES" else store.recents()
        return [(None, _known_items(ids, prefab_ids))]
    if mode == "PREFABS":
        return [(category, [prefab_id for prefab_id, _ in items]) for category, items in list_prefabs().items()]
    if mode == "CATEGORY":
        return catalog.sections(browser.category_name(), browser.subcategory_name())
    return []


def get_state(context=None):
    context = context or bpy.context
    return context.window_manager.nms_browser


def invalidate_enum_cache():
    _enum_cache["categories"] = None
    _enum_cache["categories_key"] = None
    _enum_cache["subcategories"].clear()


def register():
    bpy.utils.register_class(NMSBrowserState)
    bpy.types.WindowManager.nms_browser = bpy.props.PointerProperty(type=NMSBrowserState)


def unregister():
    del bpy.types.WindowManager.nms_browser
    bpy.utils.unregister_class(NMSBrowserState)
    invalidate_enum_cache()
