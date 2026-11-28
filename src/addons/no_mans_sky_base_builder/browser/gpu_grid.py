"""Pop-out asset browser window: a scrollable, clickable tile grid drawn with gpu/blf.

The browser is a Node Editor showing the add-on's own node tree type (space.py),
opened in a new window with wm.window_new or picked from the editor type menu.
Its main region is painted over by a SpaceNodeEditor draw handler, its header
is replaced, and input comes from keymap items on the Node Editor keymap whose
operator only polls true inside a browser area. No long-running modal operator
is used, so Blender's autosave keeps working while the window is open.
"""

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

from . import operators as ops
from . import space, state, store, thumbnails
from .catalog_data import get_catalog
from .prefab_share import get_feed, online_access

FONT_ID = 0
# Added to every font size, in pixels.
FONT_BUMP = 1

# Colour themes (sRGB, drawn as-is) ---
def _hex(value, alpha=1.0):
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)) + (alpha,)


_DISCORD = _hex("#5865F2")
_DISCORD_TEXT = (0.64, 0.68, 1.0, 1.0)
# Tab colours from the Qt browser, kept in both themes.
_FAVOURITES_TEXT = _hex("#D8D02E")
_PREFABS_TEXT = _hex("#FF69B4")

THEMES = {
    # The colours of the original Qt asset browser. Its translucent
    # overlays are pre-blended over the colour beneath them.
    "NMS": {
        "BACKGROUND": _hex("#232f40"),
        "SIDEBAR": _hex("#1a232f"),
        "SIDEBAR_ROW": _hex("#10151d"),  # rgba(0, 0, 0, 100) over the sidebar
        "SIDEBAR_HOVER": _hex("#303943"),  # rgba(255, 255, 255, 25) over the sidebar
        "SIDEBAR_BORDER": _hex("#0a1018"),
        "SIDEBAR_SEPARATOR": _hex("#D8D02E"),
        "ACTIVE": _hex("#4a5a75"),
        "ACTIVE_TEXT": _hex("#FFFFFF"),
        "ACTIVE_BAR": None,
        "CURRENT_TEXT": _hex("#D8D02E"),
        "ACCENT": _hex("#D8D02E"),
        "TILE": _hex("#1a232f"),
        "TILE_HOVER": _hex("#1e2835"),
        "TILE_TEXT": _hex("#FFFFFF"),
        "TILE_PRESSED": _hex("#000000"),
        "SIDEBAR_PRESSED": _hex("#000000"),
        "BADGE_PRESSED": _hex("#000000"),
        "BUTTON_PRESSED": _hex("#000000"),
        "DISCORD_PRESSED": _hex("#3C45A5"),
        "CARD_PRESSED": _hex("#090d12"),
        "CARD_PRESSED_BORDER": _hex("#eec920"),
        "OUTLINE": _hex("#DDDDDD"),
        "TEXT": _hex("#FFFFFF"),
        "TEXT_DIM": _hex("#b0cada"),
        "HEADER": _hex("#D8D02E"),
        "HEADER_BG": _hex("#151c26"),  # rgba(0, 0, 0, 0.4) over the background
        "HEADER_LINE": _hex("#D8D02E"),
        "HEADER_UPPER": True,
        "FAVOURITE": _hex("#D8D02E"),
        "BADGE": _hex("#141b24"),
        "BADGE_BORDER": _hex("#525456"),
        "BADGE_HOVER": _hex("#1e2835"),
        "BADGE_HOVER_BORDER": _hex("#DDDDDD"),
        "BADGE_TEXT": _hex("#FFFFFF"),
        "BUTTON": _hex("#0a1b2e"),
        "BUTTON_HOVER": _hex("#1e2835"),
        "BUTTON_TEXT": _hex("#D8D02E"),
        "BUTTON_BORDER": _hex("#060e18"),
        "BUTTON_HOVER_BORDER": _hex("#D8D02E"),
        "CARD": _hex("#17202c"),
        "CARD_BORDER": _hex("#0a1018"),
        "CARD_HOVER": _hex("#1e2835"),
        "CARD_HOVER_BORDER": _hex("#D8D02E"),
        "CARD_SELECTED": _hex("#090d12"),
        "CARD_SELECTED_BORDER": _hex("#eec920"),
        "PANEL": _hex("#17202c"),
        "PANEL_BORDER": _hex("#0a1018"),
        "PLACEHOLDER": _hex("#0a1b2e"),
        "SCROLL": _hex("#4a5a75"),
        "SCROLL_TRACK": _hex("#1a232f"),
        "DISCORD": _DISCORD,
        "DISCORD_HOVER": _hex("#4752C4"),
        "DISCORD_BORDER": _hex("#4752C4"),
        "DISCORD_TEXT": _DISCORD_TEXT,
        "FAVOURITES_TEXT": _FAVOURITES_TEXT,
        "PREFABS_TEXT": _PREFABS_TEXT,
    },
    # Neutral greys that sit with Blender's default theme.
    "BLENDER": {
        "BACKGROUND": (0.11, 0.11, 0.12, 1.0),
        "SIDEBAR": (0.15, 0.15, 0.16, 1.0),
        "SIDEBAR_ROW": None,
        "SIDEBAR_HOVER": (0.26, 0.26, 0.28, 1.0),
        "SIDEBAR_BORDER": None,
        "SIDEBAR_SEPARATOR": (0.6, 0.6, 0.62, 1.0),
        "ACTIVE": (0.28, 0.42, 0.65, 1.0),
        "ACTIVE_TEXT": (0.9, 0.9, 0.9, 1.0),
        "ACTIVE_BAR": (0.45, 0.62, 0.9, 1.0),
        "CURRENT_TEXT": (0.55, 0.72, 1.0, 1.0),
        "ACCENT": (0.28, 0.42, 0.65, 1.0),
        "TILE": (0.18, 0.18, 0.19, 1.0),
        "TILE_HOVER": (0.26, 0.26, 0.28, 1.0),
        "TILE_TEXT": (0.6, 0.6, 0.62, 1.0),
        "TILE_PRESSED": (0.12, 0.12, 0.13, 1.0),
        "SIDEBAR_PRESSED": (0.2, 0.3, 0.48, 1.0),
        "BADGE_PRESSED": (0.05, 0.05, 0.05, 1.0),
        "BUTTON_PRESSED": (0.18, 0.18, 0.2, 1.0),
        "DISCORD_PRESSED": _hex("#3C45A5"),
        "CARD_PRESSED": (0.12, 0.12, 0.13, 1.0),
        "CARD_PRESSED_BORDER": None,
        "OUTLINE": None,
        "TEXT": (0.9, 0.9, 0.9, 1.0),
        "TEXT_DIM": (0.6, 0.6, 0.62, 1.0),
        "HEADER": (0.9, 0.9, 0.9, 1.0),
        "HEADER_BG": None,
        "HEADER_LINE": (0.6, 0.6, 0.62, 1.0),
        "HEADER_UPPER": False,
        "FAVOURITE": (0.85, 0.82, 0.18, 1.0),
        "BADGE": (0.1, 0.1, 0.1, 0.85),
        "BADGE_BORDER": None,
        "BADGE_HOVER": (0.28, 0.42, 0.65, 1.0),
        "BADGE_HOVER_BORDER": None,
        "BADGE_TEXT": (0.9, 0.9, 0.9, 1.0),
        "BUTTON": (0.25, 0.25, 0.27, 1.0),
        "BUTTON_HOVER": (0.34, 0.34, 0.37, 1.0),
        "BUTTON_TEXT": (0.9, 0.9, 0.9, 1.0),
        "BUTTON_BORDER": None,
        "BUTTON_HOVER_BORDER": None,
        "CARD": (0.18, 0.18, 0.19, 1.0),
        "CARD_BORDER": None,
        "CARD_HOVER": (0.26, 0.26, 0.28, 1.0),
        "CARD_HOVER_BORDER": None,
        "CARD_SELECTED": (0.28, 0.42, 0.65, 1.0),
        "CARD_SELECTED_BORDER": None,
        "PANEL": (0.15, 0.15, 0.16, 1.0),
        "PANEL_BORDER": (0.3, 0.3, 0.32, 1.0),
        "PLACEHOLDER": (0.25, 0.25, 0.27, 1.0),
        "SCROLL": (0.35, 0.35, 0.38, 1.0),
        "SCROLL_TRACK": (0.15, 0.15, 0.16, 1.0),
        "DISCORD": _DISCORD,
        "DISCORD_HOVER": _hex("#4752C4"),
        "DISCORD_BORDER": None,
        "DISCORD_TEXT": _DISCORD_TEXT,
        "FAVOURITES_TEXT": _FAVOURITES_TEXT,
        "PREFABS_TEXT": _PREFABS_TEXT,
    },
}


