import bpy


# Operator for button to select save folder directory
class SelectSaveFolder(bpy.types.Operator):
    bl_idname = "object.nms_select_save_folder"
    bl_label = "Select Folder"

    directory: bpy.props.StringProperty(
        subtype='DIR_PATH'
    )

    def execute(self, context):
        prefs = context.scene
        save_file_identifier = "HelloGames\\NMS\\"

        print("folder is :", self.directory)
        if str(self.directory).lower().endswith(save_file_identifier.lower()):
            prefs.nms_save_folder_path = self.directory
            bpy.ops.wm.save_userpref()
            print("Selected folder is valid:", prefs.nms_save_folder_path)
        else :
            self.report({'ERROR'}, f"Selected folder is not a NMS save folder. Please select the correct folder.")
            print("Selected folder is invalid:", self.directory)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# Button to import base selected from list of bases in save editor section
class ImportBaseFromSave(bpy.types.Operator):
    bl_idname = "object.nms_import_base_from_save"
    bl_label = "Import data from selected file"

    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        result = save_data.import_base_from_save_file(context)
        save_data.pin_base()
        if result is not None:
            self.report({'INFO'}, result)
        return {"FINISHED"}

# Button to export base selected from list of bases in save editor section
class ExportBaseToSave(bpy.types.Operator):
    bl_idname = "object.nms_export_base_to_save"
    bl_label = "Export data to save file"

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
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.pin_base()
        return {"FINISHED"}
    
# Button to unpin base from top of editor
class UnpinBase(bpy.types.Operator):
    
    bl_idname = "object.nms_unpin_base"
    bl_label = "Unpin"
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.unpin_base()
        return {"FINISHED"}
    
# button to imoprt base data from a pinned base
class ImportPinnedBase(bpy.types.Operator):
    bl_idname = "object.import_pinned_base"
    bl_label = "Import"
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        save_data.import_pinned_base(context)
        return {"FINISHED"}
    
# button to export data to save file from pinned base
class ExoprtPinnedBase(bpy.types.Operator):
    bl_idname = "object.export_pinned_base"
    bl_label = "Export"
    
    def execute(self, context):
        scene = context.scene
        save_data = scene.nms_save_data
        result = save_data.export_pinned_base(context)
        if result is not None:
            self.report({'INFO'}, result)
        else: print("result is none")
        return {"FINISHED"}

# these classes can be appened to classes list in __init__.py file with + operator  
classes = (
    SelectSaveFolder,
    ImportBaseFromSave,
    ExportBaseToSave,
    PinBase,
    UnpinBase,
    ImportPinnedBase,
    ExoprtPinnedBase
)