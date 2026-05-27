import bpy
import json
from . import save_editor_utils
from .. import builder
from . import save_editor_dependencies

BUILDER = builder.Builder()

#save data to persist within blend files.
class SaveManager(bpy.types.PropertyGroup):
    
    #array to populate accounts list
    enum_accounts_list = []
    #enum property list to display cave slots list
    
    enum_save_slots_list = []
    #this stores data related to save slot like paths
    data_save_slot = []
    
    #this stores data for displaying list
    enum_base_list = []
    #this stores list of bases, in seperate arrays for both corvetets and normal bases 
    extracted_base_data = {}
    
    #These will track state of UI for easy access
    save_data_loaded= False
    is_base_selected = False
    is_base_list_load_first_time = True
    
    # A toggle button at top of Save Editor section
    check_plugin_enabled: bpy.props.BoolProperty(
        name="Open save editor",
        description="Enable/disbale Plugin, \nClicking will check for dependencies, \nWill take few seconds to load for first time",
        default=False,
        update = lambda self, context: self.on_check_plugin_enabled(),
        options={'SKIP_SAVE'}
    )

    # List to display miltiple accounts on same device
    nms_account_selected: bpy.props.EnumProperty(
        name="",
        description="Account from which save file will be loaded",
        items = lambda self, context: SaveManager.enum_accounts_list,
        update = lambda self, context: self.on_account_list_change(),
        options={'SKIP_SAVE'}
    )
    
    #list of save slots form an account
    nms_save_slot: bpy.props.EnumProperty(
        name="",
        description="Choose a save slot, \nThere can be multiple save slots within an account",
        items = lambda self, context: SaveManager.enum_save_slots_list,
        update = lambda self, context: self.on_save_slot_list_change(),
        options={'SKIP_SAVE'}
    )
    
    # this will display list of corvettes/bases after importing
    # This is index of base inside PersistentPlayerBase array
    # we store index so that it is easier to accress data later
    nms_base_index : bpy.props.EnumProperty(
        name="base index",
        description="Base in the save file.",
        items = lambda self, context: SaveManager.enum_base_list,
        options={'SKIP_SAVE'},
        update = lambda self, context: self.on_base_selected()
    )
    
    # for radio button to select between corvette and base
    nms_base_type: bpy.props.EnumProperty(
        name="base type",
        description="Type of the base, it can be a corvette and a normal planet base.",
        items = [
            ("PlayerShipBase", "Corvette", "show list of corvettes and freighters",'AUTO',0),
            ("HomePlanetBase", "Base", "show list of bases",'HOME',1),
        ],
        update = lambda self, context: self.on_base_type_selected(),
        options={'SKIP_SAVE'},
        default = 'PlayerShipBase'
    )
    
    #these properties will store data of changes made in account and save slot
    last_account_selected:bpy.props.StringProperty(
        name="acocount_selected", default = "Default"
    )
    
    last_slot_selected:bpy.props.StringProperty(
        name="slot_selected", default = "Default"
    )
    
    # this section stores parameters for pinned base which will persist within a blend file
    
    # A check to see if a base is pinned or not
    pinned_base_check:bpy.props.BoolProperty(
        name="base suer_data", default = False
    )
    
    # meta data realated to base goes here and for some fields below
    pinned_base_name:bpy.props.StringProperty(
        name="base name", default = "None"
    )
    
    pinned_base_user_data:bpy.props.IntProperty(
        name="base user_data", default = -1
    )
    
    pinned_base_type:bpy.props.StringProperty(
        name="base type", default = "None"
    )
    
    pinned_base_index:bpy.props.IntProperty(
        name="base index", default =  -1
    )
    
    pinned_base_save_1:bpy.props.StringProperty(
        name="base save line 1", default = "None"
    )
    
    pinned_save_account:bpy.props.StringProperty(
        name="account number", default = "None"
    )
    
    pinned_save_slot_name:bpy.props.StringProperty(
        name="slot name", default = "None"
    )
    
    pinned_base_save_2:bpy.props.StringProperty(
        name="base save link 2", default = "None"
    )
    
    pinned_galactic_address:bpy.props.StringProperty(
        name="galactic address", default = "1"
    )
    
    # A toggle button at top of Save Editor section
    check_also_update_name: bpy.props.BoolProperty(
        name="Also update name",
        description="Use 'Base Name' from Base Properties section as name for this.",
        default=False,
    )
    
    
    #this is called after clicking enable save editor button
    def on_check_plugin_enabled(self):
        save_editor_dependencies.installDependencies()
        SaveManager.enum_accounts_list = self.get_accounts_enum_list()
        
        # set value of accounts from values from last changes
        # check if stored account is present in newly generated list, if yes updated current list's index to it
        for account in SaveManager.enum_accounts_list:
            if account[0] == self.last_account_selected:
                self.nms_account_selected = self.last_account_selected
                break

    #function runs after an account is selected
    def on_account_list_change(self):
        #store save slots list for easy access
        SaveManager.enum_save_slots_list = self.get_save_slots_list()
        
        # these values being eaqual means changes has been made using UI and not due to loading of data
        if self.last_account_selected != self.nms_account_selected :
            #clear any previous records
            self.reset_save_slot()
            self.reset_base_list()
        else :
            # set value of save slot from values from last changes
            # check if stored slot data is present in newly generated list, if yes updated current list's index to it
            for slot in SaveManager.enum_save_slots_list:
                if slot[0] == self.last_slot_selected:
                    self.nms_save_slot = self.last_slot_selected
                    break
        
        # store account selected so that it can be used as default values next time this feature is enabled
        self.last_account_selected = self.nms_account_selected
        
    # function that generates list of accounts to populate UI
    # this is called when save editor is enabled
    def get_accounts_enum_list(self):
        default_account_list_item = ("Default", "Select Account", "No account selected")
        accounts_list = save_editor_utils.get_accounts_list()
        accounts_enum_list = [(str(account), account.name, "") for account in accounts_list]
        accounts_enum_list.insert(0, default_account_list_item)
        return accounts_enum_list
    
    # Called when an update happens Save Slots list UI
    # Extraction of base list from save file happens here
    def on_save_slot_list_change(self):
        self.reset_base_list()
        current_slot_data = self.get_current_slot_data()
        
        if current_slot_data is not None:
            #extract list of corvettes and bases for display in UI
            SaveManager.extracted_base_data = save_editor_utils.extract_bases_list_from_save(current_slot_data["saves"])
            #convert that list to data that can be used by UI
            SaveManager.enum_base_list = self.get_bases_enum_list(SaveManager.extracted_base_data)
            SaveManager.save_data_loaded = True
            self.nms_base_index = "Default"
        
        self.last_slot_selected = self.nms_save_slot 
            
    # Called when account is selected
    # creates List of data for UI of save slots
    def get_save_slots_list(self):
        default_save_slot_list_item = ("Default", "Select Save Slot", "No save slot selected")
        account_selected = self.nms_account_selected
        
        #get list of save slots under selected account
        SaveManager.data_save_slot = save_editor_utils.get_save_slots_list(account_selected)
        
        #convert that list into something that UI can use
        enum_save_slots_list = []
        for slot in SaveManager.data_save_slot:
            save_name = slot["save_name"] 
            slot_list_name = "Slot "+str(slot["slot"])
            if save_name is not None:
                slot_list_name += " : "+save_name
            slot_element = (str(slot["slot"]), slot_list_name, "save slot for importing base/corvette")
            enum_save_slots_list.append(slot_element)
        
        #add a default value at top of the list    
        enum_save_slots_list.insert(0, default_save_slot_list_item)
        return enum_save_slots_list
    
    # Called when radio buttons that represent base type are clicked
    def on_base_type_selected(self):
        #Reset values related to base selected
        SaveManager.is_base_selected = False
        if len(SaveManager.enum_base_list) > 0:
            if len(SaveManager.enum_base_list[0][0]) > 0:
                self.nms_base_index = SaveManager.enum_base_list[0][0]
                
        # change bases list accourding to type of base in UI
        if not self.nms_save_slot == "Default":
            SaveManager.enum_base_list = self.get_bases_enum_list(SaveManager.extracted_base_data)
            

    # called either after base type is selected or save slot is changed
    def get_bases_enum_list(self, extracted_base_data):
        
        # default item to represent top of list, also acts ac propmt for user to interact with
        default_base_list_item = (
            "Default", 
            "Select Corvette" if self.nms_base_type == "PlayerShipBase" else "Select Base", 
            "No base selected"
        )
        
        enum_bases = []
        base_type_key = "corvettes" if self.nms_base_type == "PlayerShipBase" else "bases"
        # convert list of bases into list for UI
        for base_data in extracted_base_data[base_type_key]:
            list_entry = ""
            base_name = base_data["base_name"]
            user_data = str(base_data["user_data"])
            base_index = str(base_data["base_index"])
            if self.nms_base_type == "PlayerShipBase":
                # if base is a corvette, add user_data in front of its name that represents its ingame slot number
                list_entry = f"{user_data.rjust(2)}. {base_name}"
            else :
                list_entry = base_name
            # base index is stored here to make it easier to traverse save file, it is index of base within persistent player bases array
            enum_bases.append((base_index, list_entry, " base desc"))
        
        #add a default value to top of the list
        enum_bases.insert(0, default_base_list_item)
        return enum_bases
    
    # this is called when a base is selected from UI
    # this updates state values accourding to which element of list is selected
    def on_base_selected(self):
        if self.nms_base_index != "Default":
            SaveManager.is_base_selected = True
        else :
            SaveManager.is_base_selected = False
    
    
    # called from a button to imprt selected bas into scene
    def import_base_from_save_file(self,context):
        base_index = self.nms_base_index
        
        # validate base index
        if not str(base_index).isdigit(): return 
        if int(base_index) < 0: return
        
        # validate save slots
        current_slot_data = self.get_current_slot_data()
        if current_slot_data is None:
            return
        
        # validate parameters that identify a base within savefile
        base_identifiers = self.get_current_base_identifiers()
        if base_identifiers is None:
            return
        
        return self.import_base(context,base_identifiers,current_slot_data["saves"])
        
    # called to import objects into scene after validating
    # can be called from anywhere provided correct parameters
    def import_base(self, context, base_identifiers, save_links):
        
        #try to import json data from savefile and return error if data was not found
        newly_imported_base = save_editor_utils.import_paticular_base_from_save(base_identifiers, save_links)
        if newly_imported_base is None:
            return "Error Importing base, base data is None"
        
        try:
            # convert imported base data to json
            nms_import_data = json.dumps(newly_imported_base)
            nms_base_json = json.loads(nms_import_data)
        except:
            return "Could not import base data, Incorrect json"

        # Import json into scene
        nms_tools = context.scene.nms_base_tool
        nms_tools.deserialise_from_data(nms_base_json)
        BUILDER.deserialise_from_data(nms_base_json)
        
        #return a string for operators for status message
        return "Base/Corvette imported sucessfully"
    
    # called from operators/UI to export objects in scene to save file
    def export_base_to_save_file(self,context):
        
        # validate save slots
        current_slot_data = self.get_current_slot_data()
        if current_slot_data is None:
            return "Error Exporting bases, slot data is None"
        
        #collect base identifiers
        base_identifiers = self.get_current_base_identifiers()
        if base_identifiers is None:
            return "Error Exporting bases, base identifiers are None"
        
        # provide data to real export function
        return self.export_base(context, base_identifiers, current_slot_data["saves"])
        
    # collect data from scene and export it to save file
    def export_base(self,context,  base_identifiers, save_links, new_base_name = None):
        # convert scene to json representing base data
        nms_tools = context.scene.nms_base_tool
        serialised_base_objects_data  = nms_tools.serialise(objects_only = True)
        # provide data to utils and return status string to calling function
        return save_editor_utils.save_base_to_save_file(serialised_base_objects_data, base_identifiers, save_links, new_base_name)
      
    # This functin collects data realated to base so that it can be identified in save file
    # since there is no unique property to identify a base, we prepare a fingerprint of that base with collection of properties
    def get_current_base_identifiers(self):
        
        #validate index of base, it is index of base in persistent player base array of save file
        base_index = self.nms_base_index
        if not str(base_index).isdigit():return None
        if int(base_index) < 0:return None
        
        # base type key to access data
        base_type_key = "corvettes" if self.nms_base_type == "PlayerShipBase" else "bases"
        for base in SaveManager.extracted_base_data[base_type_key]:
            if base_index == str(base["base_index"]):
                return base
        
        return None
        
    # Fucntion for UI to check if base list should be displayed or not
    def is_base_data_loaded(self):
        return len(SaveManager.enum_base_list) > 0 and SaveManager.save_data_loaded
      
    # called to get data related to save slot selected
    def get_current_slot_data(self):
        if not self.nms_save_slot == "Default":
            for slot in SaveManager.data_save_slot:
                if str(slot["slot"]) == self.nms_save_slot:
                    return slot
        return None
    
    # called to reset values of save slot
    def reset_save_slot(self):
        SaveManager.save_data_loaded = False
        if SaveManager.enum_save_slots_list is not None:
            if len(SaveManager.enum_save_slots_list) > 0:
                if len(SaveManager.enum_save_slots_list[0][0]) > 0:
                    self.nms_save_slot = "Default"

    # called to reset values for base list
    def reset_base_list(self):
        if SaveManager.enum_base_list is not None:
            if len(SaveManager.enum_base_list) > 0:
                if len(SaveManager.enum_base_list[0][0]) > 0:
                    self.nms_base_index = "Default"
    
    #called by ui to display type of base
    def get_base_type_string(self,base_type = None):
        if base_type is None:
            return "Corvette" if self.nms_base_type == "PlayerShipBase" else "Base"
        else: 
            return "Corvette" if base_type == "PlayerShipBase" else "Base"
        
        
    # called when update base name is checked
    # To update name of base from 'Base Name' field in Base properties panel
    def update_base_name(self, new_base_name):
        
        if not new_base_name:
            return
        
        if not self.pinned_base_check:
            return
        
        #update name of pinned base
        old_base_name = self.pinned_base_name
        self.pinned_base_name = new_base_name
        
        # update name of base in UI lists without reading save file again
        # Changes made with this will be almost identical as reimporting bases list
        # this will improve speed of updating base
        t1 = (old_base_name, self.pinned_base_type, self.pinned_galactic_address)
        if SaveManager.save_data_loaded:
            base_type_key = "corvettes" if self.nms_base_type == "PlayerShipBase" else "bases"
            base_list = SaveManager.extracted_base_data[base_type_key]
            for base in base_list:
                t2 = (base["base_name"],base["base_type"],base["galactic_address"])
                if t1 == t2:
                    base["base_name"] = new_base_name
                    break
            SaveManager.enum_base_list = self.get_bases_enum_list(SaveManager.extracted_base_data)
        
        
                
    # called from operator to pin a base and save its metadata to persist within a blend file
    # it provides easy access to update button for users
    def pin_base(self):
        save_slot_name = self.nms_save_slot
        for slot in SaveManager.enum_save_slots_list:
            if slot[0] == self.nms_save_slot:
                save_slot_name = slot[1]
                break
        
        #collect all the deta form selected base and store it
        identifiers = self.get_current_base_identifiers()
        save_slot = self.get_current_slot_data()
        self.pinned_base_check = True
        self.pinned_base_name = identifiers["base_name"]
        self.pinned_base_index = identifiers["base_index"]
        self.pinned_base_user_data = identifiers["user_data"]
        self.pinned_base_type = identifiers["base_type"]
        self.pinned_galactic_address = str(identifiers["galactic_address"])
        self.pinned_save_account = self.nms_account_selected
        self.pinned_save_slot_name = save_slot_name
        self.pinned_base_save_1 = save_slot["saves"][0]
        self.pinned_base_save_2 = save_slot["saves"][1]
      
    # called from operators to unpin a pinned base
    def unpin_base(self):
        self.pinned_base_check = False
        self.pinned_base_name = "None"
        
    # called from operators to import a pinned base into scene
    def import_pinned_base(self,context):
        base_identifiers = self.get_pinned_base_identifiers()
        if base_identifiers is None:
            print("Pinned base identifiers are none")
            return
        self.import_base(context,base_identifiers, base_identifiers["save_links"])
    
    # called to save scene data to save file
    def export_pinned_base(self, context):
        base_identifiers = self.get_pinned_base_identifiers()
        
        if base_identifiers is None:
            return "Pinned base identifiers are none"
        
        # base name will not be udpated if it is None
        new_base_name = None
        
        # check if export base name check box is checked
        if self.check_also_update_name:
            scene = context.scene
            nms_tool = scene.nms_base_tool
            string_base_name = nms_tool.string_base.strip()
            # update of new base name after validating string base name
            if string_base_name:
                new_base_name = string_base_name
        
        result = self.export_base(context, base_identifiers, base_identifiers["save_links"], new_base_name)
        
        # upate base name if base name was sucessfully changed in save file
        if result is not None and new_base_name is not None:
            self.update_base_name(new_base_name)
            
        return result
        
    # collect data of pinned base and return it
    def get_pinned_base_identifiers(self):
        if self.pinned_base_check == False:
            return None
        
        if self.pinned_base_name == "None":
            return None
        
        return {
            "base_index":self.pinned_base_index,
            "base_name":self.pinned_base_name,
            "user_data":int(self.pinned_base_user_data),
            "galactic_address": self.pinned_galactic_address,
            "base_type":self.pinned_base_type,
            "save_links":[ 
                self.pinned_base_save_1, 
                self.pinned_base_save_2 
            ]
        }

    #function for UI to display metadata realated to pinned base
    def get_pinned_base_location_details(self):
        if self.pinned_base_check:
            return f"{self.pinned_save_slot_name}, acc: ...{self.pinned_save_account[-3:]}"
        return None
        
    # for pinned backup button operator to call, will make backup of pinned base/corvette
    def backup_pinned_save_files(self):
        save_1 = self.pinned_base_save_1
        save_2 = self.pinned_base_save_2
        save_links = [save_1,save_2]
        save_editor_utils.backup_save_files(save_links)
        
    # for backup button operator to call, will make backup of selected save slot
    def backup_save_files(self):
        save_slot = self.get_current_slot_data()
        if save_slot is not None:
            save_links = save_slot["saves"]
            save_editor_utils.backup_save_files(save_links)
            
    def open_backup_folder_in_explorer(self):
        save_slot = self.get_current_slot_data()
        if save_slot is not None:
            save_links = save_slot["saves"]
            save_editor_utils.open_backup_folder_in_explorer(save_links)
        
    # called to check if savefolder path is valid or not 
    def validate_save_folder(self,save_folder):
        return save_editor_utils.validate_save_folder(save_folder)