class _Theme:
    """Colours of the active theme, as attributes (T.TILE, T.ACCENT...)."""

    def use(self, name):
        self.__dict__.update(THEMES.get(name, THEMES["NMS"]))


T = _Theme()
T.use("NMS")


def theme_name():
    from ..addon_preferences import get_addon_preferences

    prefs = get_addon_preferences()
    return getattr(prefs, "browser_theme", "NMS") if prefs else "NMS"


SHARE_INTRO = (
    "Prefabs here are shared by the community over on Discord. "
    "Join the server to browse the full collection, chat with "
    "other builders, and upload your own creations."
)

_views = {}
_draw_handle = None
_keymaps = []
_wrap_cache = {}


# Drawing helpers ---
def _shader(name):
    return gpu.shader.from_builtin(name)


def draw_rect(x, y, width, height, color):
    shader = _shader("UNIFORM_COLOR")
    batch = batch_for_shader(
        shader,
        "TRIS",
        {"pos": ((x, y), (x + width, y), (x + width, y + height), (x, y + height))},
        indices=((0, 1, 2), (0, 2, 3)),
    )
    # blf resets blending after drawing text, so set it for every draw.
    gpu.state.blend_set("ALPHA")
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def fill_rect(x, y, width, height, color):
    """draw_rect that draws nothing for a None colour (a theme without that element)."""
    if color is not None:
        draw_rect(x, y, width, height, color)


def draw_outline(x, y, width, height, color, thickness=1):
    if color is None:
        return
    draw_rect(x, y, width, thickness, color)
    draw_rect(x, y + height - thickness, width, thickness, color)
    draw_rect(x, y, thickness, height, color)
    draw_rect(x + width - thickness, y, thickness, height, color)


