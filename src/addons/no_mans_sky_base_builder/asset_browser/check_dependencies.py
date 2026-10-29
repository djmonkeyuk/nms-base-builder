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

