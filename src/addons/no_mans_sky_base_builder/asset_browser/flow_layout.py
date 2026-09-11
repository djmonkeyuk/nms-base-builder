import sys

from .utils.qt import QtCore, QtGui, QtWidgets


class FlowLayout(QtWidgets.QLayout):
    heightChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # if parent is not None:
        #     self.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))

        self._item_list = []
        self._list_mode = False

    def set_list_mode(self, enabled):
        """Switch between wrapping grid layout and a single-column list layout."""
        if self._list_mode != enabled:
            self._list_mode = enabled
            self.invalidate()

    def is_list_mode(self):
        return self._list_mode

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)
        self.invalidate()

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            item = self._item_list.pop(index)
            self.invalidate()
            return item

        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()

        for item in self._item_list:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            size = size.expandedTo(item.minimumSize())

        size += QtCore.QSize(
            2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()
        )
        return size

    def _do_layout(self, rect, test_only):
        if self._list_mode:
            return self._do_list_layout(rect, test_only)

        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QtWidgets.QSizePolicy.ControlType.PushButton,
                QtWidgets.QSizePolicy.ControlType.PushButton,
                QtCore.Qt.Orientation.Horizontal,
            )
            layout_spacing_y = style.layoutSpacing(
                QtWidgets.QSizePolicy.ControlType.PushButton,
                QtWidgets.QSizePolicy.ControlType.PushButton,
                QtCore.Qt.Orientation.Vertical,
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        new_height = y + line_height - rect.y()
        self.heightChanged.emit(new_height)
        return new_height

    def _do_list_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        spacing = self.spacing()

        for item in self._item_list:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            style = widget.style()
            layout_spacing_y = style.layoutSpacing(
                QtWidgets.QSizePolicy.ControlType.PushButton,
                QtWidgets.QSizePolicy.ControlType.PushButton,
                QtCore.Qt.Orientation.Vertical,
            )
            space_y = max(spacing, 0) + layout_spacing_y
            height = item.sizeHint().height()

            if not test_only:
                item.setGeometry(QtCore.QRect(x, y, rect.width(), height))

            y += height + space_y

        new_height = y - rect.y()
        self.heightChanged.emit(new_height)
        return new_height
