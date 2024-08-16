try:
  from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
  from PySide2 import QtCore, QtGui, QtWidgets

from asset_browser.flow_layout import FlowLayout


class CollapsableFrame(QtWidgets.QFrame):
    def __init__(self, label=None, layout="flow", *args, **kwargs):
        super(CollapsableFrame, self).__init__(*args, **kwargs)
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)

        self.label = label or ""
        self.button = QtWidgets.QPushButton(self.label, self)
        self.button.clicked.connect(self.toggle_visibility)
        self.button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.inner_frame = QtWidgets.QFrame(self)
        if layout == "flow":
            self.inner_frame_layout = FlowLayout(self.inner_frame)
        if layout == "vertical":
            self.inner_frame_layout = QtWidgets.QVBoxLayout(self.inner_frame)
        self.inner_frame_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.inner_frame_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.addWidget(self.button)
        self.main_layout.addWidget(self.inner_frame)

    def toggle_visibility(self):
        self.inner_frame.setVisible(not self.inner_frame.isVisible())
        self.inner_frame_layout.update()

    def addWidget(self, widget):
        self.inner_frame_layout.addWidget(widget)

    def clear(self):
        for _ in range(self.inner_frame_layout.count()):
            item = self.inner_frame_layout.itemAt(0)
            widget = item.widget()
            self.inner_frame_layout.removeWidget(widget)
            widget.deleteLater()