def draw_triangle(x, center_y, size, pointing_down, color):
    """Small disclosure triangle, pointing right or down."""
    half = size / 2
    if pointing_down:
        points = ((x, center_y + half * 0.6), (x + size, center_y + half * 0.6), (x + half, center_y - half * 0.6))
    else:
        points = ((x + size * 0.2, center_y + half), (x + size * 0.2, center_y - half), (x + size * 0.9, center_y))
    shader = _shader("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "TRIS", {"pos": points})
    gpu.state.blend_set("ALPHA")
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_texture(texture, x, y, width, height, fill=False):
    """Draw a texture in the box, keeping its aspect ratio.

    By default the whole image fits inside the box. With fill, the image
    covers the box and the overflow is cropped.
    """
    aspect = texture.width / max(1, texture.height)
    box_aspect = width / max(1, height)
    u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
    if fill:
        if aspect > box_aspect:
            crop = (1.0 - box_aspect / aspect) / 2
            u0, u1 = crop, 1.0 - crop
        else:
            crop = (1.0 - aspect / box_aspect) / 2
            v0, v1 = crop, 1.0 - crop
        draw_width, draw_height = width, height
    elif box_aspect > aspect:
        draw_width, draw_height = height * aspect, height
    else:
        draw_width, draw_height = width, width / aspect
    x += (width - draw_width) / 2
    y += (height - draw_height) / 2
    shader = _shader("IMAGE")
    batch = batch_for_shader(
        shader,
        "TRIS",
        {
            "pos": ((x, y), (x + draw_width, y), (x + draw_width, y + draw_height), (x, y + draw_height)),
            "texCoord": ((u0, v0), (u1, v0), (u1, v1), (u0, v1)),
        },
        indices=((0, 1, 2), (0, 2, 3)),
    )
    gpu.state.blend_set("ALPHA")
    shader.bind()
    shader.uniform_sampler("image", texture)
    batch.draw(shader)


def draw_text(text, x, y, size, color=None):
    blf.size(FONT_ID, size + FONT_BUMP)
    blf.color(FONT_ID, *(color or T.TEXT))
    blf.position(FONT_ID, x, y, 0)
    blf.draw(FONT_ID, text)


def text_width(text, size):
    blf.size(FONT_ID, size + FONT_BUMP)
    return blf.dimensions(FONT_ID, text)[0]


def fit_text(text, width, size):
    """Truncate text with an ellipsis to fit width."""
    key = ("fit", text, int(width), size)
    cached = _wrap_cache.get(key)
    if cached is not None:
        return cached
    result = text
    if text_width(text, size) > width:
        while result and text_width(result + "…", size) > width:
            result = result[:-1]
        result = result.rstrip() + "…"
    _wrap_cache[key] = result
    return result


def wrap_text(text, width, size, max_lines):
    key = ("wrap", text, int(width), size, max_lines)
    cached = _wrap_cache.get(key)
    if cached is not None:
        return cached
    lines = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split(" "):
            candidate = (line + " " + word).strip()
            if line and text_width(candidate, size) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit_text(lines[-1] + "…", width, size)
    lines = [fit_text(line, width, size) for line in lines]
    if len(_wrap_cache) > 5000:
        _wrap_cache.clear()
    _wrap_cache[key] = lines
    return lines


# View ---
class BrowserView:
    """Per-window layout, scroll and hover state."""

    def __init__(self, area):
        self.area_pointer = area.as_pointer()
        self.scroll = 0.0
        self.sidebar_scroll = 0.0
        self.content_height = 0.0
        self.sidebar_height = 0.0
        self.view_height = 0.0
        self.hover = None
        # The click target under a held left button, acted on at release.
        self.pressed = None
        self.mouse = (-1, -1)
        self.hits = []
        self.scrollbar = None
        self.content_key = None
        self.expanded = set()
        # Grid section headers the user has folded away, keyed by
        # (mode, category, title) so a "Walls" folded in one category stays
        # open in another. Session only, like the sidebar tree.
        self.collapsed = set()
        self.tree_ready = False
        # Prefab Share detail panel width (unscaled), None until read from the store.
        self.share_panel_width = None

    # Hit testing ---
    def add_hit(self, x, y, width, height, action):
        self.hits.append((x, y, x + width, y + height, action))

    def hit(self, x, y):
        for x0, y0, x1, y1, action in reversed(self.hits):
            if x0 <= x < x1 and y0 <= y < y1:
                return action
        return None

    def hovered(self, x, y, width, height):
        mx, my = self.mouse
        return x <= mx < x + width and y <= my < y + height

    def is_pressed(self, action):
        """The button is held on this target and the mouse is still over it."""
        return self.pressed is not None and self.pressed == action and self.hover == action

    # Drawing ---
    def draw(self, context):
        region = context.region
        ui = context.preferences.system.ui_scale
        browser = state.get_state(context)
        self.hits = []
        self.scrollbar = None
        T.use(theme_name())

        key = (browser.mode, browser.category_name(), browser.subcategory_name(), browser.search.strip())
        if key != self.content_key:
            self.content_key = key
            self.scroll = 0.0

        gpu.state.blend_set("ALPHA")
        draw_rect(0, 0, region.width, region.height, T.BACKGROUND)
        sidebar_width = int(190 * ui)
        sidebar_margin = int(6 * ui)
        self.draw_sidebar(region, ui, browser, sidebar_width, sidebar_margin)

        x0 = sidebar_margin + sidebar_width + 10 * ui
        x1 = region.width - 16 * ui
        if browser.mode == "SHARE" and not browser.searching():
            self.draw_share(region, ui, x0, x1)
        else:
            self.draw_items(region, ui, browser, x0, x1)
        gpu.state.blend_set("NONE")

    def draw_sidebar(self, region, ui, browser, width, margin=0):
        """Modes, then a category tree. Expanded categories list their sub categories.

        The sidebar is a panel inset by margin from the region's left, top and
        bottom edges, with its rows clipped to the panel.
        """
        panel_bottom = margin
        panel_top = region.height - margin
        panel_height = max(0, panel_top - panel_bottom)
        draw_rect(margin, panel_bottom, width, panel_height, T.SIDEBAR)
        searching = browser.searching()
        active_category = browser.category_name()
        active_sub = browser.subcategory_name()
        in_categories = not searching and browser.mode == "CATEGORY"
        if not self.tree_ready:
            # Start with the current category open.
            self.expanded.add(active_category)
            self.tree_ready = True

        row_height = 32 * ui
        category_height = 30 * ui
        sub_height = 20 * ui
        entries = [
            ("mode", "FAVOURITES", "Favourites", "★"),
            ("mode", "RECENT", "Recent", "◷"),
            ("mode", "PREFABS", "Prefabs", "▣"),
            ("mode", "SHARE", "prefab-share", "#"),
            None,
        ]
        catalog = get_catalog()
        for category in state.ordered_categories():
            entries.append(("category", category, category, None))
            if category in self.expanded:
                for sub in catalog.subcategories(category):
                    entries.append(("sub", (category, sub), sub, None))

        heights = [
            8 * ui
            if entry is None
            else sub_height
            if entry[0] == "sub"
            else category_height
            if entry[0] == "category"
            else row_height
            for entry in entries
        ]
        self.sidebar_height = sum(heights) + 24 * ui
        max_scroll = max(0.0, self.sidebar_height - panel_height)
        self.sidebar_scroll = min(max(0.0, self.sidebar_scroll), max_scroll)
        y = panel_top - 8 * ui + self.sidebar_scroll
        pinned = set(store.pinned_categories())
        x = margin

        # Clip rows to the panel so scrolled rows don't spill into the margin.
        # The scissor is in window coordinates; the region's own scissor gives its origin.
        region_scissor = gpu.state.scissor_get()
        gpu.state.scissor_set(
            region_scissor[0] + margin, region_scissor[1] + panel_bottom, width, panel_height
        )
        row_width = width - 1
        font_size = int(11 * ui)

        for entry, height in zip(entries, heights):
            y -= height
            if entry is None:
                # Divider between the modes and the part categories.
                fill_rect(x, y + height - 1, row_width, 1, T.SIDEBAR_SEPARATOR)
                continue
            if y > panel_top or y + height < panel_bottom:
                continue
            kind, value, label, glyph = entry
            discord = value == "SHARE"
            if kind == "mode":
                active = not searching and browser.mode == value
            elif kind == "category":
                active = in_categories and value == active_category and active_sub is None
            else:
                active = in_categories and value == (active_category, active_sub)
            # A category whose sub category is selected is highlighted by its text only.
            current = kind == "category" and in_categories and value == active_category

            if self.is_pressed((kind, value)):
                draw_rect(x, y, row_width, height, T.SIDEBAR_PRESSED)
            elif active:
                draw_rect(x, y, row_width, height, T.ACTIVE)
                if T.ACTIVE_BAR is not None:
                    draw_rect(x, y, 3 * ui, height, T.DISCORD if discord else T.ACTIVE_BAR)
            elif self.hovered(x, y, row_width, height):
                draw_rect(x, y, row_width, height, T.SIDEBAR_HOVER)
            elif kind != "sub":
                fill_rect(x, y, row_width, height, T.SIDEBAR_ROW)
            if kind != "sub":
                fill_rect(x, y, row_width, 1, T.SIDEBAR_BORDER)

            if discord:
                color = T.DISCORD_TEXT
            elif kind == "mode" and value == "FAVOURITES":
                color = T.FAVOURITES_TEXT
            elif kind == "mode" and value == "PREFABS":
                color = T.PREFABS_TEXT
            elif active:
                color = T.ACTIVE_TEXT
            elif current:
                color = T.CURRENT_TEXT
            elif kind == "sub":
                color = T.TEXT_DIM
            else:
                color = T.TEXT

            # Icons and glyphs sit in the same 16px slot so labels line up.
            icon_x = x + 12 * ui
            text_x = icon_x + 22 * ui
            label_width = row_width - (text_x - x) - 6 * ui
            if kind == "mode":
                glyph_x = icon_x + (16 * ui - text_width(glyph, font_size)) / 2
                draw_text(glyph, glyph_x, y + (height - 10 * ui) / 2, font_size, color)
            elif kind == "category":
                icon_x += 20 * ui
                text_x += 20 * ui
                label_width -= 20 * ui
                texture = thumbnails.image_texture("category:" + value, _category_icon(value))
                if texture is not None:
                    draw_texture(texture, icon_x, y + (height - 16 * ui) / 2, 16 * ui, 16 * ui)
                if value in pinned:
                    label = label + "  •"
            else:
                text_x += 8 * ui
                label_width -= 8 * ui
            size = int(10 * ui) if kind == "sub" else font_size
            text_y = y + 6 * ui if kind == "sub" else y + (height - 10 * ui) / 2
            draw_text(fit_text(label, label_width, size), text_x, text_y, size, color)
            # Hit areas stop at the panel edge, like the clipped row.
            hit_bottom = max(y, panel_bottom)
            hit_height = min(y + height, panel_top) - hit_bottom
            self.add_hit(x, hit_bottom, row_width, hit_height, (kind, value))

            if kind == "category":
                # Disclosure triangle, its own click target.
                tx = x + 12 * ui
                cy = y + height / 2
                expanded = value in self.expanded
                triangle_hover = self.hovered(tx - 4 * ui, y, 20 * ui, height)
                draw_triangle(tx, cy, 7 * ui, expanded, T.TEXT if triangle_hover else T.TEXT_DIM)
                self.add_hit(tx - 4 * ui, hit_bottom, 20 * ui, hit_height, ("toggle", value))

        gpu.state.scissor_set(*region_scissor)
        fill_rect(margin + width - 1, panel_bottom, 1, panel_height, T.SIDEBAR_BORDER)
        self.add_hit(0, 0, margin + width, region.height, ("sidebar", None))
        # Sidebar background hit goes first so entries are found before it.
        self.hits.insert(0, self.hits.pop())

    def draw_items(self, region, ui, browser, x0, x1):
        catalog = get_catalog()
        sections = state.sections(browser)
        step = store.thumbnail_step()
        list_mode = step == 0
        size = store.thumbnail_size(step) * ui
        font_size = int(10 * ui)
        # Header rows: a gap above, the bar, a gap before the tiles.
        header_gap = 8 * ui
        header_bar = 34 * ui
        header_height = header_gap + header_bar + 8 * ui
        if list_mode:
            tile_width, tile_height = x1 - x0, 30 * ui
        else:
            tile_width = max(size + 16 * ui, 88 * ui)
            tile_height = size + 44 * ui
        gap = 6 * ui
        columns = max(1, int((x1 - x0 + gap) // (tile_width + gap)))

        # Lay out rows from the top, independent of scrolling.
        layout = []
        cursor = 0.0
        for title, ids in sections:
            if title:
                section_key = (browser.mode, browser.category_name(), title)
                folded = section_key in self.collapsed
                layout.append(("header", (title, section_key, folded, len(ids)), cursor))
                cursor += header_height
                if folded:
                    continue
            for index in range(0, len(ids), columns):
                layout.append(("row", ids[index : index + columns], cursor))
                cursor += tile_height + gap
        self.content_height = cursor + 20 * ui
        self.view_height = region.height
        self._clamp_scroll()

        if not any(ids for _, ids in sections):
            draw_text(_empty_message(browser), x0 + 10 * ui, region.height - 40 * ui, int(13 * ui), T.TEXT_DIM)
            return

        top = region.height - 10 * ui + self.scroll
        favourites = set(store.favourites())
        for kind, value, offset in layout:
            y_top = top - offset
            row_height = header_height if kind == "header" else tile_height
            if y_top < 0:
                break
            if y_top - row_height > region.height:
                continue
            if kind == "header":
                title, section_key, folded, count = value
                action = ("section", section_key)
                bar_y = y_top - header_gap - header_bar
                if self.is_pressed(action):
                    draw_rect(x0, bar_y, x1 - x0, header_bar, T.SIDEBAR_PRESSED)
                elif self.hovered(x0, bar_y, x1 - x0, header_bar):
                    draw_rect(x0, bar_y, x1 - x0, header_bar, T.SIDEBAR_HOVER)
                else:
                    fill_rect(x0, bar_y, x1 - x0, header_bar, T.HEADER_BG)
                draw_rect(x0, bar_y, x1 - x0, 1, T.HEADER_LINE)
                # Clicking anywhere on the bar folds/unfolds the section.
                self.add_hit(x0, bar_y, x1 - x0, header_bar, action)
                draw_triangle(x0 + 12 * ui, bar_y + header_bar / 2, 9 * ui, not folded, T.HEADER)
                title = title.upper() if T.HEADER_UPPER else title
                if folded:
                    title = "{}  ({})".format(title, count)
                title_size = int(16 * ui)
                # Room for the triangle on both sides keeps the title centred.
                title = fit_text(title, x1 - x0 - 64 * ui, title_size)
                # Cap height is about 0.7 of the font size, centre that in the bar.
                title_y = bar_y + (header_bar - (title_size + FONT_BUMP) * 0.7) / 2
                draw_text(title, x0 + (x1 - x0 - text_width(title, title_size)) / 2, title_y, title_size, T.HEADER)
                continue
            for column, item_id in enumerate(value):
                x = x0 + column * (tile_width + gap)
                y = y_top - tile_height
                if list_mode:
                    self._draw_list_row(catalog, item_id, x, y, tile_width, tile_height, ui, favourites)
                else:
                    self._draw_tile(catalog, item_id, x, y, tile_width, tile_height, size, ui, font_size, favourites)
        self._draw_scrollbar(region, ui)

    def _draw_tile(self, catalog, item_id, x, y, width, height, size, ui, font_size, favourites):
        part = catalog.get(item_id)
        hover = self.hovered(x, y, width, height)
        pressed = self.is_pressed(("item", item_id))
        draw_rect(x, y, width, height, T.TILE_PRESSED if pressed else T.TILE_HOVER if hover else T.TILE)
        if hover:
            draw_outline(x, y, width, height, T.OUTLINE)
        image_y = y + height - size - 8 * ui
        image_x = x + (width - size) / 2
        texture = thumbnails.part_texture(item_id) if part else None
        if texture is not None:
            draw_texture(texture, image_x, image_y, size, size)
        else:
            draw_rect(image_x, image_y, size, size, T.PLACEHOLDER)
            label = "PREFAB" if part is None else "?"
            draw_text(label, image_x + (size - text_width(label, font_size)) / 2, image_y + size / 2 - 4 * ui, font_size, T.TEXT_DIM)
        name = part.name if part else item_id
        # Label centred in the space under the icon, padded from the tile edges.
        pad = 8 * ui
        line_height = 12 * ui
        lines = wrap_text(name, width - pad * 2, font_size, 2)
        label_top = image_y - 4 * ui
        label_bottom = y + pad
        baseline = (label_top + label_bottom) / 2 + (len(lines) * line_height) / 2 - line_height + 3 * ui
        text_color = T.TEXT if hover else T.TILE_TEXT
        for index, line in enumerate(lines):
            draw_text(line, x + (width - text_width(line, font_size)) / 2, baseline - index * line_height, font_size, text_color)
        self.add_hit(x, y, width, height, ("item", item_id))
        if item_id in favourites:
            draw_text("★", x + 4 * ui, y + height - 14 * ui, int(12 * ui), T.FAVOURITE)
        if part is not None and part.variants:
            label = "+{}".format(len(part.variants))
            badge_width = text_width(label, font_size) + 8 * ui
            bx, by = x + width - badge_width - 3 * ui, image_y
            badge_hover = self.hovered(bx, by, badge_width, 16 * ui)
            badge_pressed = self.is_pressed(("variants", item_id))
            draw_rect(bx, by, badge_width, 16 * ui, T.BADGE_PRESSED if badge_pressed else T.BADGE_HOVER if badge_hover else T.BADGE)
            draw_outline(bx, by, badge_width, 16 * ui, T.BADGE_HOVER_BORDER if badge_hover else T.BADGE_BORDER)
            draw_text(label, bx + 4 * ui, by + 4 * ui, font_size, T.BADGE_TEXT)
            self.add_hit(bx, by, badge_width, 16 * ui, ("variants", item_id))

    def _draw_list_row(self, catalog, item_id, x, y, width, height, ui, favourites):
        part = catalog.get(item_id)
        hover = self.hovered(x, y, width, height)
        pressed = self.is_pressed(("item", item_id))
        draw_rect(x, y, width, height, T.TILE_PRESSED if pressed else T.TILE_HOVER if hover else T.TILE)
        if hover:
            draw_outline(x, y, width, height, T.OUTLINE)
        icon = height - 6 * ui
        texture = thumbnails.part_texture(item_id) if part else None
        if texture is not None:
            draw_texture(texture, x + 3 * ui, y + 3 * ui, icon, icon)
        name = part.name if part else item_id
        if item_id in favourites:
            name = "★ " + name
        detail = part.subcategory if part else "Prefab"
        font_size = int(11 * ui)
        self.add_hit(x, y, width, height, ("item", item_id))
        right = x + width - 6 * ui
        if part is not None and part.variants:
            label = "+{}".format(len(part.variants))
            badge_width = text_width(label, font_size) + 10 * ui
            bx = x + width - badge_width - 4 * ui
            draw_rect(bx, y + 5 * ui, badge_width, height - 10 * ui, T.BADGE)
            draw_outline(bx, y + 5 * ui, badge_width, height - 10 * ui, T.BADGE_BORDER)
            draw_text(label, bx + 5 * ui, y + 10 * ui, font_size, T.BADGE_TEXT)
            self.add_hit(bx, y, badge_width, height, ("variants", item_id))
            right = bx - 6 * ui
        name_x = x + icon + 10 * ui
        detail_x = max(name_x + 80 * ui, x + width * 0.65)
        draw_text(fit_text(name, detail_x - name_x - 10 * ui, font_size), name_x, y + 10 * ui, font_size)
        if right - detail_x > 30 * ui:
            draw_text(fit_text(detail, right - detail_x, font_size), detail_x, y + 10 * ui, font_size, T.TEXT_DIM)

    def _clamp_scroll(self):
        max_scroll = max(0.0, self.content_height - self.view_height)
        self.scroll = min(max(0.0, self.scroll), max_scroll)

    def _draw_scrollbar(self, region, ui):
        if self.content_height <= self.view_height:
            return
        track_x = region.width - 10 * ui
        track_height = region.height - 8 * ui
        thumb_height = max(30 * ui, track_height * self.view_height / self.content_height)
        max_scroll = self.content_height - self.view_height
        thumb_y = region.height - 4 * ui - thumb_height - (track_height - thumb_height) * (self.scroll / max_scroll)
        draw_rect(track_x, 4 * ui, 6 * ui, track_height, T.SCROLL_TRACK)
        draw_rect(track_x, thumb_y, 6 * ui, thumb_height, T.SCROLL)
        self.scrollbar = (track_height - thumb_height, max_scroll)
        self.add_hit(track_x - 4 * ui, 0, 14 * ui, region.height, ("scrollbar", None))

    # Prefab share ---
    def draw_share(self, region, ui, x0, x1):
        feed = get_feed()
        feed.ensure_loaded()
        font_size = int(11 * ui)
        top = region.height - 10 * ui
        if not online_access():
            draw_text("Online access is turned off.", x0 + 10 * ui, top - 30 * ui, int(14 * ui))
            draw_text("Enable it in Preferences > System > Network to browse #prefab-share.", x0 + 10 * ui, top - 54 * ui, font_size, T.TEXT_DIM)
            return

        # Intro box across the top, text on the left, Join Discord on the right.
        intro_size = int(11 * ui)
        intro_pad = 10 * ui
        join_width = text_width("Join Discord", font_size) + 20 * ui
        intro_lines = wrap_text(SHARE_INTRO, (x1 - x0) - join_width - intro_pad * 3, intro_size, 8)
        intro_height = max(22 * ui, len(intro_lines) * 15 * ui) + intro_pad * 2
        intro_y = top - intro_height
        bar_y = intro_y - 32 * ui
        record = feed.selected()
        if self.share_panel_width is None:
            self.share_panel_width = store.share_panel_width()
        low, _, high = store.SHARE_PANEL_WIDTH
        panel = max(low, min(high, self.share_panel_width))
        # Never so wide that a column of cards no longer fits beside it.
        detail_width = max(0.0, min(panel * ui, (x1 - x0) - 110 * ui)) if record else 0
        cards_x1 = x1 - detail_width - (10 * ui if record else 0)
        card_width = min(160 * ui, max(80 * ui, cards_x1 - x0))
        image_width = card_width - 8 * ui
        image_height = image_width * 9 / 16
        card_height = image_height + 40 * ui
        gap = 8 * ui
        columns = max(1, int((cards_x1 - x0 + gap) // (card_width + gap)))
        records = feed.visible_records()
        rows = (len(records) + columns - 1) // columns
        grid_top = bar_y - 10 * ui
        self.view_height = grid_top
        more_height = 40 * ui if feed.next_cursor else 0
        self.content_height = rows * (card_height + gap) + 10 * ui + more_height
        self._clamp_scroll()

        for index, item in enumerate(records):
            row, column = divmod(index, columns)
            x = x0 + column * (card_width + gap)
            y = grid_top + self.scroll - (row + 1) * (card_height + gap) + gap
            if y > grid_top or y + card_height < 0:
                continue
            selected = item["id"] == feed.selected_id
            hover = self.hovered(x, y, card_width, card_height)
            if self.is_pressed(("share_select", item["id"])):
                fill, border = T.CARD_PRESSED, T.CARD_PRESSED_BORDER
            elif selected:
                fill, border = T.CARD_SELECTED, T.CARD_SELECTED_BORDER
            elif hover:
                fill, border = T.CARD_HOVER, T.CARD_HOVER_BORDER
            else:
                fill, border = T.CARD, T.CARD_BORDER
            draw_rect(x, y, card_width, card_height, fill)
            draw_outline(x, y, card_width, card_height, border)
            texture = thumbnails.image_texture(item["id"], item["thumbnail_path"]) if item["thumbnail_path"] else None
            image_y = y + card_height - image_height - 4 * ui
            if texture is not None:
                draw_texture(texture, x + 4 * ui, image_y, image_width, image_height, fill=True)
            else:
                draw_rect(x + 4 * ui, image_y, image_width, image_height, T.PLACEHOLDER)
            draw_text(fit_text(item["name"], card_width - 10 * ui, int(10 * ui)), x + 5 * ui, y + 20 * ui, int(10 * ui))
            draw_text(fit_text("by " + item["author"], card_width - 10 * ui, int(9 * ui)), x + 5 * ui, y + 7 * ui, int(9 * ui), T.TEXT_DIM)
            # Only the part below the toolbar is clickable.
            self.add_hit(x, y, card_width, min(card_height, grid_top - y), ("share_select", item["id"]))

        if feed.next_cursor:
            # Load More sits under the last row, centred on the cards.
            label = "Loading..." if feed.loading else "Load More"
            button_width = text_width(label, font_size) + 20 * ui
            grid_width = columns * (card_width + gap) - gap
            by = grid_top + self.scroll - rows * (card_height + gap) - 30 * ui
            if by < grid_top and by + 22 * ui > 0:
                self._button(label, ("share_more", None), x0 + (grid_width - button_width) / 2, by, ui, T.BUTTON)

        # Toolbar, drawn over cards scrolled up under it.
        draw_rect(x0 - 10 * ui, grid_top, x1 - x0 + 20 * ui, region.height - grid_top, T.BACKGROUND)
        # Blocks clicks on anything scrolled under the toolbar.
        self.add_hit(x0 - 10 * ui, grid_top, x1 - x0 + 20 * ui, region.height - grid_top, ("toolbar", None))
        draw_rect(x0, intro_y, x1 - x0, intro_height, T.PANEL)
        draw_outline(x0, intro_y, x1 - x0, intro_height, T.PANEL_BORDER)
        text_y = intro_y + intro_height - intro_pad - 11 * ui
        for line in intro_lines:
            draw_text(line, x0 + intro_pad, text_y, intro_size, T.TEXT_DIM)
            text_y -= 15 * ui
        self._button(
            "Join Discord", ("share_open", ""), x1 - intro_pad - join_width, intro_y + (intro_height - 22 * ui) / 2, ui, T.DISCORD
        )
        bx = x0 + self._button("Refresh", ("share_refresh", None), x0, bar_y, ui, T.BUTTON) + 6 * ui
        draw_text(fit_text(feed.status, max(10, x1 - bx - 10 * ui), font_size), bx + 6 * ui, bar_y + 7 * ui, font_size, T.TEXT_DIM)

        if record:
            self._draw_share_details(record, x1 - detail_width, 0, detail_width, grid_top, ui)
        self._draw_scrollbar(region, ui)

    def _draw_share_details(self, record, x, y, width, height, ui):
        draw_rect(x, y, width, height, T.PANEL)
        self.add_hit(x, y, width, height, ("panel", None))
        # Drag the left edge to resize.
        grip_hover = self.hovered(x - 3 * ui, y, 6 * ui, height) or self.hover == ("share_resize", None)
        draw_rect(x, y, 2 * ui if grip_hover else 1, height, T.ACCENT if grip_hover else T.PANEL_BORDER)
        self.add_hit(x - 3 * ui, y, 6 * ui, height, ("share_resize", None))
        pad = 10 * ui
        inner = width - pad * 2
        cursor = height - pad
        image_height = inner * 9 / 16
        texture = thumbnails.image_texture(record["id"], record["thumbnail_path"]) if record["thumbnail_path"] else None
        cursor -= image_height
        if texture is not None:
            draw_texture(texture, x + pad, cursor, inner, image_height, fill=True)
        else:
            draw_rect(x + pad, cursor, inner, image_height, T.PLACEHOLDER)

        cursor -= 30 * ui
        self._button("Open in Discord", ("share_open", record["id"]), x + pad, cursor, ui, T.DISCORD, width=inner)
        cursor -= 28 * ui
        self._button("Import Prefab", ("share_import", None), x + pad, cursor, ui, T.BUTTON, width=inner)

        cursor -= 6 * ui
        for line in wrap_text(record["name"], inner, int(13 * ui), 2):
            cursor -= 18 * ui
            draw_text(line, x + pad, cursor, int(13 * ui))
        cursor -= 16 * ui
        draw_text(fit_text("by " + record["author"], inner, int(11 * ui)), x + pad, cursor, int(11 * ui), T.TEXT_DIM)

        if len(record["attachments"]) > 1:
            cursor -= 10 * ui
            for index, attachment in enumerate(record["attachments"]):
                cursor -= 22 * ui
                active = index == record["attachment_index"]
                row_hover = self.hovered(x + pad, cursor, inner, 20 * ui)
                if self.is_pressed(("share_attachment", index)):
                    row_fill = T.BUTTON_PRESSED
                else:
                    row_fill = T.BUTTON_HOVER if active or row_hover else T.BUTTON
                draw_rect(x + pad, cursor, inner, 20 * ui, row_fill)
                draw_outline(x + pad, cursor, inner, 20 * ui, T.BUTTON_HOVER_BORDER if active else T.BUTTON_BORDER)
                draw_text(
                    fit_text(attachment.get("filename", "Attachment"), inner - 10 * ui, int(10 * ui)),
                    x + pad + 5 * ui,
                    cursor + 6 * ui,
                    int(10 * ui),
                    T.BUTTON_TEXT if active else T.TEXT,
                )
                self.add_hit(x + pad, cursor, inner, 20 * ui, ("share_attachment", index))

        if record["content"]:
            cursor -= 12 * ui
            max_lines = max(0, int((cursor - pad) // (14 * ui)))
            for line in wrap_text(record["content"], inner, int(10 * ui), max_lines):
                cursor -= 14 * ui
                draw_text(line, x + pad, cursor, int(10 * ui), T.TEXT_DIM)

    def _button(self, label, action, x, y, ui, color, text_color=None, width=None):
        """Draw a button and return its width. A given width centres the label."""
        font_size = int(11 * ui)
        label_width = text_width(fit_text(label, (width or 1e9) - 12 * ui, font_size), font_size)
        if width is None:
            width = label_width + 20 * ui
        height = 22 * ui
        hover = self.hovered(x, y, width, height)
        pressed = self.is_pressed(action)
        if color is T.BUTTON:
            fill = T.BUTTON_PRESSED if pressed else T.BUTTON_HOVER if hover else T.BUTTON
            border = T.BUTTON_HOVER_BORDER if hover else T.BUTTON_BORDER
            text_color = text_color or T.BUTTON_TEXT
        elif color is T.DISCORD:
            fill = T.DISCORD_PRESSED if pressed else T.DISCORD_HOVER if hover else T.DISCORD
            border = T.DISCORD_BORDER
            text_color = text_color or (1.0, 1.0, 1.0, 1.0)
        else:
            fill = tuple(min(1.0, channel * 1.2 + 0.03) for channel in color[:3]) + (1.0,) if hover else color
            border = None
            text_color = text_color or (1.0, 1.0, 1.0, 1.0)
        draw_rect(x, y, width, height, fill)
        draw_outline(x, y, width, height, border)
        label = fit_text(label, width - 12 * ui, font_size)
        draw_text(label, x + (width - text_width(label, font_size)) / 2, y + 7 * ui, font_size, text_color)
        self.add_hit(x, y, width, height, action)
        return width


def _category_icon(category):
    from .catalog_data import category_icon_path

    return category_icon_path(category)


def _empty_message(browser):
    if browser.searching():
        return "Nothing matches '{}'".format(browser.search.strip())
    return {
        "FAVOURITES": "No favourites yet. Right click a part to add it.",
        "RECENT": "Nothing placed yet.",
        "PREFABS": "No prefabs in your prefab folder.",
    }.get(browser.mode, "Nothing to show.")


# Draw handler ---
def _draw_callback():
    context = bpy.context
    area = context.area
    if area is None:
        return
    view = view_for_area(area)
    if view is None:
        return
    space.hide_regions_later(area)
    try:
        view.draw(context)
    except Exception as error:  # Never let a draw error spam every redraw silently.
        import traceback

        traceback.print_exc()
        draw_text("Asset browser error: {}".format(error), 10, 10, 12, (1, 0.4, 0.4, 1))


def draw_header(self, context):
    """Header of a browser area, in place of the node editor's."""
    browser = state.get_state(context)
    layout = self.layout
    layout.template_header()
    layout.label(text=space.TITLE)
    layout.separator_spacer()
    if browser.mode == "SHARE" and not browser.searching():
        layout.label(text="Sort Prefabs by")
        layout.prop(browser, "share_sort", text="")
        layout.prop(browser, "share_search", text="", icon="URL")
    layout.prop(browser, "search", text="", icon="VIEWZOOM")
    row = layout.row()
    row.ui_units_x = 6
    row.prop(browser, "thumbnail_step", text="Size")


# Views ---
def view_for_area(area):
    """The BrowserView of a browser area, made on first use."""
    if not space.is_browser_area(area):
        return None
    pointer = area.as_pointer()
    view = _views.get(pointer)
    if view is None:
        view = _views[pointer] = BrowserView(area)
    return view


def view_for(context):
    return view_for_area(context.area)


def find_browser_window(context):
    """A window showing only the browser (the pop-out), not one docked in a layout."""
    for window, area in space.browser_areas(context.window_manager):
        if len(window.screen.areas) == 1:
            return window
    return None


_original_node_header = None


def _node_header_draw(self, context):
    if space.is_browser_area(context.area):
        draw_header(self, context)
    elif _original_node_header is not None:
        _original_node_header(self, context)


# Input ---
class NMS_OT_browser_event(bpy.types.Operator):
    """Asset browser window input"""

    bl_idname = "nms.browser_event"
    bl_label = "Asset Browser Input"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return space.is_browser_area(context.area)

    def invoke(self, context, event):
        view = view_for(context)
        region = context.region
        if view is None or region is None:
            return {"PASS_THROUGH"}
        x, y = event.mouse_region_x, event.mouse_region_y
        view.mouse = (x, y)
        action = view.hit(x, y)
        kind, value = action if action else (None, None)

        if event.type == "MOUSEMOVE":
            if action != view.hover:
                if kind == "share_resize":
                    context.window.cursor_set("MOVE_X")
                elif view.hover == ("share_resize", None):
                    context.window.cursor_set("DEFAULT")
                view.hover = action
            context.area.tag_redraw()
            return {"PASS_THROUGH"}

        if event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "TRACKPADPAN"}:
            is_trackpad_pan = event.type == "TRACKPADPAN"
            if is_trackpad_pan:
                scroll_delta = event.mouse_y - event.mouse_prev_y
                direction = 1 if scroll_delta > 0 else -1 if scroll_delta < 0 else 0
            else:
                direction = -1 if event.type == "WHEELUPMOUSE" else 1
                scroll_delta = direction * 80 * context.preferences.system.ui_scale
            sidebar_delta = (
                scroll_delta
                if is_trackpad_pan
                else direction * 48 * context.preferences.system.ui_scale
            )
            if event.ctrl:
                if direction:
                    store.set_thumbnail_step(store.thumbnail_step() - direction)
                    state.bump(context)
            elif kind in {"sidebar", "mode", "category", "sub", "toggle"}:
                view.sidebar_scroll += sidebar_delta
            else:
                view.scroll += scroll_delta
            context.area.tag_redraw()
            return {"FINISHED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if kind in DRAG_KINDS:
                return self.left_click(context, view, kind, value, event)
            if kind in CLICK_KINDS:
                view.pressed = action
                view.hover = action
                context.area.tag_redraw()
                return {"FINISHED"}
            view.pressed = None
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            pressed, view.pressed = view.pressed, None
            if pressed is None:
                return {"PASS_THROUGH"}
            context.area.tag_redraw()
            # Released somewhere else: no click, like a normal button.
            if action != pressed:
                return {"FINISHED"}
            return self.left_click(context, view, kind, value, event)

        if event.type == "RIGHTMOUSE" and event.value == "PRESS":
            if kind in {"item", "variants"}:
                bpy.ops.nms.browser_item_menu("INVOKE_DEFAULT", item_id=value)
            elif kind == "category":
                bpy.ops.nms.browser_category_menu("INVOKE_DEFAULT", category=value)
            return {"FINISHED"}
        return {"PASS_THROUGH"}

    def left_click(self, context, view, kind, value, event):
        browser = state.get_state(context)
        feed = get_feed()
        if kind == "item":
            if ops.place_item(value):
                bpy.ops.ed.undo_push(message="Place {}".format(ops.item_label(value)))
        elif kind == "variants":
            bpy.ops.nms.browser_variants("INVOKE_DEFAULT", item_id=value)
        elif kind == "mode":
            browser.search = ""
            browser.mode = value
        elif kind == "category":
            # Selects only, the disclosure triangle opens and closes the tree.
            browser.search = ""
            browser.set_category(value)
        elif kind == "toggle":
            view.expanded.symmetric_difference_update({value})
        elif kind == "section":
            view.collapsed.symmetric_difference_update({value})
        elif kind == "sub":
            category, sub = value
            browser.search = ""
            browser.set_category(category)
            browser.subcategory = sub
        elif kind == "share_select":
            feed.select(value)
        elif kind == "share_attachment":
            bpy.ops.nms.browser_share_attachment(index=value)
        elif kind == "share_import":
            feed.import_selected()
        elif kind == "share_refresh":
            feed.refresh(sort=browser.share_sort, search=browser.share_search)
        elif kind == "share_more":
            feed.load_more()
        elif kind == "share_open":
            bpy.ops.nms.browser_share_open(thread_id=value)
        elif kind == "scrollbar":
            bpy.ops.nms.browser_scroll_drag("INVOKE_DEFAULT")
        elif kind == "share_resize":
            bpy.ops.nms.browser_share_resize("INVOKE_DEFAULT")
        else:
            return {"PASS_THROUGH"}
        context.area.tag_redraw()
        return {"FINISHED"}


class NMS_OT_browser_scroll_drag(bpy.types.Operator):
    """Drag the asset browser scrollbar"""

    bl_idname = "nms.browser_scroll_drag"
    bl_label = "Scroll Asset Browser"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        view = view_for(context)
        if view is None or view.scrollbar is None:
            return {"CANCELLED"}
        self._view = view
        self._start_y = event.mouse_region_y
        self._start_scroll = view.scroll
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        view = self._view
        if event.type == "MOUSEMOVE" and view.scrollbar:
            travel, max_scroll = view.scrollbar
            if travel > 0:
                delta = (self._start_y - event.mouse_region_y) / travel * max_scroll
                view.scroll = self._start_scroll + delta
                if context.area:
                    context.area.tag_redraw()
            return {"RUNNING_MODAL"}
        if event.type == "ESC" or (event.type in {"LEFTMOUSE", "RIGHTMOUSE"} and event.value == "RELEASE"):
            return {"FINISHED"}
        return {"RUNNING_MODAL"}


class NMS_OT_browser_share_resize(bpy.types.Operator):
    """Drag to resize the Prefab Share detail panel"""

    bl_idname = "nms.browser_share_resize"
    bl_label = "Resize Prefab Share Panel"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        view = view_for(context)
        if view is None:
            return {"CANCELLED"}
        self._view = view
        self._ui = context.preferences.system.ui_scale
        self._start_x = event.mouse_region_x
        self._start_width = view.share_panel_width or store.share_panel_width()
        context.window.cursor_modal_set("MOVE_X")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _finish(self, context, keep):
        context.window.cursor_modal_restore()
        if keep:
            store.set_share_panel_width(self._view.share_panel_width)
        else:
            self._view.share_panel_width = self._start_width
        if context.area:
            context.area.tag_redraw()

    def modal(self, context, event):
        if event.type == "MOUSEMOVE":
            # The panel sits on the right, so dragging left makes it wider.
            low, _, high = store.SHARE_PANEL_WIDTH
            width = self._start_width + (self._start_x - event.mouse_region_x) / self._ui
            self._view.share_panel_width = max(low, min(high, width))
            if context.area:
                context.area.tag_redraw()
            return {"RUNNING_MODAL"}
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context, keep=False)
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self._finish(context, keep=True)
            return {"FINISHED"}
        return {"RUNNING_MODAL"}


classes = (NMS_OT_browser_event, NMS_OT_browser_scroll_drag, NMS_OT_browser_share_resize)

# Act on press (they start a drag), everything else in CLICK_KINDS on release.
DRAG_KINDS = {"scrollbar", "share_resize"}
CLICK_KINDS = {
    "item",
    "variants",
    "mode",
    "category",
    "toggle",
    "section",
    "sub",
    "share_select",
    "share_attachment",
    "share_import",
    "share_refresh",
    "share_more",
    "share_open",
}

KEYMAP_EVENTS = (
    ("LEFTMOUSE", "PRESS", False),
    ("LEFTMOUSE", "RELEASE", False),
    ("RIGHTMOUSE", "PRESS", False),
    ("MOUSEMOVE", "ANY", False),
    ("TRACKPADPAN", "ANY", False),
    ("TRACKPADPAN", "ANY", True),
)
# The wheel is taken by the View2D keymap before the Info keymap is reached.
# So is a press on the node editor's own scroller zones (right and bottom
# edges, under the browser scrollbar), which view2d.scroller_activate takes.
VIEW2D_EVENTS = (
    ("LEFTMOUSE", "PRESS", False),
    ("WHEELUPMOUSE", "ANY", False),
    ("WHEELDOWNMOUSE", "ANY", False),
    ("WHEELUPMOUSE", "ANY", True),
    ("WHEELDOWNMOUSE", "ANY", True),
    ("TRACKPADPAN", "ANY", False),
    ("TRACKPADPAN", "ANY", True),
)


@bpy.app.handlers.persistent
def _on_load_post(*_args):
    # Area pointers change with a new file, views are made again on draw.
    _views.clear()


def register():
    global _draw_handle
    for cls in classes:
        bpy.utils.register_class(cls)
    global _original_node_header
    _draw_handle = bpy.types.SpaceNodeEditor.draw_handler_add(_draw_callback, (), "WINDOW", "POST_PIXEL")
    # The node editor header (menus, node tree picker) means nothing here, so
    # browser areas draw their own.
    header = bpy.types.NODE_HT_header
    if header.draw is not _node_header_draw:
        _original_node_header = header.draw
        header.draw = _node_header_draw

    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is not None:
        for keymap_name, space_type, events in (
            ("Node Editor", "NODE_EDITOR", KEYMAP_EVENTS),
            ("View2D", "EMPTY", VIEW2D_EVENTS),
        ):
            keymap = keyconfig.keymaps.new(name=keymap_name, space_type=space_type)
            for event_type, value, ctrl in events:
                item = keymap.keymap_items.new(NMS_OT_browser_event.bl_idname, event_type, value, ctrl=ctrl)
                _keymaps.append((keymap, item))

    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)
    space.redraw()


def unregister():
    global _draw_handle
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
    for keymap, item in _keymaps:
        try:
            keymap.keymap_items.remove(item)
        except (ReferenceError, RuntimeError):
            pass
    _keymaps.clear()
    global _original_node_header
    header = bpy.types.NODE_HT_header
    if header.draw is _node_header_draw and _original_node_header is not None:
        header.draw = _original_node_header
    _original_node_header = None
    if _draw_handle is not None:
        bpy.types.SpaceNodeEditor.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    for area_pointer in list(_views):
        _views.pop(area_pointer, None)
    _wrap_cache.clear()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
