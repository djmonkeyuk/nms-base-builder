import json
import os

try:
  from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
  from PySide2 import QtCore, QtGui, QtWidgets

import asset_browser.icons.icons

THUMB_SIZE = 55
ITEM_SIZE = 80
FONT_SIZE = 7

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
ICON_PATH = os.path.join(FILE_DIR, "icons")

class Thumb(QtWidgets.QLabel):
    def __init__(self, part_id=None, *args, **kwargs):
        super(Thumb, self).__init__(*args, **kwargs)
        part_id = part_id or ""
        icon_path = ":{}".format(part_id)
        if QtCore.QFile.exists(icon_path):
            pixmap = QtGui.QPixmap(icon_path)
            scaled = pixmap.scaled(THUMB_SIZE, THUMB_SIZE, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.setPixmap(scaled)
        self.setMinimumSize(QtCore.QSize(THUMB_SIZE, THUMB_SIZE))
        self.setMaximumSize(QtCore.QSize(THUMB_SIZE, THUMB_SIZE))
        self.setAlignment(QtCore.Qt.AlignCenter)

class Item(QtWidgets.QFrame):

    clicked = QtCore.Signal()

    def __init__(self, item_id=None, label=None, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)
        self.label = label or ""
        self.item_id = item_id or ""
        self.setToolTip(self.item_id)
        self.setMinimumSize(QtCore.QSize(ITEM_SIZE, ITEM_SIZE))
        self.setMaximumSize(QtCore.QSize(ITEM_SIZE, ITEM_SIZE))
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        self._build_ui()
        self._layout()
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def _build_ui(self):
        self.thumb = Thumb(part_id=self.item_id, parent=self)
        self.label_widget = QtWidgets.QLabel(self.label, parent=self)
        self.label_widget.setAlignment(QtCore.Qt.AlignCenter)
        self.label_widget.setWordWrap(True)
        font = QtGui.QFont("Decorative", FONT_SIZE)
        self.label_widget.setFont(font)
        self.label_widget.setMinimumWidth(THUMB_SIZE)
        self.label_widget.setMaximumWidth(THUMB_SIZE)

    def _layout(self):
        self.main_layout.addWidget(self.thumb, QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(self.label_widget, QtCore.Qt.AlignCenter)


    def mousePressEvent(self, event):
        self.clicked.emit()


class Preset(QtWidgets.QFrame):

    clicked = QtCore.Signal()
    editClicked = QtCore.Signal()

    def __init__(self, item_id=None, label=None, *args, **kwargs):
        super(Preset, self).__init__(*args, **kwargs)
        self.label = label or ""
        self.item_id = item_id or ""
        self.setToolTip(self.item_id)
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        self._build_ui()
        self._layout()
        self._setup_ui()
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    def _build_ui(self):
        self.label_button = QtWidgets.QPushButton(self.label, parent=self)
        self.label_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        font = QtGui.QFont("Decorative", 10)
        self.label_button.setFont(font)
        self.edit_button = QtWidgets.QPushButton("Edit" , parent=self)

    def _layout(self):
        self.main_layout.addWidget(self.label_button)
        self.main_layout.addWidget(self.edit_button)

    def _setup_ui(self):
        self.label_button.clicked.connect(self.clicked.emit)
        self.edit_button.clicked.connect(self.editClicked.emit)
