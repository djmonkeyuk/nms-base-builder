import bpy
from bpy.types import Panel
from .save_manager import SaveManager

# Save Editor Panel ---
class NMS_PT_save_editor_panel(Panel):
    bl_idname = "NMS_PT_save_editor_panel"
    bl_label = "Save Manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "No Mans Sky Base Builder"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        save_data = context.scene.nms_save_data
        
        #display data related to a pinned base on top if there is any withing a blend file
        if save_data.pinned_base_check:
            layout.label(text = "Pinned Base/Corvette")
            bookmark_box = layout.box()
            bookmark_col = bookmark_box.column(align = True)
            
            #make a row to display name of base, and buttons to import base data and unpin the base
            name_row = bookmark_col.row(align = True)
            #name of base
            name_row.label(text=save_data.pinned_base_name, icon="BOOKMARKS")
            bookmark_button_row = name_row.row(align=True)
            #imort button
            bookmark_button_row.operator("object.import_pinned_base", icon="IMPORT", text = "")
            bookmark_button_row.separator()
            #unpin button
            bookmark_button_row.operator("object.nms_unpin_base", icon="UNPINNED", text = "")
            
            #display metadata related to pinned base
            bookmark_smaller_col = bookmark_col.column(align = True)
            bookmark_smaller_col.scale_y = 0.6
            #display base type
            bookmark_smaller_col.label(text = save_data.get_base_type_string(save_data.pinned_base_type), icon = "DOT")
            #display save slot and last 3 digits of account number for easy recognition
            bookmark_smaller_col.label(text = f"{save_data.pinned_save_slot_name}, (...{save_data.pinned_save_account[-3:]})", icon = "DOT")
            
            # display a big update button as it is gong to be used alot
            bookmark_col.separator()
            update_row = bookmark_col.row(align = True)
            update_row.scale_y = 1.2
            update_row.operator("object.export_pinned_base", icon="FILE_TICK", text = "Update Save")
            bookmark_col.prop(save_data,"check_also_update_name")
            
        
        #make a seprate section to display elements related to selecting bases
        save_folder_box = layout.box()
        sf_column = save_folder_box.column(align=True)
        sf_enable_row = sf_column.row(align = True)
        sf_enable_row.label(text = "Select Save", icon = "DISK_DRIVE")
        # A button to enable save editor, this will also additional dependencies required when pressed
        sf_enable_row.prop(save_data,"check_plugin_enabled",  icon = "TRIA_DOWN", text = "")
        
         # Select Save
        if save_data.check_plugin_enabled:
            is_base_data_loaded = save_data.is_base_data_loaded()
            sf_column.separator()
            #this row will contain a field where location of save folder is displayed
            savefile_col = sf_column.row(align=True)
            #display part to save folder
            savefile_col.prop(context.scene, "nms_save_folder_path")
            #button to choose path to save folder
            savefile_col.separator()
            savefile_col.operator( "object.nms_select_save_folder", text="", icon='FILE_FOLDER')
            
            sf_column.separator()
            #display list of accounts, will display steam ids for recognition
            sf_column.prop(save_data, "nms_account_selected", icon = "USER")
            #display save slots present within an account
            sf_column.prop(save_data, "nms_save_slot", icon = "SORTSIZE")

            #Section where bases can be selected to import/update/pin
            #this section will only be visible when base list has been loaded
            if is_base_data_loaded:
                sf_column.separator()
                se_column = sf_column.column(align = True)
                
                #radio buttons to select type of base
                base_type_row = se_column.row(align=True)
                base_type_row.prop(save_data, "nms_base_type",expand=True, text = "base type")
                se_column.separator()
                
                #list of bases/corvettes
                base_index_row = se_column.row(align = True)
                base_index_row.scale_y = 1.5
                base_index_row.prop(save_data, "nms_base_index", text="", icon = "GEOMETRY_SET")
                
                #display buttons when a base is selected from list
                if SaveManager.is_base_selected:
                    import_export_row = se_column.row(align=True)
                    #Import button, this button will import base to scene and also pin it for easy access
                    import_export_row.operator("object.nms_import_base_from_save", icon="IMPORT", text = "Import")
                    #Pin button, pin a base without imorting it to scene, so that save data can be updated to location marked by it
                    import_export_row.operator("object.nms_pin_base", icon="PINNED", text = "Pin")
                
                #layout.prop(context.scene, "nms_check_export_name")
        
