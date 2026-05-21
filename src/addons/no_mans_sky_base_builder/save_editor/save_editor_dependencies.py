import importlib.util
import os
import site
import subprocess
import sys

PYTHON_EXE_PATH = sys.executable

for p in site.getusersitepackages().split(os.pathsep):
    if p not in sys.path:
        sys.path.append(p)


def install_pip():
    command = [PYTHON_EXE_PATH, "-m", "ensurepip", "--upgrade"]
    subprocess.run(command)


def install_package(package_name):
    command = [PYTHON_EXE_PATH, "-m", "pip", "install", package_name]
    subprocess.run(command)
    
def check_package(package_name):
    found = importlib.util.find_spec(package_name) 
    return found

def installDependencies():
    if not check_package("pip"):
        install_pip()

    if not check_package("lz4"):
        install_package("lz4")

    return True
