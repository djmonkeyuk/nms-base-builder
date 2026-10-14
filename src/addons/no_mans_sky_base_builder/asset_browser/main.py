import ctypes
import json
import os
import sys
import tempfile
import time
import threading
import urllib.parse
import urllib.request
from functools import partial

import bpy

from .collapsable_frame import CollapsableFrame
from .flow_layout import FlowLayout
from .icons import icons
from .item import Item, Preset
from .settings import Settings
from .utils import contexts, parts_definition
from .utils.qt import QtCore, QtGui, QtWidgets

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
SEND_SNIPPET = os.path.join(FILE_DIR, "build_part_snippet.txt")
EDIT_PRESET_SNIPPET = os.path.join(FILE_DIR, "edit_preset_snippet.txt")
END_SNIPPET = os.path.join(FILE_DIR, "terminate_snippet.txt")
BROWSER_LAYOUT_FILE = os.path.join(FILE_DIR, "..", "resources", "asset_data.yaml")
NICE_NAMES_FILE = os.path.join(FILE_DIR, "..", "resources", "nice_names.json")
STYLESHEET_FILE = os.path.join(FILE_DIR, "core.css")
APP_ICON = os.path.join(FILE_DIR, "logo.png")
CATEGORY_ICONS_DIR = os.path.join(FILE_DIR, "..", "images", "icons")
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")

# Best-effort filename match per part category, from the icon set in
# images/icons - several are a judgement call rather than an exact fit.
# Easy to swap by editing this table. (prefab-share is handled separately
# in _default_tab_icon, since it's tinted rather than used as-is.)
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
}
PREFAB_SHARE_TAB_ICON = os.path.join(CATEGORY_ICONS_DIR, "T_Icon_Hash.png")
PREFAB_SHARE_URL = "https://api.djmonkey.uk"
PREFAB_SHARE_CACHE_PATH = os.path.join(USER_PATH, "prefab-share")
# Discord message metadata (name/author/content/attachments) and
# thumbnail images, keyed by thread id. Treated as permanent once
# written - a Discord post's content essentially never changes, so this
# lets a returning session skip the /post and thumbnail-CDN calls for
# every thread it has already seen, only hitting the network for
# threads it doesn't have cached yet. Separate from the folder above,
# which holds the user's already-imported .nmsprefab files.
PREFAB_SHARE_MESSAGE_CACHE_PATH = os.path.join(PREFAB_SHARE_CACHE_PATH, "messages")
PREFAB_SHARE_THUMBNAIL_CACHE_PATH = os.path.join(PREFAB_SHARE_CACHE_PATH, "thumbnails")
PREFAB_SHARE_EXTENSIONS = (".json", ".txt", ".nmsprefab", ".nmsbase")
PREFAB_SHARE_DISCORD_INVITE_URL = "https://discord.gg/kpGVRKPn5W"
PREFAB_SHARE_DISCORD_GUILD_ID = "844499346450939904"
PREFAB_SHARE_DISCORD_PARENT_CHANNEL_ID = "1107768757482442842"
PREFAB_SHARE_DETAILS_THUMBNAIL_WIDTH = 280

# Thumbnail size slider for the part list, similar to a file browser.
# Step 0 is the smallest setting and switches the part list into a compact
# list view; steps 1+ are grid views at increasing thumbnail sizes.
THUMBNAIL_SIZE_STEPS = (32, 48, 64, 80, 100, 128)
DEFAULT_THUMBNAIL_SIZE_STEP = 3

PREFAB_SHARE_SORT_OPTIONS = (
    ("Discord Order", "default"),
    ("Newest", "newest"),
    ("Oldest", "oldest"),
    ("A-Z", "title_asc"),
    ("Z-A", "title_desc"),
    ("Most Comments", "activity"),
)

DISCORD_BRAND_COLOR = "#5865F2"

# Accent colours for the unique, always-present tabs.
TAB_ICON_COLOR_FAVOURITES = "#D8D02E"  # the app's existing yellow accent.
TAB_ICON_COLOR_PREFABS = "#FF69B4"
TAB_ICON_COLOR_PREFAB_SHARE = DISCORD_BRAND_COLOR

with open(NICE_NAMES_FILE, "r") as stream:
    NICE_NAME_DATA = json.load(stream)


def _tinted_icon(resource_path, color):
    """Recolour a monochrome icon resource, keeping its original alpha
    shape (a standard QPainter SourceIn tint)."""
    source = QtGui.QPixmap(resource_path)
    if source.isNull():
        return QtGui.QIcon()
    tinted = QtGui.QPixmap(source.size())
    tinted.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(tinted)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QtGui.QColor(color))
    painter.end()
    return QtGui.QIcon(tinted)


def _category_tab_icon(tab_name):
    """The tab icon for a part category, loaded from images/icons as-is
    (no tinting - these are already finished icon art). Falls back to a
    blank icon when there is no mapped/available
    file for that tab."""
    filename = CATEGORY_ICON_FILES.get(tab_name)
    if not filename:
        return QtGui.QIcon()
    path = os.path.join(CATEGORY_ICONS_DIR, filename)
    if not os.path.isfile(path):
        return QtGui.QIcon()
    return QtGui.QIcon(path)


def _prefab_share_message_cache_path(thread_id):
    return os.path.join(PREFAB_SHARE_MESSAGE_CACHE_PATH, "{}.json".format(thread_id))


def _load_cached_prefab_share_message(thread_id):
    try:
        with open(
            _prefab_share_message_cache_path(thread_id), "r", encoding="utf-8"
        ) as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return None


def _save_cached_prefab_share_message(thread_id, message):
    try:
        os.makedirs(PREFAB_SHARE_MESSAGE_CACHE_PATH, exist_ok=True)
        with open(
            _prefab_share_message_cache_path(thread_id), "w", encoding="utf-8"
        ) as stream:
            json.dump(message, stream)
    except OSError:
        pass


def _prefab_share_thumbnail_cache_path(thread_id):
    return os.path.join(PREFAB_SHARE_THUMBNAIL_CACHE_PATH, "{}.bin".format(thread_id))


def _load_cached_prefab_share_thumbnail(thread_id):
    try:
        with open(_prefab_share_thumbnail_cache_path(thread_id), "rb") as stream:
            return stream.read()
    except OSError:
        return None


def _save_cached_prefab_share_thumbnail(thread_id, image_data):
    try:
        os.makedirs(PREFAB_SHARE_THUMBNAIL_CACHE_PATH, exist_ok=True)
        with open(_prefab_share_thumbnail_cache_path(thread_id), "wb") as stream:
            stream.write(image_data)
    except OSError:
        pass


class HorizontalTabBar(QtWidgets.QTabBar):
    """A QTabBar for a West-positioned QTabWidget that keeps each tab's
    icon and text drawn horizontally, like a normal button, instead of
    Qt's default behaviour of rotating the whole tab 90 degrees when the
    tab bar is docked on a side. Tabs are stacked top-to-bottom, each one
    reading left-to-right, like a sidebar list."""

    MIN_WIDTH = 150
    MAX_WIDTH = 230
    TAB_HEIGHT = 32
    ICON_SIZE = 16
    PADDING_X = 10
    ICON_SPACING = 6

    BACKGROUND_COLOR = QtGui.QColor("#1a232f")
    BORDER_COLOR = QtGui.QColor("#0a1018")
    SEPARATOR_COLOR = QtGui.QColor("#D8D02E")
    # The one tab after which the unique tabs (Favourites, Prefabs,
    # prefab-share) end and the part-category tabs begin.
    SEPARATOR_AFTER_TAB = "prefab-share"

    def __init__(self, *args, **kwargs):
        super(HorizontalTabBar, self).__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.setDrawBase(False)

    def tabSizeHint(self, index):
        return QtCore.QSize(self._shared_tab_width(), self.TAB_HEIGHT)

    def minimumTabSizeHint(self, index):
        return self.tabSizeHint(index)

    def _shared_tab_width(self):
        # Every tab shares one width, sized to fit the longest current
        # label (capped), so the sidebar reads as a tidy column of
        # buttons rather than ragged-width tabs.
        metrics = self.fontMetrics()
        needed = self.MIN_WIDTH
        for i in range(self.count()):
            icon_allowance = (
                0 if self.tabIcon(i).isNull()
                else self.ICON_SIZE + self.ICON_SPACING
            )
            text_width = metrics.horizontalAdvance(self.tabText(i).upper())
            needed = max(needed, text_width + icon_allowance + self.PADDING_X * 2)
        return min(needed, self.MAX_WIDTH)

    def mouseMoveEvent(self, event):
        super(HorizontalTabBar, self).mouseMoveEvent(event)
        self.update()

    def leaveEvent(self, event):
        super(HorizontalTabBar, self).leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        # The sidebar panel background, spanning the bar's full height
        # (not just down to the last tab) plus a 1px edge separating it
        # from the content pane.
        painter.fillRect(self.rect(), self.BACKGROUND_COLOR)
        painter.setPen(self.BORDER_COLOR)
        painter.drawLine(
            self.width() - 1, 0, self.width() - 1, self.height() - 1
        )

        hover_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        for index in range(self.count()):
            self._paint_tab(painter, index, hover_pos)
        painter.end()

    def _paint_tab(self, painter, index, hover_pos):
        rect = self.tabRect(index)
        if not rect.isValid():
            return
        selected = index == self.currentIndex()
        hovered = (not selected) and rect.contains(hover_pos)

        if selected:
            background = QtGui.QColor("#4a5a75")
        elif hovered:
            background = QtGui.QColor(255, 255, 255, 25)
        else:
            background = QtGui.QColor(0, 0, 0, 100)
        painter.fillRect(rect, background)

        painter.setPen(self.BORDER_COLOR)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        content_rect = rect.adjusted(self.PADDING_X, 0, -self.PADDING_X, 0)
        icon = self.tabIcon(index)
        if not icon.isNull():
            icon_rect = QtCore.QRect(
                content_rect.left(),
                rect.center().y() - self.ICON_SIZE // 2,
                self.ICON_SIZE,
                self.ICON_SIZE,
            )
            icon.paint(painter, icon_rect, QtCore.Qt.AlignCenter)
            content_rect.setLeft(icon_rect.right() + self.ICON_SPACING)

        metrics = painter.fontMetrics()
        text = metrics.elidedText(
            self.tabText(index).upper(), QtCore.Qt.ElideRight, content_rect.width()
        )
        painter.setPen(QtGui.QColor("#FFFFFF"))
        painter.drawText(
            content_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text
        )

        # A clearer divider between the unique tabs (Favourites, Prefabs,
        # prefab-share) and the general part-category tabs below them.
        if self.tabText(index) == self.SEPARATOR_AFTER_TAB:
            painter.setPen(QtGui.QPen(self.SEPARATOR_COLOR, 1))
            painter.drawLine(
                rect.left(), rect.bottom(), rect.right(), rect.bottom()
            )


