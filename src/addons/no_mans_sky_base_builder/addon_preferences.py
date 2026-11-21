import bpy
from bpy.props import BoolProperty, StringProperty

from .save_editor import save_editor_utils

ADDON_ID = __package__


class NMSAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    nms_save_folder_path: StringProperty(
        name="Save Directory",
        description="Folder where save files are stored",
        subtype='DIR_PATH',
        default = str(save_editor_utils.get_default_save_folder())
    )

    share_meshes_on_duplicate: BoolProperty(
        name="Share part meshes on duplicate",
        description=(
            "Turn off blender's Duplicate Data > Mesh, so Shift+D copies share the "
            "original part's mesh, like Alt+D. Keeps big bases light"
        ),
        default=True,
        update=lambda self, context: apply_duplicate_mesh_setting(self),
    )

    # blender's own Duplicate Data > Mesh value, put back when sharing is turned off
    original_duplicate_mesh: BoolProperty(default=True)
    has_original_duplicate_mesh: BoolProperty(default=False)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "nms_save_folder_path")
        layout.prop(self, "share_meshes_on_duplicate")


def get_addon_preferences():
    addon = bpy.context.preferences.addons.get(ADDON_ID)
    return addon.preferences if addon else None


# the NMS save folder, None while the addon's preferences aren't available
def get_save_folder_path():
    prefs = get_addon_preferences()
    return prefs.nms_save_folder_path if prefs else None


# store the NMS save folder and write the user preferences to disk
# returns True when the folder was stored
def set_save_folder_path(path, save=True):
    prefs = get_addon_preferences()
    if prefs is None:
        return False

    prefs.nms_save_folder_path = str(path)
    if save:
        save_user_preferences()
    return True


def save_user_preferences():
    # the operator needs a window, there is none in background mode
    try:
        bpy.ops.wm.save_userpref()
    except RuntimeError as error:
        print("Could not save preferences:", error)


# turn blender's Duplicate Data > Mesh off while sharing is on, remembering its value
def apply_duplicate_mesh_setting(prefs=None):
    prefs = prefs or get_addon_preferences()
    if prefs is None:
        return

    if not prefs.share_meshes_on_duplicate:
        restore_duplicate_mesh_setting(prefs)
        return

    edit_preferences = bpy.context.preferences.edit
    if not prefs.has_original_duplicate_mesh:
        prefs.original_duplicate_mesh = edit_preferences.use_duplicate_mesh
        prefs.has_original_duplicate_mesh = True
    edit_preferences.use_duplicate_mesh = False


# put blender's Duplicate Data > Mesh back the way it was
def restore_duplicate_mesh_setting(prefs=None):
    prefs = prefs or get_addon_preferences()
    if prefs is None or not prefs.has_original_duplicate_mesh:
        return
    bpy.context.preferences.edit.use_duplicate_mesh = prefs.original_duplicate_mesh
    prefs.has_original_duplicate_mesh = False
