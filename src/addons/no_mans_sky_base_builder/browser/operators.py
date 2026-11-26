"""Operators for the native asset browser."""

import webbrowser

import bpy
from bpy.props import IntProperty, StringProperty

from . import state, store, thumbnails
from .catalog_data import get_catalog
from .prefab_share import DISCORD_INVITE_URL, get_feed, thread_url


# Placement ---
def view3d_override(context=None):
    """temp_override kwargs targeting a 3D View, preferring the current one."""
    context = context or bpy.context
    area = getattr(context, "area", None)
    if area is not None and area.type == "VIEW_3D" and context.window is not None:
        region = next((region for region in area.regions if region.type == "WINDOW"), None)
        return {"window": context.window, "area": area, "region": region}
    window_manager = context.window_manager
    # Main windows first.
    windows = sorted(window_manager.windows, key=lambda window: window.parent is not None)
    for window in windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                region = next((region for region in area.regions if region.type == "WINDOW"), None)
                return {"window": window, "area": area, "region": region}
    return None


def is_prefab(item_id):
    from .catalog_data import prefab_paths

    return item_id in prefab_paths()


def place_item(item_id):
    """Place a part or prefab through the builder, as the legacy list does.

    Uses object.list_build_operator so prefabs, rigs and snapping to the
    current selection all behave the same as everywhere else.
    """
    override = view3d_override()
    try:
        if override is not None:
            with bpy.context.temp_override(**override):
                if bpy.context.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
                    bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.list_build_operator(part_id=item_id)
        else:
            bpy.ops.object.list_build_operator(part_id=item_id)
    except RuntimeError as error:
        print(f"NMS Base Builder: could not place {item_id}: {error}")
        return False
    from .catalog_data import clear_prefab_cache

    clear_prefab_cache()
    store.push_recent(item_id)
    state.bump()
    return True


def item_label(item_id):
    part = get_catalog().get(item_id)
    return part.name if part else item_id


# Operators ---
class NMS_OT_browser_place(bpy.types.Operator):
    """Place this item. With an item selected, the new item snaps to it"""

    bl_idname = "nms.browser_place"
    bl_label = "Place"
    bl_options = {"INTERNAL", "UNDO"}

    item_id: StringProperty()

    @classmethod
    def description(cls, context, properties):
        part = get_catalog().get(properties.item_id)
        if part is None:
            return "Place prefab {}".format(properties.item_id)
        return "{}\n{}  ({} / {})".format(part.name, part.id, part.category, part.subcategory)

    def execute(self, context):
        if not place_item(self.item_id):
            self.report({"WARNING"}, "Could not place {}".format(self.item_id))
            return {"CANCELLED"}
        return {"FINISHED"}


class NMS_OT_browser_edit_prefab(bpy.types.Operator):
    """Open this prefab on its own in a new file to edit it"""

    bl_idname = "nms.browser_edit_prefab"
    bl_label = "Edit Prefab"
    bl_options = {"INTERNAL"}

    item_id: StringProperty()

    def execute(self, context):
        override = view3d_override(context) or {}
        with context.temp_override(**override):
            bpy.ops.object.list_edit_operator("INVOKE_DEFAULT", part_id=self.item_id)
        return {"FINISHED"}


class NMS_OT_browser_favourite(bpy.types.Operator):
    """Add or remove this item from your favourites"""

    bl_idname = "nms.browser_favourite"
    bl_label = "Toggle Favourite"
    bl_options = {"INTERNAL"}

    item_id: StringProperty()

    def execute(self, context):
        store.toggle_favourite(self.item_id)
        state.bump(context)
        return {"FINISHED"}


class NMS_OT_browser_move_favourite(bpy.types.Operator):
    """Move this favourite earlier or later in the list"""

    bl_idname = "nms.browser_move_favourite"
    bl_label = "Move Favourite"
    bl_options = {"INTERNAL"}

    item_id: StringProperty()
    offset: IntProperty()

    def execute(self, context):
        store.move_favourite(self.item_id, self.offset)
        state.bump(context)
        return {"FINISHED"}


def _draw_tile(layout, item_id, scale=4.0):
    column = layout.column(align=True)
    icon_id = thumbnails.part_icon_id(item_id)
    if icon_id:
        column.template_icon(icon_value=icon_id, scale=scale)
    else:
        column.label(text="", icon="MESH_CUBE")
    column.operator(NMS_OT_browser_place.bl_idname, text=item_label(item_id)).item_id = item_id


class NMS_OT_browser_variants(bpy.types.Operator):
    """Show this part's variants"""

    bl_idname = "nms.browser_variants"
    bl_label = "Variants"
    bl_options = {"INTERNAL"}

    item_id: StringProperty()

    def invoke(self, context, event):
        count = 1 + len(self._variants())
        columns = min(4, count)
        return context.window_manager.invoke_popup(self, width=max(160, columns * 110))

    def _variants(self):
        part = get_catalog().get(self.item_id)
        return list(part.variants) if part else []

    def draw(self, context):
        layout = self.layout
        layout.label(text="{} variants".format(item_label(self.item_id)))
        ids = [self.item_id] + self._variants()
        grid = layout.grid_flow(row_major=True, columns=min(4, len(ids)), even_columns=True, align=True)
        for item_id in ids:
            _draw_tile(grid.box(), item_id, scale=4.0)

    def execute(self, context):
        return {"FINISHED"}


