import ctypes
import json
import os
import sys
import tempfile
import time
from functools import partial

import yaml

try:
  from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
  from PySide2 import QtCore, QtGui, QtWidgets

import asset_browser.icons.icons
import yaml
from asset_browser.collapsable_frame import CollapsableFrame
from asset_browser.flow_layout import FlowLayout
from asset_browser.item import Item, Preset
from PySide6 import QtCore, QtGui, QtWidgets

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
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        app_id = u"djmonkey.NMSBB.AssetBrowser.1"  # arbitrary string
        # FIXME: do this in some platform-agnostic way if possible
        if hasattr(ctypes, 'windll'):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        self.setWindowTitle("No Man's Sky Blender Builder - Asset Browser")
        self.setWindowIcon(QtGui.QIcon(APP_ICON))
        self.__search_buttons = []
        self.__preset_search_buttons = []
        self._build_ui()
        self._layout_ui()
        self._setup_ui()

        self.generate_contents()
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
        self.refresh_presets_button.setToolTip("Refresh Presets")

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget(self.main_widget)

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
        self.search_tab_widget.addTab(self.search_presets_scroll, "Presets")

    def refresh_search(self):
        search = self.search_lineedit.text()
        if search:
            self.tab_widget.setVisible(False)
            self.search_scroll.setVisible(True)
            for array in [self.__search_buttons, self.__preset_search_buttons]:
                for button in array:
                    if (
                        search.lower() in button.item_id.lower()
                        or search.lower() in button.label.lower()
                    ):
                        button.setVisible(True)
                    else:
                        button.setVisible(False)
        else:
            self.tab_widget.setVisible(True)
            self.search_scroll.setVisible(False)

    def generate_contents(self):
        with open(BROWSER_LAYOUT_FILE, "r") as stream:
            browser_data = yaml.safe_load(stream)

        # Add Categories
        for category_data in browser_data:
            for category, sub_category_data in category_data.items():
                scroll_frame = QtWidgets.QScrollArea(self)
                scroll_frame.setWidgetResizable(True)
                frame = QtWidgets.QFrame(scroll_frame)
                scroll_frame.setWidget(frame)
                layout = QtWidgets.QVBoxLayout(frame)
                layout.setAlignment(QtCore.Qt.AlignTop)
                self.tab_widget.addTab(scroll_frame, category)
                if not sub_category_data:
                    continue
                for data in sub_category_data:
                    for sub_category_title, items in data.items():
                        title_label = CollapsableFrame(
                            label=sub_category_title, parent=frame
                        )
                        layout.addWidget(title_label)
                        if not items:
                            continue
                        for item in items:
                            if isinstance(item, str):
                                # Add to tab.
                                item_widget = Item(
                                    item_id=item,
                                    label=NICE_NAME_DATA.get(item, item),
                                    parent=title_label,
                                )
                                title_label.addWidget(item_widget)
                                item_widget.clicked.connect(
                                    partial(self.send_part_command_to_blender, item)
                                )
                                # Add to search frame.
                                search_item_widget = Item(
                                    item_id=item,
                                    label=NICE_NAME_DATA.get(item, item),
                                    parent=title_label,
                                )
                                self.search_frame_layout.addWidget(search_item_widget)
                                search_item_widget.clicked.connect(
                                    partial(self.send_part_command_to_blender, item)
                                )
                                self.__search_buttons.append(search_item_widget)

        # Add Presets.
        scroll_frame = QtWidgets.QScrollArea(self)
        scroll_frame.setWidgetResizable(True)
        self.presets_frame = QtWidgets.QFrame(scroll_frame)
        scroll_frame.setWidget(self.presets_frame)
        self.presets_layout = QtWidgets.QVBoxLayout(self.presets_frame)
        self.presets_layout.setAlignment(QtCore.Qt.AlignTop)
        self.tab_widget.addTab(scroll_frame, "Presets")
        self.generate_presets()

    def clear_presets(self):
        for widget in self.__preset_search_buttons:
            widget.parent().layout().removeWidget(widget)
            widget.deleteLater()
        for _ in range(self.presets_layout.count()):
            item = self.presets_layout.itemAt(0)
            widget = item.widget()
            if widget and isinstance(widget, CollapsableFrame):
                self.presets_layout.removeWidget(widget)
                widget.deleteLater()
        self.__preset_search_buttons = []

    def generate_presets(self):
        self.__preset_search_buttons = []
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
        presets = [item for item in presets if os.path.isfile(os.path.join(PRESET_PATH, item))]
        if presets:
            preset_category_frame = CollapsableFrame(
                label="Uncategorized Presets", layout="vertical", parent=self.presets_frame
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
        item_widget = Preset(
            item_id=item_id, label=nice_label, parent=frame
        )
        frame.addWidget(item_widget)
        item_widget.clicked.connect(
            partial(self.send_part_command_to_blender, item_id)
        )
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
        self.__preset_search_buttons.append(search_item_widget)

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
        PYTHON_FILE = os.path.join(tempfile.gettempdir(), "command_script.py")

        script_contents = ""
        with open(SEND_SNIPPET, "r") as stream:
            script_contents = stream.read()

        with open(PYTHON_FILE, "w") as stream:
            stream.write(script_contents.format(item_id))

        TEMP_PATH = os.path.join(tempfile.gettempdir(), "bpy_external.io")
        with open(TEMP_PATH, "w") as stream:
            stream.write(PYTHON_FILE)

    def send_edit_preset_command_to_blender(self, item_id):
        PYTHON_FILE = os.path.join(tempfile.gettempdir(), "command_script.py")

        script_contents = ""
        with open(EDIT_PRESET_SNIPPET, "r") as stream:
            script_contents = stream.read()

        with open(PYTHON_FILE, "w") as stream:
            stream.write(script_contents.format(item_id))

        TEMP_PATH = os.path.join(tempfile.gettempdir(), "bpy_external.io")
        with open(TEMP_PATH, "w") as stream:
            stream.write(PYTHON_FILE)

    def sizeHint(self):
        return QtCore.QSize(1000, 1000)

    def closeEvent(self, event):
        PYTHON_FILE = os.path.join(tempfile.gettempdir(), "command_script.py")
        script_contents = ""
        with open(END_SNIPPET, "r") as stream:
            script_contents = stream.read()
        with open(PYTHON_FILE, "w") as stream:
            stream.write(script_contents)

        TEMP_PATH = os.path.join(tempfile.gettempdir(), "bpy_external.io")
        with open(TEMP_PATH, "w") as stream:
            stream.write(PYTHON_FILE)

        time.sleep(0.5)
        with open(TEMP_PATH, "w") as stream:
            stream.write("")

        # Close
        super(AssetBrowser, self).closeEvent(event)


def load():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AssetBrowser()
    window.show()
    app.exit(app.exec_())
