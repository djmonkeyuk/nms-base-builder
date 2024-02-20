import os
import subprocess
import sys

from PIL import Image

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))


from automation_utils import (PATH_TO_MOD_PROJECT, PATH_TO_UNPACKED,
                              list_missing_icons)

icon_dict = list_missing_icons(os.path.join(PATH_TO_MOD_PROJECT, "METADATA/REALITY/TABLES/NMS_REALITY_GCPRODUCTTABLE.EXML"))
ICON_EXPORT_FOLDER = os.path.dirname(os.path.realpath(__file__))
ICON_EXPORT_FOLDER = os.path.join(ICON_EXPORT_FOLDER, "icon_export")

for icon, path in icon_dict.items():
    new_path = os.path.join(ICON_EXPORT_FOLDER, icon+".PNG")
    image_load = Image.open(os.path.join(PATH_TO_UNPACKED, path))
    new_image = image_load.resize((64, 64))
    new_image.save(new_path)

# Write QRC.
file_path = os.path.join(ICON_EXPORT_FOLDER, "icons.qrc")
return_string = "<!DOCTYPE RCC><RCC version=\"1.0\">\n"
return_string += "<qresource>\n"
for part in icon_dict.keys():
    return_string += "    <file alias=\"{0}\">{0}.PNG</file>\n".format(part)
return_string += "    <file alias=\"TOP_BAR_REFRESH\">../images/TOP_BAR_REFRESH.PNG</file>\n".format(part)
return_string += "</qresource>\n"
return_string += "</RCC>\n"

file_path = os.path.join(ICON_EXPORT_FOLDER, "icons.qrc")
with open(file_path, "w") as stream:
    stream.write(return_string)

subprocess.call("pyside6-rcc.exe -g python {} -o {}".format(file_path, file_path.replace(".qrc", ".py")))
