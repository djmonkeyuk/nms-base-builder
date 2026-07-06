import bpy

from . import save_editor_utils
ADDON_ID = __package__.rsplit(".", 1)[0]

# Operator for button to select save folder directory
class SelectSaveFolder(bpy.types.Operator):
    bl_idname = "object.nms_select_save_folder"
    bl_label = "Select Folder"
    
    bl_description = "Manually select location of save folder of NMS"

    directory: bpy.props.StringProperty(
        subtype='DIR_PATH'
    )

    def execute(self, context):
        prefs = context.scene
        print("folder is :", self.directory)
        if save_editor_utils.validate_save_folder(str(self.directory)):
            
            prefs = context.preferences.addons[ADDON_ID].preferences
            prefs.nms_save_folder_path = self.directory
            bpy.ops.wm.save_userpref()
            
            scene = context.scene
            save_data = scene.nms_save_data
            save_data.on_check_plugin_enabled(context)
            save_data.nms_account_selected = "Default"
            
            self.report({'INFO'}, f"Selected folder is valid NMS save folder")
            print("Selected folder is valid:", prefs.nms_save_folder_path)
        else :
            self.report({'ERROR'}, f"Selected folder is not a NMS save folder. Please select the correct folder.")
            print("Selected folder is invalid:", self.directory)
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = context.preferences.addons[ADDON_ID].preferences
        save_root_folder = prefs.nms_save_folder_path
        self.directory = save_root_folder
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# Button to import base selected from list of bases in save editor section
class ImportBaseFromSave(bpy.types.Operator):
    bl_idname = "object.nms_import_base_from_save"
    bl_label = "Import data from selected file"
    bl_description = "Import base from save file while also pinning it on top"

    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        result = save_data.import_base_from_save_file(context)
        if result is not None:
            self.report({'INFO'}, result)
        return {"FINISHED"}

# Button to export base selected from list of bases in save editor section
class ExportBaseToSave(bpy.types.Operator):
    bl_idname = "object.nms_export_base_to_save"
    bl_label = "Export data to save file"
    bl_description = "Export base to save_file"

    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        result = save_data.export_base_to_save_file(context)
        if result is not None:
            self.report({'INFO'}, result)
        return {"FINISHED"}
    
# Button to pin base to top of the editor
class PinBase(bpy.types.Operator):
    bl_idname = "object.nms_pin_base"
    bl_label = "Pin"
    bl_description = "Pin this base at top of Save Editor for easy access to updating functionality and persistence"
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.pin_base()
        return {"FINISHED"}
    
# Button to unpin base from top of editor
class UnpinBase(bpy.types.Operator):
    
    bl_idname = "object.nms_unpin_base"
    bl_label = "Unpin"
    bl_description = "Unpin base from top of save editor"
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.unpin_base()
        return {"FINISHED"}
    
# button to imoprt base data from a pinned base
class ImportPinnedBase(bpy.types.Operator):
    bl_idname = "object.import_pinned_base"
    bl_label = "Import"
    
    bl_description = (
        "Import latest data from save file into scene, \n"
        "replace all objects in scene with data imported"
    )
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.import_pinned_base(context)
        return {"FINISHED"}
    
# button to export data to save file from pinned base
class ExoprtPinnedBase(bpy.types.Operator):
    
    bl_idname = "object.export_pinned_base"
    bl_label = "Export"
    bl_description = (
        "Update changes to save_file onto location that is pinned.\n"
        "Only ['Objects'] are updated.\n"
        "Check export base name to update name along with objects.\n"
        "Base Name will be taken from 'Base Name' field in Base properties section"
    )
        
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        result = save_data.export_pinned_base(context)
        if result is not None:
            self.report({'INFO'}, result)
        else: 
            self.report({'ERROR'}, "Update Failed, repinning the base may resolve this issue ")
            print("result is none")
        return {"FINISHED"}
    
# a button to manually backup save files
class MakeBackupPinned(bpy.types.Operator):
    
    bl_idname = "object.make_pinned_savefile_backup"
    bl_label = "Backup"
    bl_description = (
        "Backup save files liked to pinned base\n"
        "backup folder with name 'nms_base_builder_backup' will be created in folder where save files are located. \n"
        "To restore, rename the files by remove everything before '.hg.' and pasting them into their parent folder"
    )
        
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.backup_pinned_save_files()
        self.report({'INFO'}, "Backup created sucessfully")
        return {"FINISHED"}
    
    
class MakeBackup(bpy.types.Operator):
    
    bl_idname = "object.make_savefile_backup"
    bl_label = "Backup"
    bl_description = (
        "Backup currently selected save slot\n"
        "backup folder with name 'nms_base_builder_backup' will be created in folder where save files are located. \n"
        "To restore, rename the files by remove everything before '.hg.' and pasting them into their parent folder"
    )
        
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.backup_save_files()
        self.report({'INFO'}, "Backup created sucessfully")
        return {"FINISHED"}
    
class OpenBackupFolder(bpy.types.Operator):
    
    bl_idname = "object.open_backup_folder"
    bl_label = "Open save folder"
    bl_description = (
        "Backup currently selected save slot\n"
        "backup folder with name 'nms_base_builder_backup' will be created in folder where save files are located. \n"
        "To restore, rename the files by remove everything before '.hg.' and pasting them into their parent folder"
    )
        
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.open_backup_folder_in_explorer()
        return {"FINISHED"}

# these classes can be appened to classes list in __init__.py file with + operator  
classes = (
    SelectSaveFolder,
    ImportBaseFromSave,
    ExportBaseToSave,
    PinBase,
    UnpinBase,
    ImportPinnedBase,
    ExoprtPinnedBase,
    MakeBackupPinned,
    MakeBackup,
    OpenBackupFolder
)