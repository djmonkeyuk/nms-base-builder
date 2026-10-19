import importlib
import os
import site
import subprocess
import sys

# Check and install dependencies.
PYTHON_EXE_PATH = sys.executable


# target_dir = os.path.join(sys.exec_prefix, "lib", "site-packages")


def add_site_dirs():
    site_dirs = []
    try:
        site_dirs.extend(site.getsitepackages())
    except AttributeError:
        pass

    try:
        site_dirs.extend(site.getusersitepackages().split(os.pathsep))
    except AttributeError:
        site_dirs.append(site.getusersitepackages())

    for path in site_dirs:
        if path and path not in sys.path:
            sys.path.append(path)
        try:
            site.addsitedir(path)
        except Exception:
            pass

    importlib.invalidate_caches()


for p in site.getusersitepackages().split(os.pathsep):
    if p not in sys.path:
        sys.path.append(p)


def install_pip():
    command = [PYTHON_EXE_PATH, "-m", "ensurepip", "--upgrade"]
    subprocess.run(command, check=True)


def install_package(package_name):
    command = [PYTHON_EXE_PATH, "-m", "pip", "install", package_name]
    subprocess.run(command, check=True)


def check_dependencies():
    try:
        import pip

        print("Pip found.")
    except Exception:
        install_pip()
        add_site_dirs()

    try:
        import PySide6

        print("PySide6 found.")
    except Exception:
        install_package("PySide6_Essentials")
        add_site_dirs()
        try:
            import PySide6

            print("PySide6 found after install.")
        except Exception:
            raise

    return True


def prewarm_qt():
    """Pays Qt's one-time style/font-engine warmup cost on a throwaway
    widget, in the background, before the user ever opens the Asset
    Browser - so their actual first click doesn't pay it.

    Confirmed by profiling: the first-ever styled widget shown in a fresh
    QApplication session costs roughly 30x more than every one after it
    (~0.4-1s vs ~0.01-0.1s) - and this holds for a trivial QFrame with one
    label and one button, not just the full AssetBrowser window, meaning
    it's a general Qt engine cost paid once per process, not something
    tied to how complex the real window is. The QApplication this creates
    is the same one AssetBrowser.load() looks for and reuses
    (QApplication.instance() or QApplication(...)), so nothing is wasted -
    the dummy widget itself is destroyed immediately.

    Silently does nothing if PySide6 isn't already known-installed (never
    triggers an install from here - that should only ever happen from the
    user explicitly launching the browser, via check_dependencies()) or if
    anything at all goes wrong - this is purely a perf optimisation for
    the real launch, never something that should affect Blender's own
    behaviour if it fails.
    """
    try:
        import PySide6
    except Exception:
        return

    try:
        from PySide6 import QtWidgets

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        stylesheet_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "core.css"
        )
        widget = QtWidgets.QFrame()
        if os.path.isfile(stylesheet_path):
            with open(stylesheet_path) as stream:
                widget.setStyleSheet(stream.read())
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel("", widget))
        layout.addWidget(QtWidgets.QPushButton("", widget))
        widget.show()
        widget.minimumSizeHint()
        widget.hide()
        widget.deleteLater()
    except Exception:
        pass
