import json
import os
import sys
from pathlib import Path


def get_appdata(app_name):
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    else:  # Linux and others
        return (
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            / app_name
        )


class Settings:
    APP_TITLE = "No Mans Sky Base Builder Blender"

    def __init__(self, *args, **kwargs):

        self.folder_path = get_appdata(self.APP_TITLE)
        self.file_path = os.path.join(self.folder_path, "settings.json")
        self.__favourites = []
        self.__pinned_tabs = []
        self.__thumbnail_size_step = None
        self.load_from_file()

    def serialise(self):
        return {
            "favourites": self.__favourites,
            "pinned_tabs": self.__pinned_tabs,
            "thumbnail_size_step": self.__thumbnail_size_step,
        }

    def deserialise(self, data):
        self.__favourites = data.get("favourites", [])
        self.__pinned_tabs = data.get("pinned_tabs", [])
        self.__thumbnail_size_step = data.get("thumbnail_size_step")

    def save_to_file(self):
        os.makedirs(self.folder_path, exist_ok=True)
        with open(self.file_path, "w") as stream:
            json.dump(self.serialise(), stream, indent=4)

    def load_from_file(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as stream:
                data = json.load(stream)
                self.deserialise(data)

    # Favourites...
    def get_favourites(self):
        return self.__favourites

    def add_favourite(self, part_id):
        if part_id not in self.__favourites:
            self.__favourites.append(part_id)
            self.save_to_file()

    def remove_favourite(self, part_id):
        if part_id in self.__favourites:
            self.__favourites.remove(part_id)
            self.save_to_file()

    def can_move_left(self, part_id):
        return part_id in self.__favourites and self.__favourites.index(part_id) > 0

    def can_move_right(self, part_id):
        return (
            part_id in self.__favourites
            and self.__favourites.index(part_id) < len(self.__favourites) - 1
        )

    def move_favourite_left(self, part_id):
        if self.can_move_left(part_id):
            index = self.__favourites.index(part_id)
            self.__favourites[index], self.__favourites[index - 1] = (
                self.__favourites[index - 1],
                self.__favourites[index],
            )
            self.save_to_file()

    def move_favourite_right(self, part_id):
        if self.can_move_right(part_id):
            index = self.__favourites.index(part_id)
            self.__favourites[index], self.__favourites[index + 1] = (
                self.__favourites[index + 1],
                self.__favourites[index],
            )
            self.save_to_file()

    def bring_favourite_to_front(self, part_id):
        if part_id in self.__favourites:
            self.__favourites.remove(part_id)
            self.__favourites.insert(0, part_id)
            self.save_to_file()

    def send_favourite_to_back(self, part_id):
        if part_id in self.__favourites:
            self.__favourites.remove(part_id)
            self.__favourites.append(part_id)
            self.save_to_file()

    # Pinned Tabs ---
    def get_pinned_tabs(self):
        return self.__pinned_tabs

    def add_pinned_tab(self, tab_id):
        if tab_id not in self.__pinned_tabs:
            self.__pinned_tabs.append(tab_id)
            self.save_to_file()

    def remove_pinned_tab(self, tab_id):
        if tab_id in self.__pinned_tabs:
            self.__pinned_tabs.remove(tab_id)
            self.save_to_file()

    # Part list thumbnail size ---
    def get_thumbnail_size_step(self):
        return self.__thumbnail_size_step

    def set_thumbnail_size_step(self, step):
        if step != self.__thumbnail_size_step:
            self.__thumbnail_size_step = step
            self.save_to_file()