class SidebarTabWidget(QtWidgets.QTabWidget):
    """A QTabWidget that fills in the sidebar background/border below its
    West-positioned tab bar's last tab, down to the bottom of the widget.
    QTabWidget's own layout always sizes the tab bar to exactly its
    sizeHint (just enough for its tabs), and fighting that by force-
    resizing the tab bar itself does not stick - Qt's internal layout
    re-asserts the sizeHint on a later pass regardless. Painting the
    leftover gap here, underneath the tab bar, is the reliable way to
    make the sidebar panel read as one continuous background down to the
    bottom of the window."""

    def paintEvent(self, event):
        super(SidebarTabWidget, self).paintEvent(event)
        if self.tabPosition() != QtWidgets.QTabWidget.West:
            return
        bar = self.tabBar()
        width = bar.sizeHint().width()
        gap_top = bar.height()
        if self.height() <= gap_top:
            return
        painter = QtGui.QPainter(self)
        painter.fillRect(
            0, gap_top, width, self.height() - gap_top,
            HorizontalTabBar.BACKGROUND_COLOR,
        )
        painter.setPen(HorizontalTabBar.BORDER_COLOR)
        painter.drawLine(width - 1, gap_top, width - 1, self.height() - 1)


class AspectFitThumbnail(QtWidgets.QLabel):
    """A fixed-size 16:9 box that cover-fits/crops its pixmap to it.

    Callers must explicitly tell it what width to be via apply_width() -
    it never recomputes its own size from inside resizeEvent. An earlier
    version did (either by mutating its own min/max height, or even just
    by declaring heightForWidth support) so it could track a resizable
    parent on its own; inside this app's real widget tree - a QLabel
    whose width is Expanding, sitting in a QVBoxLayout, inside a
    QScrollArea, inside a QSplitter pane - that self-reacting resize
    turned into a live feedback loop the moment a real image was loaded
    (confirmed by instrumenting resizeEvent: width crept up by ~2px on
    every single call, forever, regardless of whether the reaction was a
    direct resize() or just a heightForWidth query), which crashed with
    EXCEPTION_STACK_OVERFLOW. Being purely externally-driven sidesteps
    that class of bug entirely: nothing here ever mutates this widget's
    own geometry in response to its own resize.
    """

    ASPECT_RATIO = 9.0 / 16.0

    def __init__(self, placeholder_text="", *args, **kwargs):
        super(AspectFitThumbnail, self).__init__(placeholder_text, *args, **kwargs)
        self._source_pixmap = None
        self._placeholder_text = placeholder_text
        self._current_width = None
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setWordWrap(True)
        self.setScaledContents(False)

    def apply_width(self, width):
        width = max(int(width), 0)
        if width == self._current_width:
            return
        self._current_width = width
        height = int(round(width * self.ASPECT_RATIO)) if width else 0
        self.setFixedSize(width, height)
        self._refresh_pixmap()

    def set_source_pixmap(self, pixmap):
        self._source_pixmap = pixmap
        self._refresh_pixmap()

    def set_image_data(self, image_data):
        pixmap = QtGui.QPixmap()
        if pixmap.loadFromData(image_data):
            self.set_source_pixmap(pixmap)
            return True
        return False

    def clear_thumbnail(self, placeholder_text=None):
        self._source_pixmap = None
        self.setPixmap(QtGui.QPixmap())
        self.setText(
            self._placeholder_text if placeholder_text is None else placeholder_text
        )

    def _refresh_pixmap(self):
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return
        target_size = self.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = self._source_pixmap.scaled(
            target_size,
            QtCore.Qt.KeepAspectRatioByExpanding,
            QtCore.Qt.SmoothTransformation,
        )
        cropped = scaled.copy(
            max((scaled.width() - target_size.width()) // 2, 0),
            max((scaled.height() - target_size.height()) // 2, 0),
            target_size.width(),
            target_size.height(),
        )
        self.setText("")
        self.setPixmap(cropped)


class ElidedLabel(QtWidgets.QLabel):
    """A single-line QLabel that elides overflowing text with "..."
    instead of wrapping, so sibling cards/rows stay a consistent height
    regardless of how long a particular name or author is."""

    def __init__(self, *args, **kwargs):
        super(ElidedLabel, self).__init__(*args, **kwargs)
        self._full_text = ""
        self.setWordWrap(False)

    def setText(self, text):
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        self._apply_elided_text()

    def resizeEvent(self, event):
        super(ElidedLabel, self).resizeEvent(event)
        self._apply_elided_text()

    def _apply_elided_text(self):
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(
            self._full_text, QtCore.Qt.ElideRight, max(self.width(), 0)
        )
        QtWidgets.QLabel.setText(self, elided)


class PrefabShareCard(QtWidgets.QFrame):
    clicked = QtCore.Signal(object)

    def __init__(self, share_data, *args, **kwargs):
        super(PrefabShareCard, self).__init__(*args, **kwargs)
        self.share_data = share_data
        self.setObjectName("PrefabShareCard")
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFixedWidth(200)
        self.setToolTip(share_data["name"])

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.thumbnail = AspectFitThumbnail("No preview", self)
        self.thumbnail.setObjectName("PrefabShareThumbnail")
        self.thumbnail.apply_width(184)
        self.name_label = ElidedLabel(self)
        self.name_label.setObjectName("PrefabShareName")
        self.name_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.name_label.setText(share_data["name"])
        self.author_label = ElidedLabel(self)
        self.author_label.setObjectName("PrefabShareAuthor")
        self.author_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.author_label.setText("by {}".format(share_data["author"]))

        layout.addWidget(self.thumbnail)
        layout.addWidget(self.name_label)
        layout.addWidget(self.author_label)
        layout.addStretch()

    def set_thumbnail(self, image_data):
        self.thumbnail.set_image_data(image_data)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.share_data)
        super(PrefabShareCard, self).mousePressEvent(event)


class AssetBrowser(QtWidgets.QMainWindow):
    prefab_share_catalog_loaded = QtCore.Signal(object)
    prefab_share_post_loaded = QtCore.Signal(object, object)
    prefab_share_post_failed = QtCore.Signal(object, str)
    prefab_share_thumbnail_loaded = QtCore.Signal(object, object)
    prefab_share_prefab_loaded = QtCore.Signal(object, object)
    prefab_share_request_failed = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super(AssetBrowser, self).__init__(*args, **kwargs)
        self.setWindowTitle("No Man's Sky Base Builder :: Asset Browser")
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        app_id = "djmonkey.NMSBB.AssetBrowser.1"  # arbitrary string
        # FIXME: do this in some platform-agnostic way if possible
        if hasattr(ctypes, "windll"):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        self.setWindowTitle("No Man's Sky Blender Builder - Asset Browser")
        self.setWindowIcon(QtGui.QIcon(APP_ICON))
        self.__item_widgets = {}
        self.__search_buttons = {}
        # id -> nice_name for every searchable part, independent of whether
        # a search widget has actually been built for it yet - see
        # _ensure_search_item_widget. Lets refresh_search() know what *could*
        # match without needing one built-and-eagerly-hidden widget per part
        # up front (half of every part widget built at startup used to be
        # exactly that, used only if the user happened to search).
        self.__search_item_data = {}
        # base part id -> [(variant_id, nice_name), ...], built once
        # alongside the main grid's own variant wiring (generate_contents)
        # so a search widget built later by _ensure_search_item_widget can
        # look its variants up instead of needing the original eager
        # variant-wiring pass to have already found and touched it.
        self.__variants_by_base = {}
        # Category title -> (frame, layout) for its (possibly still-empty)
        # tab container, and the set of categories whose contents have
        # actually been built - see generate_contents/
        # _ensure_category_tab_built. Set here, before any tab exists, not
        # inside generate_contents: adding the very first tab (Favourites,
        # in generate_favourites, called before generate_contents) makes
        # Qt fire currentChanged immediately, which refresh_layouts reacts
        # to - leaving these unset that early raised an AttributeError
        # there (swallowed by Qt's slot exception handling, so harmless
        # beyond a scary traceback and a skipped geometry refresh, but a
        # real bug regardless).
        self.__browser_data = {}
        self.__category_tab_built = set()
        self.__category_frames = {}
        self.__preset_search_buttons = {}
        self.__favourite_item_widgets = []
        self.__part_flow_layouts = []
        self.__prefab_share_cards = {}
        self.__prefab_share_posts = {}
        self.__prefab_share_thumbnail_data = {}
        self.__prefab_share_post_requests = set()
        self.__prefab_share_card_order = []
        self.__prefab_share_next_card_index = 0
        self.__prefab_share_next_cursor = None
        self.__prefab_share_loaded_thread_ids = set()
        self.__prefab_share_selected_record = None
        self.__prefab_share_query_token = 0
        self.__prefab_share_has_loaded = False
        self.prefab_share_status = QtWidgets.QLabel(self)
        self.__settings = Settings()
        self.__thumbnail_size_step = (
            self.__settings.get_thumbnail_size_step() or DEFAULT_THUMBNAIL_SIZE_STEP
        )
        self._build_ui()
        self._layout_ui()
        self._setup_ui()

        # Applied before any part/preset widgets exist, not after: with
        # ~2900 widgets already built, setStyleSheet() has to re-match CSS
        # selectors and re-style the entire existing tree in one pass
        # (~2s, confirmed by profiling). Styling each widget incrementally
        # as it's constructed instead - which is what applying the sheet
        # to the still-empty window first gets you, since Qt cascades a
        # parent's stylesheet to children as they're added - cut total
        # cold-start time from ~3.9s to ~2.5s in that same profile.
        self.apply_style()

        self.generate_favourites()
        self.generate_contents()
        self._apply_thumbnail_view_settings()
        self.refresh_tab_bar()

    def _build_ui(self):
        # Main
        self.main_widget = QtWidgets.QFrame(self)
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # Search
        self.top_bar_frame = QtWidgets.QFrame(self)
        self.top_bar_layout = QtWidgets.QHBoxLayout(self.top_bar_frame)
        self.top_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.search_lineedit = QtWidgets.QLineEdit(self.top_bar_frame)
        self.search_lineedit.setPlaceholderText("Search...")
        self.refresh_presets_button = QtWidgets.QPushButton(self.top_bar_frame)
        self.refresh_presets_button.setIcon(QtGui.QIcon(":TOP_BAR_REFRESH"))
        self.refresh_presets_button.setObjectName("refresh_button")
        self.refresh_presets_button.setCursor(
            QtGui.QCursor(QtCore.Qt.PointingHandCursor)
        )
        self.refresh_presets_button.setToolTip("Refresh Prefabs")

        # Tab widget - tabs live on the left, since there are too many of
        # them to fit comfortably across the top. HorizontalTabBar keeps
        # each tab's icon/text reading normally (not rotated 90 degrees,
        # which is Qt's default for a side-mounted tab bar).
        self.tab_widget = SidebarTabWidget(self.main_widget)
        self.tab_widget.setTabBar(HorizontalTabBar(self.tab_widget))
        self.tab_widget.setTabPosition(QtWidgets.QTabWidget.West)
        tabbar = self.tab_widget.tabBar()
        tabbar.setUsesScrollButtons(True)
        tabbar.setExpanding(False)
        tabbar.setElideMode(QtCore.Qt.ElideNone)

        self.search_scroll = QtWidgets.QScrollArea(self.main_widget)
        self.search_scroll.setWidgetResizable(True)
        self.search_scroll.setVisible(False)

        self.search_tab_widget = QtWidgets.QTabWidget(self.search_scroll)
        self.search_scroll.setWidget(self.search_tab_widget)

        # Search Parts
        self.search_parts_scroll = QtWidgets.QScrollArea(self.search_tab_widget)
        self.search_parts_scroll.setWidgetResizable(True)
        self.search_parts_frame = QtWidgets.QFrame(self.search_parts_scroll)
        self.search_frame_layout = FlowLayout(parent=self.search_parts_frame)
        self.search_parts_scroll.setWidget(self.search_parts_frame)
        self.search_tab_widget.addTab(self.search_parts_scroll, "Parts")
        self.__part_flow_layouts.append(self.search_frame_layout)

        # Search presets
        self.search_presets_scroll = QtWidgets.QScrollArea(self.search_tab_widget)
        self.search_presets_scroll.setWidgetResizable(True)
        self.search_presets_frame = QtWidgets.QFrame(self.search_presets_scroll)
        self.search_presets_layout = QtWidgets.QVBoxLayout(self.search_presets_frame)
        self.search_presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.search_presets_scroll.setWidget(self.search_presets_frame)
        self.search_tab_widget.addTab(self.search_presets_scroll, "Prefabs")

        # Thumbnail size / view mode bar, similar to a file browser.
        self.thumbnail_size_frame = QtWidgets.QFrame(self.main_widget)
        self.thumbnail_size_frame.setObjectName("ThumbnailSizeBar")
        self.thumbnail_size_layout = QtWidgets.QHBoxLayout(self.thumbnail_size_frame)
        self.thumbnail_size_layout.setContentsMargins(6, 4, 6, 4)
        self.thumbnail_size_list_label = QtWidgets.QLabel(
            "List", self.thumbnail_size_frame
        )
        self.thumbnail_size_list_label.setObjectName("ThumbnailSizeLabel")
        self.thumbnail_size_grid_label = QtWidgets.QLabel(
            "Grid", self.thumbnail_size_frame
        )
        self.thumbnail_size_grid_label.setObjectName("ThumbnailSizeLabel")
        self.thumbnail_size_slider = QtWidgets.QSlider(
            QtCore.Qt.Horizontal, self.thumbnail_size_frame
        )
        self.thumbnail_size_slider.setObjectName("ThumbnailSizeSlider")
        self.thumbnail_size_slider.setMinimum(0)
        self.thumbnail_size_slider.setMaximum(len(THUMBNAIL_SIZE_STEPS))
        self.thumbnail_size_slider.setValue(self.__thumbnail_size_step)
        self.thumbnail_size_slider.setFixedWidth(160)
        self.thumbnail_size_slider.setToolTip(
            "Thumbnail size (drag to the left for a list view)"
        )
        self.thumbnail_size_layout.addStretch()
        self.thumbnail_size_layout.addWidget(self.thumbnail_size_list_label)
        self.thumbnail_size_layout.addWidget(self.thumbnail_size_slider)
        self.thumbnail_size_layout.addWidget(self.thumbnail_size_grid_label)

    def refresh_search(self):
        with contexts.block_render(self):
            with contexts.WaitCursor():
                search = self.search_lineedit.text().lower()
                if not search or len(search) <= 2:
                    self.tab_widget.setVisible(True)
                    self.search_scroll.setVisible(False)
                    return
                self.tab_widget.setVisible(False)
                self.search_scroll.setVisible(True)

                # Build a search widget for any newly-matching part that
                # doesn't have one yet - see _ensure_search_item_widget.
                for item_id, nice_name in self.__search_item_data.items():
                    if search in item_id.lower() or search in nice_name.lower():
                        self._ensure_search_item_widget(item_id)

                for data_pack in [self.__search_buttons, self.__preset_search_buttons]:
                    for button_data in data_pack.values():
                        match = (
                            search in button_data["search_id"]
                            or search in button_data["search_label"]
                        )
                        button_data["widget"].setVisible(match)

    def _thumbnail_view_for_step(self, step):
        if step <= 0:
            return "list", THUMBNAIL_SIZE_STEPS[0]
        index = min(step, len(THUMBNAIL_SIZE_STEPS)) - 1
        return "grid", THUMBNAIL_SIZE_STEPS[index]

    def _configure_item_widget(self, item_widget):
        view_mode, thumbnail_size = self._thumbnail_view_for_step(
            self.__thumbnail_size_step
        )
        item_widget.set_thumbnail_size(thumbnail_size)
        item_widget.set_view_mode(view_mode)

    def _ensure_search_item_widget(self, item_id):
        """Builds item_id's search-tab widget the first time it's actually
        needed (a search that matches it), instead of generate_contents
        building one eagerly for every part regardless of whether the user
        ever searches - confirmed by profiling to be half of all part
        widgets built at startup. Returns the existing widget on every
        call after the first."""
        existing = self.__search_buttons.get(item_id)
        if existing is not None:
            return existing["widget"]

        nice_name = self.__search_item_data.get(item_id)
        if nice_name is None:
            return None

        search_item_widget = Item(
            item_id=item_id,
            label=nice_name,
            parent=self.search_parts_frame,
        )
        self.search_frame_layout.addWidget(search_item_widget)
        search_item_widget.clicked.connect(
            partial(self.send_part_command_to_blender, item_id)
        )
        search_item_widget.varClicked.connect(self.send_part_command_to_blender)
        self.attach_favourites_menu(search_item_widget, item_id)
        self._configure_item_widget(search_item_widget)
        for variant_id, variant_nice_name in self.__variants_by_base.get(item_id, []):
            search_item_widget.add_variant(variant_id, variant_nice_name)

        self.__search_buttons[item_id] = {
            "widget": search_item_widget,
            "search_id": item_id.lower(),
            "search_label": nice_name.lower(),
        }
        # _apply_thumbnail_view_settings (the thumbnail-size slider) walks
        # every widget in here, so a widget built after that has already
        # run once needs to be added too, not just the main-grid one
        # generate_contents put there.
        self.__item_widgets.setdefault(item_id, []).append(search_item_widget)
        return search_item_widget

    def set_thumbnail_size_step(self, step):
        if step == self.__thumbnail_size_step:
            return
        self.__thumbnail_size_step = step
        self.__settings.set_thumbnail_size_step(step)
        self._apply_thumbnail_view_settings()

    def _on_thumbnail_size_slider_changed(self, value):
        if self.thumbnail_size_slider.isSliderDown():
            # Live drag - wait for release before doing the expensive
            # relayout of every part item.
            return
        self.set_thumbnail_size_step(value)

    def _on_thumbnail_size_slider_released(self):
        self.set_thumbnail_size_step(self.thumbnail_size_slider.value())

    def _apply_thumbnail_view_settings(self):
        view_mode, thumbnail_size = self._thumbnail_view_for_step(
            self.__thumbnail_size_step
        )
        for widgets in self.__item_widgets.values():
            for item_widget in widgets:
                item_widget.set_thumbnail_size(thumbnail_size)
                item_widget.set_view_mode(view_mode)
        for item_widget in self.__favourite_item_widgets:
            item_widget.set_thumbnail_size(thumbnail_size)
            item_widget.set_view_mode(view_mode)
        for flow_layout in self.__part_flow_layouts:
            flow_layout.set_list_mode(view_mode == "list")

    def generate_favourites(self):
        # Main Category
        scroll_frame = QtWidgets.QScrollArea(self)
        scroll_frame.setWidgetResizable(True)
        frame = QtWidgets.QFrame(scroll_frame)
        scroll_frame.setWidget(frame)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_widget.addTab(
            scroll_frame,
            _tinted_icon(":FAVOURITES", TAB_ICON_COLOR_FAVOURITES),
            "Favourites",
        )

        self.favourites_frame = CollapsableFrame(label="Favourites", parent=frame)
        self.favourites_frame.setProperty("partList", True)
        layout.addWidget(self.favourites_frame)
        self.__part_flow_layouts.append(self.favourites_frame.inner_frame_layout)

        info_frame = QtWidgets.QFrame(frame)
        info_frame.setObjectName("InfoFrame")
        info_layout = QtWidgets.QHBoxLayout(info_frame)
        info_label = QtWidgets.QLabel(
            """Right click items to add or remove from favourites.

Right click on a tab to pin it to the top of the tab bar.""",
            info_frame,
        )
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_label.setObjectName("InfoLabel")
        info_layout.addWidget(info_label)
        layout.addWidget(info_frame)

        self.refresh_favourites()

    def refresh_favourites(self):
        self.__fav_widgets = {}
        self.__favourite_item_widgets = []
        browser_data = parts_definition.get_part_definition()
        # --- Clear layout ---
        self.favourites_frame.clear()

        # --- Add new widgets ---
        for favourite in self.__settings.get_favourites():
            item_widget = Item(
                item_id=favourite,
                label=NICE_NAME_DATA.get(favourite, favourite),
                parent=self.favourites_frame,
            )
            self.favourites_frame.addWidget(item_widget)
            item_widget.clicked.connect(
                partial(self.send_part_command_to_blender, favourite)
            )
            item_widget.varClicked.connect(self.send_part_command_to_blender)
            self.attach_favourites_menu(item_widget, favourite, expanded=True)
            self.__fav_widgets[favourite] = [
                item_widget,
            ]
            self.__favourite_item_widgets.append(item_widget)
            self._configure_item_widget(item_widget)

        # Add Variants
        for category_title, category_data in browser_data.items():
            if not category_data:
                continue
            # Sub Categories
            for sub_category_title, items in category_data.items():
                for item_data in items:
                    item = item_data["id"]
                    nice_name = item_data["nice_name"]
                    variant_of = item_data["variantOf"]
                    if variant_of != "None":
                        variant_key = variant_of[1:]
                        if variant_key in self.__fav_widgets:
                            widgets = self.__fav_widgets[variant_key]
                            for widget in widgets:
                                widget.add_variant(item, nice_name)

    def generate_contents(self):
        browser_data = parts_definition.get_part_definition()
        self.__browser_data = browser_data

        # Variants index and the search index, both as pure data,
        # independent of any widget existing yet - built once here so a
        # category built lazily later (_ensure_category_tab_built) and a
        # search widget built lazily (_ensure_search_item_widget) can each
        # wire their own items' variants at creation time, however late
        # that turns out to be, rather than needing a second pass over
        # every category's widgets once they're all built - which is what
        # used to force every category to be built eagerly in the first
        # place. __search_item_data in particular has to be built for
        # *every* part here regardless of category - search needs to find
        # a part whether or not its category tab has ever been opened, so
        # unlike __item_widgets, this index can't itself be built lazily
        # per category without breaking search for anything in a category
        # not yet visited.
        for category_title, category_data in browser_data.items():
            if not category_data:
                continue
            for sub_category_title, items in category_data.items():
                for item_data in items:
                    if item_data["showInDrawer"] == "True" and isinstance(
                        item_data["id"], str
                    ):
                        self.__search_item_data[item_data["id"]] = item_data["nice_name"]

                    variant_of = item_data["variantOf"]
                    if variant_of != "None":
                        variant_key = variant_of[1:]
                        self.__variants_by_base.setdefault(variant_key, []).append(
                            (item_data["id"], item_data["nice_name"])
                        )

        # Add Categories - just the empty tab/scroll/frame container for
        # each one here; the actual contents (CollapsableFrame sections +
        # Item widgets) are built on first visit, by
        # _ensure_category_tab_built, not eagerly for every category
        # regardless of whether the user ever opens it - confirmed by
        # profiling to be the largest single cost at launch (~1.2s across
        # all 16 categories' ~1470 part widgets).
        for category_title, category_data in browser_data.items():
            scroll_frame = QtWidgets.QScrollArea(self)
            scroll_frame.setWidgetResizable(True)
            frame = QtWidgets.QFrame(scroll_frame)
            scroll_frame.setWidget(frame)
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setAlignment(QtCore.Qt.AlignTop)
            self.tab_widget.addTab(scroll_frame, category_title)
            self.__category_frames[category_title] = (frame, layout)
            if not category_data:
                self.__category_tab_built.add(category_title)  # nothing to build

        # Add Presets.
        scroll_frame = QtWidgets.QScrollArea(self)
        scroll_frame.setWidgetResizable(True)
        self.presets_frame = QtWidgets.QFrame(scroll_frame)
        scroll_frame.setWidget(self.presets_frame)
        self.presets_layout = QtWidgets.QVBoxLayout(self.presets_frame)
        self.presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_widget.addTab(scroll_frame, "Prefabs")
        self.generate_presets()

        self._build_prefab_share_tab()

    def _ensure_category_tab_built(self, category_title):
        """Builds category_title's CollapsableFrame sections and Item
        widgets the first time its tab is actually opened - see
        generate_contents, which only builds the empty tab container for
        every category up front. A no-op on every call after the first."""
        if category_title in self.__category_tab_built:
            return
        self.__category_tab_built.add(category_title)

        category_data = self.__browser_data.get(category_title)
        if not category_data:
            return
        frame, layout = self.__category_frames[category_title]
        # _apply_thumbnail_view_settings only runs when the slider actually
        # changes, so a category built after that (any category not yet
        # open the last time it ran - which, with lazy building, is most
        # of them) needs its own flow layout put in the current view mode
        # itself, here, rather than staying stuck on FlowLayout's grid-mode
        # default regardless of what the slider is actually set to.
        view_mode, _ = self._thumbnail_view_for_step(self.__thumbnail_size_step)

        for sub_category_title, items in category_data.items():
            title_label = CollapsableFrame(label=sub_category_title, parent=frame)
            title_label.setProperty("partList", True)
            layout.addWidget(title_label)
            title_label.inner_frame_layout.set_list_mode(view_mode == "list")
            self.__part_flow_layouts.append(title_label.inner_frame_layout)
            if not items:
                continue
            for item_data in items:
                item = item_data["id"]
                show_in_drawer = item_data["showInDrawer"]
                nice_name = item_data["nice_name"]
                if show_in_drawer == "True" and isinstance(item, str):
                    item_widget = Item(
                        item_id=item,
                        label=nice_name,
                        parent=title_label,
                    )
                    title_label.addWidget(item_widget)
                    item_widget.clicked.connect(
                        partial(self.send_part_command_to_blender, item)
                    )
                    item_widget.varClicked.connect(self.send_part_command_to_blender)
                    self.attach_favourites_menu(item_widget, item)
                    self._configure_item_widget(item_widget)
                    for variant_id, variant_nice_name in self.__variants_by_base.get(
                        item, []
                    ):
                        item_widget.add_variant(variant_id, variant_nice_name)

                    # The search-tab widget is built separately, on demand,
                    # by _ensure_search_item_widget (__search_item_data is
                    # already populated for every part up front in
                    # generate_contents, independent of category-build
                    # state - see the comment there). setdefault+append
                    # rather than a plain assignment because a search for
                    # this part could already have built its search-tab
                    # widget before this category was ever opened.
                    self.__item_widgets.setdefault(item, []).append(item_widget)

    def _build_prefab_share_tab(self):
        scroll_frame = QtWidgets.QScrollArea(self)
        scroll_frame.setWidgetResizable(True)
        frame = QtWidgets.QFrame(scroll_frame)
        scroll_frame.setWidget(frame)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        self.prefab_share_intro_frame = QtWidgets.QFrame(frame)
        self.prefab_share_intro_frame.setObjectName("PrefabShareIntro")
        intro_layout = QtWidgets.QHBoxLayout(self.prefab_share_intro_frame)
        intro_layout.setContentsMargins(10, 8, 10, 8)
        intro_layout.setSpacing(10)
        self.prefab_share_intro_label = QtWidgets.QLabel(
            "Prefabs here are shared by the community over on Discord. "
            "Join the server to browse the full collection, chat with "
            "other builders, and upload your own creations.",
            self.prefab_share_intro_frame,
        )
        self.prefab_share_intro_label.setObjectName("PrefabShareIntroLabel")
        self.prefab_share_intro_label.setWordWrap(True)
        self.prefab_share_join_discord_button = QtWidgets.QPushButton(
            "Join Discord", self.prefab_share_intro_frame
        )
        self.prefab_share_join_discord_button.setObjectName("PrefabShareDiscord")
        self.prefab_share_join_discord_button.setCursor(
            QtGui.QCursor(QtCore.Qt.PointingHandCursor)
        )
        intro_layout.addWidget(self.prefab_share_intro_label, 1)
        intro_layout.addWidget(
            self.prefab_share_join_discord_button, 0, QtCore.Qt.AlignVCenter
        )
        layout.addWidget(self.prefab_share_intro_frame)

        toolbar = QtWidgets.QHBoxLayout()
        self.prefab_share_search = QtWidgets.QLineEdit(frame)
        self.prefab_share_search.setObjectName("PrefabShareSearch")
        self.prefab_share_search.setPlaceholderText("Search shared prefabs...")
        self.prefab_share_sort = QtWidgets.QComboBox(frame)
        self.prefab_share_sort.setObjectName("PrefabShareSort")
        for label, value in PREFAB_SHARE_SORT_OPTIONS:
            self.prefab_share_sort.addItem(label, value)
        self.prefab_share_refresh_button = QtWidgets.QPushButton("Refresh", frame)
        toolbar.addWidget(QtWidgets.QLabel("Sort By", frame))
        toolbar.addWidget(self.prefab_share_sort)
        toolbar.addWidget(QtWidgets.QLabel("Search", frame))
        toolbar.addWidget(self.prefab_share_search, 1)
        toolbar.addWidget(self.prefab_share_refresh_button)

        self.prefab_share_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, frame)
        self.prefab_share_results_scroll = QtWidgets.QScrollArea(
            self.prefab_share_splitter
        )
        self.prefab_share_results_scroll.setWidgetResizable(True)
        self.prefab_share_results_content = QtWidgets.QFrame(
            self.prefab_share_results_scroll
        )
        self.prefab_share_results_layout = QtWidgets.QVBoxLayout(
            self.prefab_share_results_content
        )
        self.prefab_share_results_layout.setContentsMargins(0, 0, 0, 0)
        self.prefab_share_results_layout.setSpacing(6)
        self.prefab_share_frame = QtWidgets.QFrame(
            self.prefab_share_results_content
        )
        self.prefab_share_layout = FlowLayout(parent=self.prefab_share_frame)
        self.prefab_share_results_scroll.setWidget(self.prefab_share_results_content)

        self.prefab_share_details_scroll = QtWidgets.QScrollArea(
            self.prefab_share_splitter
        )
        self.prefab_share_details_scroll.setWidgetResizable(True)
        self.prefab_share_details_scroll.setMinimumWidth(220)
        self.prefab_share_details_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        # Pin the vertical scrollbar on permanently. The thumbnail inside
        # this panel is width-driven (16:9, recomputed on resize), so if
        # the scrollbar were only shown "as needed" it would toggle in and
        # out as the thumbnail's height changes, which changes the
        # viewport width, which changes the thumbnail's computed height
        # again - an unbounded resize/layout feedback loop that crashes
        # with a stack overflow. Reserving the scrollbar's space always
        # keeps the viewport width stable and breaks that loop.
        self.prefab_share_details_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOn
        )
        self.prefab_share_details = QtWidgets.QFrame(
            self.prefab_share_details_scroll
        )
        self.prefab_share_details.setObjectName("PrefabShareDetails")
        self.prefab_share_details_scroll.setWidget(self.prefab_share_details)
        details_layout = QtWidgets.QVBoxLayout(self.prefab_share_details)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(6)

        # Thumbnail, with the Discord button directly beneath it. Fixed
        # size - it does not stretch when the details pane is resized,
        # only the text/controls below it do.
        self.prefab_share_details_thumbnail = AspectFitThumbnail(
            "Select a shared prefab", self.prefab_share_details
        )
        self.prefab_share_details_thumbnail.setObjectName("PrefabShareDetailsThumbnail")
        self.prefab_share_details_thumbnail.apply_width(
            PREFAB_SHARE_DETAILS_THUMBNAIL_WIDTH
        )
        self.prefab_share_discord_button = QtWidgets.QPushButton(
            "Open in Discord", self.prefab_share_details
        )
        self.prefab_share_discord_button.setObjectName("PrefabShareDiscord")

        # Name / author block, tightly spaced and left-aligned.
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        self.prefab_share_details_name = ElidedLabel(self.prefab_share_details)
        self.prefab_share_details_name.setObjectName("PrefabShareDetailsName")
        self.prefab_share_details_name.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.prefab_share_details_author = ElidedLabel(self.prefab_share_details)
        self.prefab_share_details_author.setObjectName("PrefabShareDetailsAuthor")
        self.prefab_share_details_author.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        header_layout.addWidget(self.prefab_share_details_name)
        header_layout.addWidget(self.prefab_share_details_author)

        # Attachment selector (only shown when a post has more than one
        # compatible file) followed by the Import button - the import
        # button sits directly below the selector when it is visible, and
        # in the same place when it is not.
        self.prefab_share_details_attachment_combo = QtWidgets.QComboBox(
            self.prefab_share_details
        )
        self.prefab_share_details_attachment_combo.setObjectName(
            "PrefabShareAttachmentCombo"
        )
        self.prefab_share_details_attachment_combo.setVisible(False)
        self.prefab_share_import_button = QtWidgets.QPushButton(
            "Import Prefab", self.prefab_share_details
        )
        self.prefab_share_import_button.setObjectName("PrefabShareImport")

        self.prefab_share_details_content = QtWidgets.QTextEdit(
            self.prefab_share_details
        )
        self.prefab_share_details_content.setObjectName("PrefabShareDetailsContent")
        self.prefab_share_details_content.setReadOnly(True)
        self.prefab_share_details_content.setPlaceholderText(
            "Select a prefab to view its Discord post."
        )
        self.prefab_share_details_content.setMinimumHeight(160)
        self.prefab_share_details_content.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        details_layout.addWidget(
            self.prefab_share_details_thumbnail, 0, QtCore.Qt.AlignHCenter
        )
        details_layout.addWidget(self.prefab_share_discord_button)
        details_layout.addLayout(header_layout)
        details_layout.addWidget(self.prefab_share_details_attachment_combo)
        details_layout.addWidget(self.prefab_share_import_button)
        details_layout.addWidget(self.prefab_share_details_content, 1)
        details_layout.addStretch()
        # The details pane keeps a fixed width when the window itself is
        # resized - all the extra/removed space goes to the results grid.
        # It only changes size when the user explicitly drags the handle.
        self.prefab_share_splitter.setStretchFactor(0, 1)
        self.prefab_share_splitter.setStretchFactor(1, 0)
        self.prefab_share_splitter.setSizes([640, 320])
        self.prefab_share_splitter.setChildrenCollapsible(False)

        self.prefab_share_load_more_button = QtWidgets.QPushButton(
            "Load More", frame
        )
        self.prefab_share_load_more_button.setObjectName("PrefabShareLoadMore")
        self.prefab_share_load_more_button.setVisible(False)
        self.prefab_share_results_layout.addWidget(self.prefab_share_frame)
        self.prefab_share_results_layout.addWidget(self.prefab_share_load_more_button)
        self.prefab_share_results_layout.addStretch()
        layout.addLayout(toolbar)
        layout.addWidget(self.prefab_share_splitter, 1)
        self.tab_widget.addTab(scroll_frame, "prefab-share")

        self.prefab_share_refresh_button.clicked.connect(self.refresh_prefab_share)
        self.prefab_share_search.returnPressed.connect(self.refresh_prefab_share)
        self.prefab_share_sort.currentIndexChanged.connect(self.refresh_prefab_share)
        self.prefab_share_load_more_button.clicked.connect(self.load_more_prefab_share)
        self.prefab_share_import_button.clicked.connect(
            self._import_selected_prefab_share
        )
        self.prefab_share_discord_button.clicked.connect(
            self._open_selected_prefab_share_discord
        )
        self.prefab_share_join_discord_button.clicked.connect(
            self._open_prefab_share_discord_invite
        )
        self.prefab_share_details_attachment_combo.currentIndexChanged.connect(
            self._on_prefab_share_attachment_changed
        )
        self.prefab_share_catalog_loaded.connect(self._populate_prefab_share)
        self.prefab_share_post_loaded.connect(self._populate_prefab_share_post)
        self.prefab_share_post_failed.connect(self._handle_prefab_share_post_failure)
        self.prefab_share_thumbnail_loaded.connect(self._set_prefab_share_thumbnail)
        self.prefab_share_prefab_loaded.connect(self._import_prefab_share_prefab)
        self.prefab_share_request_failed.connect(self._show_prefab_share_error)
        self.prefab_share_layout.heightChanged.connect(
            self._resize_prefab_share_results
        )
        self._clear_prefab_share_details()
        self.prefab_share_status.setText(
            "Select #prefab-share to load shared prefabs."
        )

    @staticmethod
    def _download_bytes(url):
        request = urllib.request.Request(url, headers={"User-Agent": "NMS-Base-Builder"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()

    @staticmethod
    def _prefab_share_record(thread):
        author = thread.get("creator") or {}
        return {
            "id": thread.get("id", ""),
            "name": thread.get("name", "Untitled Prefab"),
            "author": author.get("displayName") or author.get("username") or "Unknown author",
            "attachment": None,
            "attachments": [],
            "post_resolved": False,
            "thumbnail_url": "",
        }

    def refresh_prefab_share(self):
        self.__prefab_share_query_token += 1
        self._clear_prefab_share_cards()
        self._clear_prefab_share_details()
        self.__prefab_share_next_cursor = None
        self.__prefab_share_loaded_thread_ids = set()
        self.__prefab_share_card_order = []
        self.__prefab_share_next_card_index = 0
        self.prefab_share_load_more_button.setVisible(False)
        self._load_prefab_share_page()

    def load_more_prefab_share(self):
        if self.__prefab_share_next_cursor:
            self._load_prefab_share_page(self.__prefab_share_next_cursor)

    def _load_prefab_share_page(self, cursor=None):
        self.prefab_share_refresh_button.setEnabled(False)
        self.prefab_share_load_more_button.setEnabled(False)
        self.prefab_share_status.setText("Loading shared prefabs...")
        query = {
            "limit": "20",
            "sort": self.prefab_share_sort.currentData(),
            "search": self.prefab_share_search.text().strip(),
        }
        if cursor:
            query["cursor"] = cursor
        query_token = self.__prefab_share_query_token

        def load_catalog():
            try:
                url = PREFAB_SHARE_URL.rstrip("/") + "/threads?"
                url += urllib.parse.urlencode(query)
                payload = json.loads(
                    self._download_bytes(url).decode("utf-8")
                )
                self.prefab_share_catalog_loaded.emit({
                    "payload": payload,
                    "query_token": query_token,
                })
            except Exception as error:
                self.prefab_share_request_failed.emit("Unable to load #prefab-share: {}".format(error))

        threading.Thread(target=load_catalog, daemon=True).start()

    def _clear_prefab_share_cards(self):
        while self.prefab_share_layout.count():
            item = self.prefab_share_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.__prefab_share_cards = {}

    def _resize_prefab_share_results(self, height):
        self.prefab_share_frame.setFixedHeight(max(height, 1))

    def _clear_prefab_share_details(self):
        self.__prefab_share_selected_record = None
        self.prefab_share_import_button.setEnabled(False)
        self.prefab_share_discord_button.setEnabled(False)
        self.prefab_share_details_thumbnail.clear_thumbnail("Select a shared prefab")
        self.prefab_share_details_name.setText("")
        self.prefab_share_details_author.setText("")
        self.prefab_share_details_content.clear()
        self._populate_attachment_selector(None)

    def _populate_prefab_share(self, result):
        if result["query_token"] != self.__prefab_share_query_token:
            return
        payload = result["payload"]
        records = [
            self._prefab_share_record(thread)
            for thread in payload.get("threads", [])
            if thread.get("id") not in self.__prefab_share_loaded_thread_ids
        ]
        for record in records:
            record["query_token"] = self.__prefab_share_query_token
        self.__prefab_share_card_order.extend(records)
        self.__prefab_share_loaded_thread_ids.update(
            record["id"] for record in records
        )
        self.__prefab_share_next_cursor = payload.get("nextCursor")
        self.prefab_share_status.setText("Checking {} shared threads...".format(len(records)))
        self.prefab_share_refresh_button.setEnabled(True)
        self.prefab_share_load_more_button.setVisible(
            bool(self.__prefab_share_next_cursor)
        )
        self.prefab_share_load_more_button.setEnabled(
            bool(self.__prefab_share_next_cursor)
        )
        for record in records:
            self._load_prefab_share_post(record)

    def _load_prefab_share_post(self, record):
        thread_id = record["id"]
        if thread_id in self.__prefab_share_posts:
            self.prefab_share_post_loaded.emit(
                record, self.__prefab_share_posts[thread_id]
            )
            return
        if thread_id in self.__prefab_share_post_requests:
            return
        # A Discord message's content essentially never changes once
        # posted, so a cached copy from a previous session is treated as
        # permanently valid - Refresh only re-queries the thread catalog
        # for new/changed threads, it does not bypass this.
        cached_message = _load_cached_prefab_share_message(thread_id)
        if cached_message is not None:
            self.__prefab_share_posts[thread_id] = cached_message
            self.prefab_share_post_loaded.emit(record, cached_message)
            return
        self.__prefab_share_post_requests.add(thread_id)

        def load_post():
            try:
                url = PREFAB_SHARE_URL.rstrip("/") + "/post?threadId=" + thread_id
                payload = json.loads(self._download_bytes(url).decode("utf-8"))
                message = payload.get("message") or {}
                _save_cached_prefab_share_message(thread_id, message)
                self.prefab_share_post_loaded.emit(record, message)
            except Exception as error:
                self.prefab_share_post_failed.emit(
                    record,
                    "Unable to load {}: {}".format(record["name"], error)
                )

        threading.Thread(target=load_post, daemon=True).start()

    def _populate_prefab_share_post(self, record, message):
        if record["query_token"] != self.__prefab_share_query_token:
            return
        thread_id = record["id"]
        self.__prefab_share_post_requests.discard(thread_id)
        self.__prefab_share_posts[thread_id] = message
        attachments = message.get("attachments") or []
        matching_attachments = [
            attachment
            for attachment in attachments
            if os.path.splitext(attachment.get("filename", ""))[1].lower()
            in PREFAB_SHARE_EXTENSIONS
        ]
        record["attachments"] = matching_attachments
        record["attachment"] = matching_attachments[0] if matching_attachments else None
        thumbnail_attachment = next(
            (
                attachment
                for attachment in attachments
                if attachment.get("contentType", "").lower().startswith("image/")
            ),
            None,
        )
        record["thumbnail_url"] = (
            thumbnail_attachment.get("url") if thumbnail_attachment else ""
        )
        author = message.get("author") or {}
        record["author"] = (
            author.get("displayName") or author.get("username") or record["author"]
        )
        record["post_resolved"] = True
        self._append_resolved_prefab_share_cards()

    def _handle_prefab_share_post_failure(self, record, message):
        if record["query_token"] != self.__prefab_share_query_token:
            return
        self.__prefab_share_post_requests.discard(record["id"])
        record["post_resolved"] = True
        self._append_resolved_prefab_share_cards()
        self.prefab_share_status.setText(message)

    def _append_resolved_prefab_share_cards(self):
        while self.__prefab_share_next_card_index < len(
            self.__prefab_share_card_order
        ):
            record = self.__prefab_share_card_order[
                self.__prefab_share_next_card_index
            ]
            if not record["post_resolved"]:
                return
            self.__prefab_share_next_card_index += 1
            if not record["attachment"]:
                continue
            card = PrefabShareCard(record, parent=self.prefab_share_frame)
            card.clicked.connect(self._select_prefab_share_card)
            self.prefab_share_layout.addWidget(card)
            self.__prefab_share_cards[record["id"]] = card
            if record["thumbnail_url"]:
                self._load_prefab_share_thumbnail(record)

    def _load_prefab_share_thumbnail(self, record):
        thread_id = record["id"]
        cached_image_data = _load_cached_prefab_share_thumbnail(thread_id)
        if cached_image_data is not None:
            self.prefab_share_thumbnail_loaded.emit(record, cached_image_data)
            return

        def load_thumbnail():
            try:
                image_data = self._download_bytes(record["thumbnail_url"])
                _save_cached_prefab_share_thumbnail(thread_id, image_data)
                self.prefab_share_thumbnail_loaded.emit(record, image_data)
            except Exception:
                pass

        threading.Thread(target=load_thumbnail, daemon=True).start()

    def _set_prefab_share_thumbnail(self, record, image_data):
        self.__prefab_share_thumbnail_data[record["id"]] = image_data
        card = self.__prefab_share_cards.get(record["id"])
        if card:
            card.set_thumbnail(image_data)
        if self.__prefab_share_selected_record is record:
            self._set_prefab_share_details_thumbnail(image_data)

    def _select_prefab_share_card(self, record):
        if record["id"] not in self.__prefab_share_posts:
            self.prefab_share_status.setText("Loading {}...".format(record["name"]))
            self._load_prefab_share_post(record)
            return
        self.__prefab_share_selected_record = record
        message = self.__prefab_share_posts[record["id"]]
        self.prefab_share_details_name.setText(record["name"])
        self.prefab_share_details_author.setText("by {}".format(record["author"]))
        self.prefab_share_details_content.setPlainText(message.get("content") or "")
        self._populate_attachment_selector(record)
        self.prefab_share_discord_button.setEnabled(bool(record.get("id")))
        self.prefab_share_details_thumbnail.clear_thumbnail("Loading preview...")
        image_data = self.__prefab_share_thumbnail_data.get(record["id"])
        if image_data:
            self._set_prefab_share_details_thumbnail(image_data)
        elif record["thumbnail_url"]:
            self._load_prefab_share_thumbnail(record)
        else:
            self.prefab_share_details_thumbnail.clear_thumbnail("No preview available")

    def _populate_attachment_selector(self, record):
        combo = self.prefab_share_details_attachment_combo
        combo.blockSignals(True)
        combo.clear()
        attachments = (record or {}).get("attachments") or []
        if len(attachments) > 1:
            for attachment in attachments:
                combo.addItem(
                    attachment.get("filename", "Attachment"), attachment
                )
            combo.setCurrentIndex(0)
            record["attachment"] = attachments[0]
            combo.setVisible(True)
        else:
            combo.setVisible(False)
        combo.blockSignals(False)
        self.prefab_share_import_button.setEnabled(
            bool(record and record.get("attachment"))
        )

    def _on_prefab_share_attachment_changed(self, index):
        record = self.__prefab_share_selected_record
        if not record:
            return
        attachment = self.prefab_share_details_attachment_combo.itemData(index)
        if attachment:
            record["attachment"] = attachment
        self.prefab_share_import_button.setEnabled(bool(record["attachment"]))

    def _set_prefab_share_details_thumbnail(self, image_data):
        self.prefab_share_details_thumbnail.set_image_data(image_data)

    def _import_selected_prefab_share(self):
        if self.__prefab_share_selected_record:
            self._load_prefab_share_attachment(self.__prefab_share_selected_record)

    def _open_selected_prefab_share_discord(self):
        record = self.__prefab_share_selected_record
        if not record:
            return
        if (
            PREFAB_SHARE_DISCORD_GUILD_ID
            and PREFAB_SHARE_DISCORD_PARENT_CHANNEL_ID
            and record.get("id")
        ):
            # Deep-links straight to the thread (post) itself, e.g.
            # https://discord.com/channels/<guild>/<forum-channel>/threads/<thread-id>
            url = "https://discord.com/channels/{}/{}/threads/{}".format(
                PREFAB_SHARE_DISCORD_GUILD_ID,
                PREFAB_SHARE_DISCORD_PARENT_CHANNEL_ID,
                record["id"],
            )
        else:
            url = PREFAB_SHARE_DISCORD_INVITE_URL
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _open_prefab_share_discord_invite(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(PREFAB_SHARE_DISCORD_INVITE_URL))

    def _load_prefab_share_attachment(self, record):
        if not record["attachment"]:
            self._show_prefab_share_error(
                "{} has no supported prefab attachment.".format(record["name"])
            )
            return
        self.prefab_share_status.setText("Downloading {}...".format(record["name"]))

        def load_attachment():
            try:
                self.prefab_share_prefab_loaded.emit(record, self._download_bytes(record["attachment"]["url"]))
            except Exception as error:
                self.prefab_share_request_failed.emit("Unable to download {}: {}".format(record["name"], error))

        threading.Thread(target=load_attachment, daemon=True).start()

    def _import_prefab_share_prefab(self, record, attachment_data):
        try:
            prefab_data = json.loads(attachment_data.decode("utf-8-sig"))
            if isinstance(prefab_data, list):
                prefab_data = {"Objects": prefab_data}
            if not isinstance(prefab_data, dict) or not (prefab_data.get("Objects") or prefab_data.get("Prefab")):
                raise ValueError("The attachment does not contain a supported prefab object list.")

            os.makedirs(PREFAB_SHARE_CACHE_PATH, exist_ok=True)
            preset_id = self._prefab_share_preset_id(record)
            data_path = os.path.join(PREFAB_SHARE_CACHE_PATH, preset_id + ".nmsprefab")
            with open(data_path, "w", encoding="utf-8") as stream:
                json.dump(prefab_data, stream)
            self.send_prefab_share_preset_to_blender(preset_id, data_path)
            self.prefab_share_status.setText("Imported {}".format(record["name"]))
        except Exception as error:
            self._show_prefab_share_error("Unable to import {}: {}".format(record["name"], error))

    @staticmethod
    def _prefab_share_preset_id(record):
        name = "{}_{}".format(record["author"], record["name"])
        return "".join(
            character if character.isalnum() or character in " -_" else "_"
            for character in name
        ).strip(" ._") or "shared_prefab"

    def _show_prefab_share_error(self, message):
        self.prefab_share_status.setText(message)
        self.prefab_share_refresh_button.setEnabled(True)
        self.prefab_share_load_more_button.setEnabled(
            bool(self.__prefab_share_next_cursor)
        )

    def attach_favourites_menu(self, item_widget, item_id, expanded=False):
        menu = QtWidgets.QMenu()
        menu.aboutToShow.connect(
            lambda: self.update_favourites_menu(menu, item_id, expanded)
        )
        item_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        item_widget.customContextMenuRequested.connect(
            lambda pos: menu.exec_(item_widget.mapToGlobal(pos))
        )

    def update_favourites_menu(self, menu, item_id, expanded=False):
        menu.clear()
        if expanded:
            # Move left and Move right options.
            if self.__settings.can_move_left(item_id):
                action = menu.addAction("Move Left")
                action.triggered.connect(partial(self.move_favourite_left, item_id))
            if self.__settings.can_move_right(item_id):
                action = menu.addAction("Move Right")
                action.triggered.connect(partial(self.move_favourite_right, item_id))
            menu.addSeparator()

            # Bring to front/back option.
            if self.__settings.can_move_left(item_id):
                action = menu.addAction("Move to Start")
                action.triggered.connect(
                    partial(self.bring_favourite_to_front, item_id)
                )
            if self.__settings.can_move_right(item_id):
                action = menu.addAction("Move to End")
                action.triggered.connect(partial(self.send_favourite_to_back, item_id))

            menu.addSeparator()
        if item_id in self.__settings.get_favourites():
            action = menu.addAction("Remove from Favourites")
            action.triggered.connect(partial(self.remove_from_favourites, item_id))
        else:
            action = menu.addAction("Add to Favourites")
            action.triggered.connect(partial(self.add_to_favourites, item_id))

    def bring_favourite_to_front(self, item_id):
        self.__settings.bring_favourite_to_front(item_id)
        self.refresh_favourites()

    def send_favourite_to_back(self, item_id):
        self.__settings.send_favourite_to_back(item_id)
        self.refresh_favourites()

    def move_favourite_left(self, item_id):
        self.__settings.move_favourite_left(item_id)
        self.refresh_favourites()

    def move_favourite_right(self, item_id):
        self.__settings.move_favourite_right(item_id)
        self.refresh_favourites()

    def add_to_favourites(self, item_id):
        self.__settings.add_favourite(item_id)
        self.refresh_favourites()

    def remove_from_favourites(self, item_id):
        self.__settings.remove_favourite(item_id)
        self.refresh_favourites()

    def clear_presets(self):
        for preset_id, preset_data in self.__preset_search_buttons.items():
            widget = preset_data["widget"]
            widget.parent().layout().removeWidget(widget)
            widget.deleteLater()
        for _ in range(self.presets_layout.count()):
            item = self.presets_layout.itemAt(0)
            widget = item.widget()
            if widget and isinstance(widget, CollapsableFrame):
                self.presets_layout.removeWidget(widget)
                widget.deleteLater()
        self.__preset_search_buttons = {}

    def generate_presets(self):
        self.__preset_search_buttons = {}
        # Add Categories.
        categories = sorted(os.listdir(PRESET_PATH))
        for category in categories:
            full_path = os.path.join(PRESET_PATH, category)
            if os.path.isdir(full_path):
                preset_category_frame = CollapsableFrame(
                    label=category, layout="vertical", parent=self.presets_frame
                )
                self.presets_layout.addWidget(preset_category_frame)
                presets = os.listdir(full_path)
                for preset in presets:
                    self.add_preset_to_frame(preset, preset_category_frame)

        # Add un-categorized presets.
        presets = sorted(os.listdir(PRESET_PATH))
        presets = [
            item for item in presets if os.path.isfile(os.path.join(PRESET_PATH, item))
        ]
        if presets:
            preset_category_frame = CollapsableFrame(
                label="Uncategorized Prefabs",
                layout="vertical",
                parent=self.presets_frame,
            )
            self.presets_layout.addWidget(preset_category_frame)
            for preset in presets:
                self.add_preset_to_frame(preset, preset_category_frame)

    def add_preset_to_frame(self, preset, frame):
        item_id = preset.split(".")[0]
        if not item_id:
            return
        nice_label = item_id.replace("_", " ").title()
        # Add preset
        item_widget = Preset(item_id=item_id, label=nice_label, parent=frame)
        frame.addWidget(item_widget)
        item_widget.clicked.connect(partial(self.send_part_command_to_blender, item_id))
        item_widget.editClicked.connect(
            partial(self.send_edit_preset_command_to_blender, item_id)
        )
        # Add to search
        search_item_widget = Preset(
            item_id=item_id, label=nice_label, parent=self.search_presets_frame
        )
        self.search_presets_layout.addWidget(search_item_widget)
        search_item_widget.clicked.connect(
            partial(self.send_part_command_to_blender, item_id)
        )
        search_item_widget.editClicked.connect(
            partial(self.send_edit_preset_command_to_blender, item_id)
        )
        self.__preset_search_buttons[item_id] = {
            "widget": search_item_widget,
            "search_id": item_id,
            "search_label": nice_label,
        }

    def _layout_ui(self):
        self.setCentralWidget(self.main_widget)
        self.main_layout.addWidget(self.top_bar_frame)
        self.top_bar_layout.addWidget(self.search_lineedit)
        self.top_bar_layout.addWidget(self.refresh_presets_button)
        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(self.search_scroll)
        self.main_layout.addWidget(self.thumbnail_size_frame)
        # prefab_share_status itself stays (its .setText() calls are used
        # throughout the prefab-share code for status messages) - it's just
        # not added to a status bar, so QMainWindow never creates/shows one.

    def _setup_ui(self):
        self.search_lineedit.textChanged.connect(self.refresh_search)
        self.refresh_presets_button.clicked.connect(self.refresh_presets)
        self.tab_widget.currentChanged.connect(self.refresh_layouts)
        tabbar = self.tab_widget.tabBar()
        tabbar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tabbar.customContextMenuRequested.connect(self.show_tab_context_menu)
        # Re-laying out every part item/category is expensive enough that
        # doing it on every single tick of a live drag feels sluggish, so
        # it's only applied once the drag ends. Keyboard/programmatic
        # value changes (which never "drag") still apply immediately.
        self.thumbnail_size_slider.valueChanged.connect(
            self._on_thumbnail_size_slider_changed
        )
        self.thumbnail_size_slider.sliderReleased.connect(
            self._on_thumbnail_size_slider_released
        )

    def show_tab_context_menu(self, pos):
        tabbar = self.tab_widget.tabBar()

        index = tabbar.tabAt(pos)
        if index == -1:
            return  # clicked empty space

        menu = QtWidgets.QMenu()
        tab_name = tabbar.tabText(index)
        print (tab_name)
        if tab_name in ["Favourites", "Prefabs"]:
            return  # Don't allow pinning the favourites tab.
        if tab_name in self.__settings.get_pinned_tabs():
            action = menu.addAction("Unpin Tab")
            action.triggered.connect(partial(self.remove_from_pinned_tabs, tab_name))
        else:
            pin_action = menu.addAction("Pin Tab")
            pin_action.triggered.connect(partial(self.add_to_pinned_tabs, tab_name))
        action = menu.exec(tabbar.mapToGlobal(pos))

    def add_to_pinned_tabs(self, tab_name):
        self.__settings.add_pinned_tab(tab_name)
        self.refresh_tab_bar()

    def remove_from_pinned_tabs(self, tab_name):
        self.__settings.remove_pinned_tab(tab_name)
        self.refresh_tab_bar()

    def get_tab_index(self, name):
        tabbar = self.tab_widget.tabBar()
        for i in range(tabbar.count()):
            if tabbar.tabText(i) == name:
                return i
        return -1

    def _default_tab_icon(self, tab_name):
        if tab_name == "Prefabs":
            return _tinted_icon(":PACKAGE", TAB_ICON_COLOR_PREFABS)
        if tab_name == "prefab-share":
            return _tinted_icon(PREFAB_SHARE_TAB_ICON, TAB_ICON_COLOR_PREFAB_SHARE)
        return _category_tab_icon(tab_name)

    def refresh_tab_bar(self):
        tabbar = self.tab_widget.tabBar()
        all_tabs = [tabbar.tabText(i) for i in range(tabbar.count())]
        for index in range(tabbar.count()):
            tab_name = tabbar.tabText(index)
            if tab_name in ["Favourites"]:
                continue  # Don't allow pinning the favourites tab.

            if tab_name in self.__settings.get_pinned_tabs():
                tabbar.setTabIcon(index, QtGui.QIcon(":PIN"))
            else:
                tabbar.setTabIcon(index, self._default_tab_icon(tab_name))

        pinned_tabs = set(self.__settings.get_pinned_tabs())

        all_tabs = [tabbar.tabText(i) for i in range(tabbar.count())]

        pinned = sorted(
            tab
            for tab in all_tabs
            if tab in pinned_tabs and tab not in ["Favourites", "Prefabs"]
        )

        unpinned = sorted(
            tab
            for tab in all_tabs
            if tab not in pinned_tabs
            and tab not in ["Favourites", "Prefabs", "prefab-share"]
        )

        if "Prefabs" in all_tabs:
            unpinned.insert(0, "Prefabs")
        if "prefab-share" in all_tabs and "prefab-share" not in pinned_tabs:
            unpinned.insert(1, "prefab-share")

        final_order = ["Favourites"] + pinned + unpinned

        for target_index, tab_name in enumerate(final_order):
            current_index = self.get_tab_index(tab_name)

            if current_index != -1 and current_index != target_index:
                tabbar.moveTab(current_index, target_index)

    def refresh_layouts(self, tab_index):
        tab_name = self.tab_widget.tabText(tab_index)
        if tab_name == "prefab-share":
            if not self.__prefab_share_has_loaded:
                self.__prefab_share_has_loaded = True
                self.refresh_prefab_share()
        elif tab_name in self.__browser_data:
            # Same lazy-build-on-first-visit idea as prefab-share just
            # above - see _ensure_category_tab_built.
            self._ensure_category_tab_built(tab_name)
        scroll_widget = self.tab_widget.currentWidget()
        widget = scroll_widget.widget()
        layout = widget.layout()
        for idx in range(layout.count()):
            frame_item = layout.itemAt(idx)
            frame = frame_item.widget()
            if isinstance(frame, CollapsableFrame):
                frame.inner_frame_layout.update()

    def refresh_presets(self):
        self.clear_presets()
        self.generate_presets()
        self.refresh_search()

    def apply_style(self):
        with open(STYLESHEET_FILE) as stream:
            self.setStyleSheet(stream.read())

    def send_part_command_to_blender(self, item_id):
        import sys

        path = os.path.join(FILE_DIR, "..", "..").replace("\\", "/")
        if path not in sys.path:
            sys.path.insert(0, path)

        import no_mans_sky_base_builder
        import no_mans_sky_base_builder.preset as preset
        import no_mans_sky_base_builder.utils.blend_utils as blend_utils

        BUILDER = no_mans_sky_base_builder.builder.get_builder()

        selection = blend_utils.get_current_selection()

        # Build item
        if item_id in preset.Preset.get_presets():
            new_item = BUILDER.add_preset(item_id)
        else:
            new_item = BUILDER.add_part(item_id)
            if hasattr(new_item, "build_rig"):
                new_item.build_rig()

        # Make this item the selected.
        new_item.select()

        # If there was a previous selection, snap the new item to it.
        if selection:
            builder_selection = BUILDER.get_builder_object_from_bpy_object(selection)
            if builder_selection:
                new_item.snap_to(builder_selection)

    def send_prefab_share_preset_to_blender(self, preset_id, data_path):
        import sys

        path = os.path.join(FILE_DIR, "..", "..").replace("\\", "/")
        if path not in sys.path:
            sys.path.insert(0, path)

        import no_mans_sky_base_builder
        import no_mans_sky_base_builder.preset as preset
        import no_mans_sky_base_builder.utils.blend_utils as blend_utils

        BUILDER = no_mans_sky_base_builder.BUILDER
        selection = blend_utils.get_current_selection()
        new_item = preset.Preset(
            preset_id=preset_id,
            data_path=data_path,
            builder_object=BUILDER,
        )
        new_item.select()

        if selection:
            builder_selection = BUILDER.get_builder_object_from_bpy_object(selection)
            if builder_selection:
                new_item.snap_to(builder_selection)

    def send_edit_preset_command_to_blender(self, item_id):
        import sys

        path = os.path.join(FILE_DIR, "..", "..").replace("\\", "/")
        if path not in sys.path:
            sys.path.insert(0, path)

        import bpy
        import no_mans_sky_base_builder
        import no_mans_sky_base_builder.preset as preset
        import no_mans_sky_base_builder.utils.blend_utils as blend_utils

        BUILDER = no_mans_sky_base_builder.builder.get_builder()

        nms_tool = bpy.context.scene.nms_base_tool
        if item_id in preset.Preset.get_presets():
            nms_tool.new_file()
            preset.Preset(
                preset_id=item_id,
                builder_object=BUILDER,
                create_control=False,
                apply_shader=False,
                build_rigs=True,
            )
            BUILDER.build_rigs()
            BUILDER.optimise_control_points()

    def sizeHint(self):
        return QtCore.QSize(1000, 1000)


qt_app = None
qt_window = None
qt_thread = None
IS_LINUX = sys.platform.startswith("linux")


def qt_event_loop():
    global qt_app
    if qt_app is None:
        return None
    # Only process pending Qt events for a very short time slice.
    # This prevents heavy resize/event storms from blocking Blender.
    qt_app.processEvents(QtCore.QEventLoop.AllEvents, 1)
    return 0.01


def qt_thread_func():
    global qt_app
    qt_app.exec_()


def load():
    global qt_app, qt_window, qt_thread
    if not QtWidgets.QApplication.instance():
        qt_app = QtWidgets.QApplication(sys.argv)
    else:
        qt_app = QtWidgets.QApplication.instance()
    qt_window = AssetBrowser()
    qt_window.show()

    if IS_LINUX:
        # Qt objects were created by Blender's main thread.  Qt requires their
        # event loop to run on that same thread; calling exec_() from a Python
        # worker happens to work on Windows but is rejected on Linux.
        # Let Blender schedule short Qt event-processing slices instead.
        if not bpy.app.timers.is_registered(qt_event_loop):
            bpy.app.timers.register(qt_event_loop, first_interval=0.01)
        return

    # Preserve the existing Windows behaviour, where the separate Qt event
    # loop has historically coexisted with Blender without blocking its UI.
    qt_thread = threading.Thread(target=qt_thread_func, daemon=True)
    qt_thread.start()

