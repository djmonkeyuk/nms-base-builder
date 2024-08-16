import os
import subprocess
import sys

# Check and install dependencies.
PYTHON_EXE_PATH = sys.executable
PYTHON_DIR_PATH = os.path.dirname(PYTHON_EXE_PATH)

def install_pip():
    command = [PYTHON_EXE_PATH, "-m", "ensurepip", "--upgrade"]
    subprocess.run(command)

def install_package(package_name):
    command = [PYTHON_EXE_PATH, "-m", "pip", "install", package_name]
    subprocess.run(command)

try:
    import pip
    print ("Pip found.")
except:
    install_pip()

try:
    import yaml
    print ("Yaml found.")
except:
    install_package("pyaml")

try:
    import PySide6
    print ("PySide6 found.")
except:
    try:
        import PySide2
        print ("PySide2 found (fallback).")
    except:
        install_package("PySide6")

# Load the Asset Browser
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
ASSET_BROWSER_PATH = os.path.join(THIS_DIR, "..")
sys.path.append(ASSET_BROWSER_PATH)

import asset_browser.main

asset_browser.main.load()