class NMS_OT_browser_item_menu(bpy.types.Operator):
    """Options for this item"""

    bl_idname = "nms.browser_item_menu"
    bl_label = "Item Options"
    bl_options = {"INTERNAL"}

    item_id: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=220)

    def draw(self, context):
        layout = self.layout
        item_id = self.item_id
        layout.label(text=item_label(item_id))
        column = layout.column(align=True)
        column.operator(NMS_OT_browser_place.bl_idname, text="Place", icon="ADD").item_id = item_id
        if is_prefab(item_id):
            column.operator(NMS_OT_browser_edit_prefab.bl_idname, text="Edit Prefab", icon="GREASEPENCIL").item_id = item_id
        favourite = store.is_favourite(item_id)
        column.operator(
            NMS_OT_browser_favourite.bl_idname,
            text="Remove from Favourites" if favourite else "Add to Favourites",
            icon="SOLO_ON" if favourite else "SOLO_OFF",
        ).item_id = item_id
        if favourite:
            row = column.row(align=True)
            op = row.operator(NMS_OT_browser_move_favourite.bl_idname, text="Move Earlier", icon="TRIA_LEFT")
            op.item_id, op.offset = item_id, -1
            op = row.operator(NMS_OT_browser_move_favourite.bl_idname, text="Move Later", icon="TRIA_RIGHT")
            op.item_id, op.offset = item_id, 1
        part = get_catalog().get(item_id)
        if part and part.variants:
            column.operator(NMS_OT_browser_variants.bl_idname, text="Variants...", icon="DOWNARROW_HLT").item_id = item_id

    def execute(self, context):
        return {"FINISHED"}


class NMS_OT_browser_category_menu(bpy.types.Operator):
    """Pin or reorder this category"""

    bl_idname = "nms.browser_category_menu"
    bl_label = "Category Options"
    bl_options = {"INTERNAL"}

    category: StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=200)

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.category)
        column = layout.column(align=True)
        pinned = self.category in store.pinned_categories()
        column.operator(
            NMS_OT_browser_pin_category.bl_idname,
            text="Unpin" if pinned else "Pin to Top",
            icon="PINNED" if pinned else "UNPINNED",
        ).category = self.category
        op = column.operator(NMS_OT_browser_move_category.bl_idname, text="Move Up", icon="TRIA_UP")
        op.category, op.offset = self.category, -1
        op = column.operator(NMS_OT_browser_move_category.bl_idname, text="Move Down", icon="TRIA_DOWN")
        op.category, op.offset = self.category, 1

    def execute(self, context):
        return {"FINISHED"}


class NMS_OT_browser_pin_category(bpy.types.Operator):
    """Pin this category to the top of the list"""

    bl_idname = "nms.browser_pin_category"
    bl_label = "Pin Category"
    bl_options = {"INTERNAL"}

    category: StringProperty()

    def execute(self, context):
        store.toggle_pinned_category(self.category)
        state.invalidate_enum_cache()
        state.bump(context)
        return {"FINISHED"}


class NMS_OT_browser_move_category(bpy.types.Operator):
    """Move this category up or down the list"""

    bl_idname = "nms.browser_move_category"
    bl_label = "Move Category"
    bl_options = {"INTERNAL"}

    category: StringProperty()
    offset: IntProperty()

    def execute(self, context):
        store.move_category(self.category, self.offset, get_catalog().categories())
        state.invalidate_enum_cache()
        state.bump(context)
        return {"FINISHED"}


# Prefab share ---
class NMS_OT_browser_share_attachment(bpy.types.Operator):
    """Choose which attachment to import"""

    bl_idname = "nms.browser_share_attachment"
    bl_label = "Choose Attachment"
    bl_options = {"INTERNAL"}

    index: IntProperty()

    def execute(self, context):
        feed = get_feed()
        record = feed.selected()
        if record and 0 <= self.index < len(record["attachments"]):
            record["attachment_index"] = self.index
            feed.touch()
        return {"FINISHED"}


class NMS_OT_browser_share_open(bpy.types.Operator):
    """Open the selected post in Discord, or the server invite"""

    bl_idname = "nms.browser_share_open"
    bl_label = "Open in Discord"
    bl_options = {"INTERNAL"}

    thread_id: StringProperty()

    def execute(self, context):
        webbrowser.open_new_tab(thread_url(self.thread_id) if self.thread_id else DISCORD_INVITE_URL)
        return {"FINISHED"}


# Window ---
class NMS_OT_browser_open_window(bpy.types.Operator):
    """Open the asset browser in its own window"""

    bl_idname = "nms.browser_open_window"
    bl_label = "Open Asset Browser Window"

    def execute(self, context):
        from . import gpu_grid

        window_manager = context.window_manager
        existing = gpu_grid.find_browser_window(context)
        if existing is not None:
            self.report({"INFO"}, "The asset browser window is already open")
            return {"FINISHED"}
        before = {window.as_pointer() for window in window_manager.windows}
        bpy.ops.wm.window_new()
        window = next(
            (window for window in window_manager.windows if window.as_pointer() not in before),
            None,
        )
        if window is None:
            self.report({"ERROR"}, "Could not open a new window")
            return {"CANCELLED"}
        from . import space

        space.prepare_area(window.screen.areas[0])
        return {"FINISHED"}


classes = (
    NMS_OT_browser_place,
    NMS_OT_browser_edit_prefab,
    NMS_OT_browser_favourite,
    NMS_OT_browser_move_favourite,
    NMS_OT_browser_variants,
    NMS_OT_browser_item_menu,
    NMS_OT_browser_category_menu,
    NMS_OT_browser_pin_category,
    NMS_OT_browser_move_category,
    NMS_OT_browser_share_attachment,
    NMS_OT_browser_share_open,
    NMS_OT_browser_open_window,
)
