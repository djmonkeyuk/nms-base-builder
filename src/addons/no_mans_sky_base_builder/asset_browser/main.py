import ctypes
import json
import os
import sys
import tempfile
import time
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
USER_PATH = os.path.join(os.path.expanduser("~"), "NoMansSkyBaseBuilder")
PRESET_PATH = os.path.join(USER_PATH, "presets")

with open(NICE_NAMES_FILE, "r") as stream:
    NICE_NAME_DATA = json.load(stream)


class AssetBrowser(QtWidgets.QMainWindow):
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
        self.__preset_search_buttons = {}
        self._build_ui()
        self._layout_ui()
        self._setup_ui()
        self.__settings = Settings()

        self.generate_favourites()
        self.generate_contents()
        self.refresh_tab_bar()
        self.apply_style()

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

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget(self.main_widget)
        tabbar = self.tab_widget.tabBar()
        tabbar.setUsesScrollButtons(True)
        tabbar.setExpanding(False)
        tabbar.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
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

        # Search presets
        self.search_presets_scroll = QtWidgets.QScrollArea(self.search_tab_widget)
        self.search_presets_scroll.setWidgetResizable(True)
        self.search_presets_frame = QtWidgets.QFrame(self.search_presets_scroll)
        self.search_presets_layout = QtWidgets.QVBoxLayout(self.search_presets_frame)
        self.search_presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.search_presets_scroll.setWidget(self.search_presets_frame)
        self.search_tab_widget.addTab(self.search_presets_scroll, "Prefabs")

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
                for data_pack in [self.__search_buttons, self.__preset_search_buttons]:
                    for button_data in data_pack.values():
                        match = (
                            search in button_data["search_id"]
                            or search in button_data["search_label"]
                        )
                        button_data["widget"].setVisible(match)

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
            QtGui.QIcon(":FAVOURITES"),
            "Favourites",
        )

        self.favourites_frame = CollapsableFrame(label="Favourites", parent=frame)
        self.favourites_frame.setProperty("partList", True)
        layout.addWidget(self.favourites_frame)

        info_frame = QtWidgets.QFrame(frame)
        info_frame.setObjectName("InfoFrame")
        info_layout = QtWidgets.QHBoxLayout(info_frame)
        info_label = QtWidgets.QLabel(
            """Right click items to add or remove from favourites.
            
Right click on a tab to pin it to the left of the tab bar.""",
            info_frame,
        )
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_label.setObjectName("InfoLabel")
        info_layout.addWidget(info_label)
        layout.addWidget(info_frame)

        self.refresh_favourites()

    def refresh_favourites(self):
        self.__fav_widgets = {}
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
        # Add Categories
        for category_title, category_data in browser_data.items():

            # Main Category
            scroll_frame = QtWidgets.QScrollArea(self)
            scroll_frame.setWidgetResizable(True)
            frame = QtWidgets.QFrame(scroll_frame)
            scroll_frame.setWidget(frame)
            layout = QtWidgets.QVBoxLayout(frame)
            layout.setAlignment(QtCore.Qt.AlignTop)
            category_tab = self.tab_widget.addTab(scroll_frame, category_title)

            if not category_data:
                continue

            # Sub Categories
            for sub_category_title, items in category_data.items():
                title_label = CollapsableFrame(label=sub_category_title, parent=frame)
                title_label.setProperty("partList", True)
                layout.addWidget(title_label)
                if not items:
                    continue
                for item_data in items:
                    item = item_data["id"]
                    show_in_drawer = item_data["showInDrawer"]
                    nice_name = item_data["nice_name"]
                    if show_in_drawer == "True":
                        if isinstance(item, str):
                            # Add to tab.
                            item_widget = Item(
                                item_id=item,
                                label=nice_name,
                                parent=title_label,
                            )
                            title_label.addWidget(item_widget)
                            item_widget.clicked.connect(
                                partial(self.send_part_command_to_blender, item)
                            )
                            item_widget.varClicked.connect(
                                self.send_part_command_to_blender
                            )
                            self.attach_favourites_menu(item_widget, item)

                            # Add to search frame.
                            search_item_widget = Item(
                                item_id=item,
                                label=nice_name,
                                parent=title_label,
                            )
                            self.search_frame_layout.addWidget(search_item_widget)
                            search_item_widget.clicked.connect(
                                partial(self.send_part_command_to_blender, item)
                            )
                            search_item_widget.varClicked.connect(
                                self.send_part_command_to_blender
                            )
                            self.attach_favourites_menu(search_item_widget, item)
                            self.__search_buttons[item] = {
                                "widget": search_item_widget,
                                "search_id": item.lower(),
                                "search_label": nice_name.lower(),
                            }
                            self.__item_widgets[item] = [
                                item_widget,
                                search_item_widget,
                            ]

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
                        if variant_key in self.__item_widgets:
                            widgets = self.__item_widgets[variant_key]
                            for widget in widgets:
                                widget.add_variant(item, nice_name)

        # Add Presets.
        scroll_frame = QtWidgets.QScrollArea(self)
        scroll_frame.setWidgetResizable(True)
        self.presets_frame = QtWidgets.QFrame(scroll_frame)
        scroll_frame.setWidget(self.presets_frame)
        self.presets_layout = QtWidgets.QVBoxLayout(self.presets_frame)
        self.presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_widget.addTab(scroll_frame, "Prefabs")
        self.generate_presets()

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

    def _setup_ui(self):
        self.search_lineedit.textChanged.connect(self.refresh_search)
        self.refresh_presets_button.clicked.connect(self.refresh_presets)
        self.tab_widget.currentChanged.connect(self.refresh_layouts)
        tabbar = self.tab_widget.tabBar()
        tabbar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        tabbar.customContextMenuRequested.connect(self.show_tab_context_menu)

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
                tabbar.setTabIcon(index, QtGui.QIcon())
                
            if tab_name in ["Prefabs"]:
                tabbar.setTabIcon(index, QtGui.QIcon(":PACKAGE"))

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
            if tab not in pinned_tabs and tab not in ["Favourites", "Prefabs"]
        )

        if "Prefabs" in all_tabs:
            unpinned.insert(0, "Prefabs")
        
        final_order = ["Favourites"] + pinned + unpinned

        for target_index, tab_name in enumerate(final_order):
            current_index = self.get_tab_index(tab_name)

            if current_index != -1 and current_index != target_index:
                tabbar.moveTab(current_index, target_index)

    def refresh_layouts(self, tab_index):
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

        BUILDER = no_mans_sky_base_builder.BUILDER

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

    def send_edit_preset_command_to_blender(self, item_id):
        import sys

        path = os.path.join(FILE_DIR, "..", "..").replace("\\", "/")
        if path not in sys.path:
            sys.path.insert(0, path)

        import bpy
        import no_mans_sky_base_builder
        import no_mans_sky_base_builder.preset as preset
        import no_mans_sky_base_builder.utils.blend_utils as blend_utils

        BUILDER = no_mans_sky_base_builder.BUILDER

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


import threading

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

