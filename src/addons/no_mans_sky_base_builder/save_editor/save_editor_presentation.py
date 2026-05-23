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
            pinned_lable = layout.row(align = True)
            pinned_lable.label(text = "Pinned Base/Corvette")
            #unpin button
            pinned_lable.operator("object.nms_unpin_base", icon="UNPINNED", text = "")
            pinned_lable.separator()
            
            pinned_box = layout.box()
            pinned_col = pinned_box.column(align = True)
            #make a row to display name of base, and buttons to import base data and unpin the base
            name_row = pinned_col.row(align = True)
            #name of base
            name_row.label(text=save_data.pinned_base_name, icon="PINNED")
            bookmark_button_row = name_row.row(align=True)
            #imort button
            bookmark_button_row.operator("object.import_pinned_base", icon="IMPORT", text = "")
            
            #display metadata related to pinned base
            bookmark_smaller_col = pinned_col.column(align = True)
            bookmark_smaller_col.scale_y = 0.6
            #display base type
            bookmark_smaller_col.label(text = save_data.get_base_type_string(save_data.pinned_base_type), icon = "DOT")
            #display save slot and last 3 digits of account number for easy recognition
            bookmark_smaller_col.label(text = f"{save_data.pinned_save_slot_name}, (...{save_data.pinned_save_account[-3:]})", icon = "DOT")
            
            # display a big update button as it is gong to be used alot
            pinned_col.separator()
            update_row = pinned_col.row(align = True)
            update_row.scale_y = 1.2
            update_row.operator("object.export_pinned_base", icon="FILE_TICK", text = "Update Save")
            update_row.separator()
            update_col = update_row.column(align = True)
            update_col.scale_x = 1.52
            update_col.operator("object.make_savefile_backup",  icon = "COLLECTION_NEW", text = "")
            pinned_col.prop(save_data,"check_also_update_name")
            
        
        #make a seprate section to display elements related to selecting bases
        save_folder_box = layout.box()
        sf_column = save_folder_box.column(align=True)
        sf_enable_row = sf_column.row(align = True)
        sf_enable_row.label(text = "Select Save", icon = "DISK_DRIVE")
        
        #this row will contain a field where location of save folder is displayed
        if save_data.check_plugin_enabled and save_data.validate_save_folder(context.scene.nms_save_folder_path):
            #button to choose path to save folder
            sf_enable_row.operator( "object.nms_select_save_folder", text="", icon='FILE_FOLDER')
        
        # A button to enable save editor, this will also additional dependencies required when pressed
        sf_enable_row.separator()
        sf_enable_button_row = sf_enable_row.row(align = True)
        sf_enable_button_row.scale_x = 0.7 if not save_data.check_plugin_enabled else 1.0
        sf_enable_icon = "TRIA_DOWN" if not save_data.check_plugin_enabled else "TRIA_UP"
        sf_enable_text = "Enable"  if not save_data.check_plugin_enabled else ""
        sf_enable_button_row.prop(save_data,"check_plugin_enabled",  icon = sf_enable_icon, text = sf_enable_text)
        
         # Select Save
        if save_data.check_plugin_enabled:
            if not save_data.validate_save_folder(context.scene.nms_save_folder_path):
                sf_column.separator()
                sf_column.operator( "object.nms_select_save_folder", text="Select Save Folder", icon='FILE_FOLDER')
            else:
                is_base_data_loaded = save_data.is_base_data_loaded()
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
        
