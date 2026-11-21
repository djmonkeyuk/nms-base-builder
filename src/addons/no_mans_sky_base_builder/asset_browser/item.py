import os
from functools import partial

from .icons import icons
from .utils.qt import QtCore, QtGui, QtWidgets

DEFAULT_THUMB_SIZE = 64
MIN_THUMB_SIZE = 32
MAX_THUMB_SIZE = 128
GRID_LABEL_PADDING = 36
GRID_HEIGHT_PADDING = 61
LIST_HEIGHT_PADDING = 16
FONT_SIZE = 10

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
ICON_PATH = os.path.join(FILE_DIR, "icons")


class Thumb(QtWidgets.QLabel):
    def __init__(self, part_id=None, size=DEFAULT_THUMB_SIZE, *args, **kwargs):
        super(Thumb, self).__init__(*args, **kwargs)
        self.part_id = part_id or ""
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.set_size(size)

    def set_size(self, size):
        self.setMinimumSize(QtCore.QSize(size, size))
        self.setMaximumSize(QtCore.QSize(size, size))
        icon_path = ":{}".format(self.part_id)
        if QtCore.QFile.exists(icon_path):
            pixmap = QtGui.QPixmap(icon_path)
            scaled = pixmap.scaled(
                size,
                size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            self.setPixmap(scaled)


class Item(QtWidgets.QFrame):

    clicked = QtCore.Signal()
    rightClicked = QtCore.Signal()
    varClicked = QtCore.Signal(str)

    def __init__(self, item_id=None, label=None, variants=None, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)
        self.label = label or ""
        self.item_id = item_id or ""
        self.variants = variants or []
        self.setToolTip(self.item_id)
        self._thumb_size = DEFAULT_THUMB_SIZE
        self._view_mode = "grid"

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_ui()
        self._layout()
        self._setup()
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._apply_view_mode()

    def _build_ui(self):
        # A page for the "icon on top, label below, centered" grid appearance.
        self.grid_page = QtWidgets.QWidget(self)
        self.grid_page_layout = QtWidgets.QVBoxLayout(self.grid_page)
        self.grid_page_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_page_layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        # A page for the "icon on the left, label on the right" list appearance.
        self.list_page = QtWidgets.QWidget(self)
        self.list_page_layout = QtWidgets.QHBoxLayout(self.list_page)
        self.list_page_layout.setContentsMargins(6, 3, 6, 3)
        self.list_page_layout.setSpacing(8)

        self.thumb_container = QtWidgets.QWidget(self)
        self.thumb_container_layout = QtWidgets.QHBoxLayout(self.thumb_container)
        self.thumb_container_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb = Thumb(
            part_id=self.item_id, size=self._thumb_size, parent=self.thumb_container
        )
        self.thumb_container_layout.addWidget(self.thumb)

        self.label_widget = QtWidgets.QLabel(self.label, parent=self)
        self.label_widget.setWordWrap(True)
        font = QtGui.QFont("Decorative", FONT_SIZE)
        self.label_widget.setFont(font)

        self.variants_button = QtWidgets.QPushButton("v", self)
        self.variants_button.setContentsMargins(0, 0, 0, 0)
        self.variants_button.setFixedSize(25, 25)
        self.variants_button.setVisible(False)
        self.variants_button.setObjectName("VariantButton")

    def _layout(self):
        self.main_layout.addWidget(self.grid_page)
        self.main_layout.addWidget(self.list_page)

    def _setup(self):
        self.variants_button.clicked.connect(self.open_context_menu)

    def set_thumbnail_size(self, size):
        size = max(MIN_THUMB_SIZE, min(MAX_THUMB_SIZE, size))
        if size == self._thumb_size:
            return
        self._thumb_size = size
        self.thumb.set_size(size)
        self._apply_view_mode()

    def set_view_mode(self, mode):
        if mode not in ("grid", "list") or mode == self._view_mode:
            return
        self._view_mode = mode
        self._apply_view_mode()

    def _apply_view_mode(self):
        # Detach the shared thumbnail/label from whichever page currently holds them.
        self.grid_page_layout.removeWidget(self.thumb_container)
        self.grid_page_layout.removeWidget(self.label_widget)
        self.list_page_layout.removeWidget(self.thumb_container)
        self.list_page_layout.removeWidget(self.label_widget)

        if self._view_mode == "grid":
            self.grid_page.setVisible(True)
            self.list_page.setVisible(False)
            self.label_widget.setAlignment(QtCore.Qt.AlignCenter)
            label_width = max(self._thumb_size + GRID_LABEL_PADDING, 70)
            self.label_widget.setMinimumWidth(label_width)
            self.label_widget.setMaximumWidth(label_width)
            self.grid_page_layout.addWidget(
                self.thumb_container, 0, QtCore.Qt.AlignHCenter
            )
            self.grid_page_layout.addWidget(
                self.label_widget, 0, QtCore.Qt.AlignHCenter
            )
            width = label_width + 10
            height = self._thumb_size + GRID_HEIGHT_PADDING
            self.setMinimumSize(QtCore.QSize(width, height))
            self.setMaximumSize(QtCore.QSize(width, height))
        else:
            self.grid_page.setVisible(False)
            self.list_page.setVisible(True)
            self.label_widget.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.label_widget.setMinimumWidth(0)
            self.label_widget.setMaximumWidth(16777215)
            self.list_page_layout.addWidget(self.thumb_container)
            self.list_page_layout.addWidget(self.label_widget, 1)
            height = self._thumb_size + LIST_HEIGHT_PADDING
            self.setMinimumSize(QtCore.QSize(0, height))
            self.setMaximumSize(QtCore.QSize(16777215, height))

        self.variants_button.raise_()
        self.updateGeometry()
        self._position_variants_button()

    def resizeEvent(self, event):
        super(Item, self).resizeEvent(event)
        self._position_variants_button()

    def _position_variants_button(self):
        margin = 4
        self.variants_button.move(
            max(self.width() - self.variants_button.width() - margin, 0),
            margin if self._view_mode == "grid" else
            max((self.height() - self.variants_button.height()) // 2, 0),
        )

    def open_context_menu(self):
        variants_menu = QtWidgets.QMenu(self.variants_button)
        action = variants_menu.addAction(self.label)
        action.triggered.connect(partial(self.add_part, self.item_id))
        for variant_id, variant_label in self.variants:
            action = variants_menu.addAction(variant_label)
            action.triggered.connect(partial(self.add_part, variant_id))
        variants_menu.exec(QtGui.QCursor.pos())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        elif event.button() == QtCore.Qt.RightButton:
            self.rightClicked.emit()

    def add_variant(self, variant_id, variant_label):
        self.variants.append((variant_id, variant_label))
        self.refresh_variants()

    def refresh_variants(self):
        if self.variants:
            self.variants_button.setVisible(True)
            self.variants_button.raise_()

    def add_part(self, part_id):
        self.varClicked.emit(part_id)


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
        self.label_button.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        font = QtGui.QFont("Decorative", FONT_SIZE)
        self.label_button.setFont(font)
        self.edit_button = QtWidgets.QPushButton("Edit", parent=self)
        self.edit_button.setObjectName("EditButton")

    def _layout(self):
        self.main_layout.addWidget(self.label_button)
        self.main_layout.addWidget(self.edit_button)

    def _setup_ui(self):
        self.label_button.clicked.connect(self.clicked.emit)
        self.edit_button.clicked.connect(self.editClicked.emit)
