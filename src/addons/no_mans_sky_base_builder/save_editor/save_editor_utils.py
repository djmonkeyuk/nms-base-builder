import os
import bpy
import platform
import subprocess
import sys
from pathlib import Path
import shutil
from datetime import datetime
import re


from . import save_translation
from .save_translation import SaveTranslation


# called to display messages/notificatoin
def ShowMessageBox(message="", title="Message Box", icon="INFO"):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
    
# return save folder path for different OS versions
def get_root_save_folder():
    system = platform.system()
    if system == "Windows":
        # windows
        return (Path.home()/ "AppData/Roaming/HelloGames/NMS" )
    elif system == "Darwin":
        # macOS
        return (Path.home()/ "Library/Application Support/HelloGames/NMS" )
    elif system == "Linux":
        # Proton / Steam Play
        return (Path.home() / ".steam/steam/steamapps/compatdata" )
    else:
        ShowMessageBox(message="Manually select save folder", title= "Default sve folder not found")
        return Path.home()

#returns list of files with valid save file names within a given folder, parameter is string
def get_hg_files_in_folder(folder):
    hg_files_list = []
    for file in Path(folder).glob("save*.hg"):
        if re.fullmatch(r"save(\d+)?\.hg", file.name):
            hg_files_list.append(file)
    return hg_files_list

#Returns all account folders
def get_accounts_list():
    accounts_list = []
    root_dir = Path(bpy.context.scene.nms_save_folder_path)
    for folder in root_dir.iterdir():
        if not folder.is_dir():
            continue
        # Steam/Gamepass account folders
        if folder.name.startswith("st_"):
            files_list = get_hg_files_in_folder(str(folder))
            if files_list is not None:
                if len(files_list) > 0:
                    accounts_list.append(folder)
    return accounts_list
    

# Returns list of save slot data that contains save name and save files lines
def get_save_slots_list(account):
    from .save_file import SaveFile
    
    # to validate correct save file name
    pattern = re.compile(r"save(\d+)\.hg")
    # store list of all hg save files
    hg_files_list = get_hg_files_in_folder(account)
    
    # interate through each save file and record their pairs
    save_slots = []
    for save_2 in hg_files_list:
        
        # save type is "Main" for normal save and "Season" for expeditiion
        save_type = SaveFile(save_2).search_property(SaveTranslation.active_context)
        if save_type != "Main":
            continue
        
        # validate name of save file
        match = pattern.fullmatch(save_2.name)
        if not match:
            continue
        
        #extract number from name of save file
        file_number = int(match.group(1))
        if file_number %2 == 1:
            continue
        
        #name of linked save file
        save_1_name = "save.hg" if file_number == 2 else f"save{file_number - 1}.hg"
        save_1 = Path(save_2.parent / save_1_name )
        #check if linked save file exits in save folder or not
        save_1_found = next((p for p in hg_files_list if p == save_1), None)
        if not save_1_found:
            continue
        
        #slot number is always half of second save file's number
        save_slot_number = file_number//2
        #links to save files for this slot
        saves_links = [str(save_1), str(save_2)]
        #extract save's name from save file data by partially loading it, and increasing efficiency
        save_name = SaveFile(save_2).search_property(SaveTranslation.save_name)
        
        save_slot = {
            "slot": save_slot_number,
            "saves": saves_links,
            "save_name": save_name
        }
        save_slots.append(save_slot)
        
    #sort list according to slot number
    save_slots.sort(key=lambda x: x["slot"])
    return save_slots  

# returns list of data related to bses present in a save slot
def extract_bases_list_from_save(save_slot):
    save_file = get_save_file(save_slot)
    data = save_file.load()
    
    obfuscated_persistent_base_data = data[SaveTranslation.base_context][SaveTranslation.player_state_data][SaveTranslation.persistent_player_bases]
    
    bases = []
    corvettes = []
    
    #record only what is necessary rather than entire data about base
    for index,base in enumerate(obfuscated_persistent_base_data):
        
        in_base_type = base[SaveTranslation.base_type][SaveTranslation.persistent_base_types]
        
        if in_base_type == "ExternalPlanetBase":
            break
        
        base_data = {
            "base_index":index,
            "base_name":base[SaveTranslation.base_name],
            "user_data":base[SaveTranslation.user_data],
            "galactic_address": str(base[SaveTranslation.galactic_address]),
            "base_type":in_base_type,
            "save_links":[ save_slot[0], save_slot[1] ]
        }
        #store list of corvettes and bases in their respective list
        if in_base_type == "PlayerShipBase":
            corvettes.append(base_data)
        elif in_base_type == "HomePlanetBase":
            bases.append(base_data)
    
    # sort list of corvettes with restpect to their user_data, because user_data represents location of corvette in ship slots making it wasy to read
    corvettes.sort(key=lambda x: x["user_data"])
    
    # return combined list in an object for easy search
    return {
        "corvettes":corvettes,
        "bases":bases
    }
    
    
# active save is most recently modified save file
def get_lastes_save_file_location(save_slot):
    save_1 = Path(save_slot[0])
    save_2 = Path(save_slot[1])
    
    # store when last time these save files were modified
    m_time_save_1 = os.path.getmtime(save_1)
    m_time_save_2 = os.path.getmtime(save_2)
    
    # return the save file that was most recently modified
    return save_1 if m_time_save_1 > m_time_save_2 else save_2

# since there is no unique identifier for a base, we can compare bases by matching their fingerprints
def matches_base(base, identifier):
    base_tuple = (
        base[SaveTranslation.base_name] ,
        base[SaveTranslation.base_type][SaveTranslation.persistent_base_types],
        base[SaveTranslation.user_data]
    )
    identifier_tuple = (
        identifier["base_name"],
        identifier["base_type"],
        identifier["user_data"]
    )
    
    return ( base_tuple == identifier_tuple)
    
# helper function that gives returns save file object for easier loading
def get_save_file(save_slot):
    save_location = get_lastes_save_file_location(save_slot)
    from .save_file import SaveFile
    save_file = SaveFile(save_location)
    return save_file

# first check if base exist at an index, if not check for in in bases list
def search_base_with_identifier(data, base_identifier):
    base_list = data[SaveTranslation.base_context][SaveTranslation.player_state_data][SaveTranslation.persistent_player_bases]
    
    #try looking for base in bases list
    try:
        in_base = base_list[base_identifier["base_index"]]
    except IndexError:
        print("base not found")
        return None
    
    # return base if base found or else iterate over each base to check if it exist somewhere else
    base_found = matches_base(in_base,base_identifier)
    if base_found:
        return in_base
    else:
        # There can be multiple bases with same names and user_data,
        # if base is not found on original index recorded try to search it on other places
        # if multiple bases with same names are detected we ask user to repin the base to avoid writing over unintend base
        in_bases_list = []
        for base in base_list:
            
            #break loop when ecternal bases start coming as the are always at bottom of list
            if base[SaveTranslation.base_type][SaveTranslation.persistent_base_types] == "ExternalPlanetBase":
                break
            
            if matches_base(base, base_identifier):
                #since a corvette can be identified with user_data, we return on first match
                if(base_identifier["base_type"] == "PlayerShipBase"):
                    return base
                else:
                    in_bases_list.append(base)
        if in_bases_list is not None:
            if len(in_bases_list) == 1:
                return in_bases_list[0]
            elif len(in_bases_list) > 1 :
                ShowMessageBox(message="Multiple bases.corvettes with same name found, try repinnig base/corvette")
            else:
                message = (
                    "Base couldn't be saved, \n"
                    "Re-pinning may resolve this issue."
                )
                ShowMessageBox(message = message, title="Export Failed", icon = "WARNING_LARGE")
    # reaching here means base doesnt exist
    return None

# impart a base from save file
def import_paticular_base_from_save(base_identifier,  save_slot):
    save_file = get_save_file(save_slot)
    data = save_file.load()
    
    # fist see if base actially exists or not
    searched_base = search_base_with_identifier(data, base_identifier)
    if searched_base is None:
        return None
        
    #return bases after translating it to engish
    return save_translation.translate_to_eng_data(searched_base)
    
#save a base to save file
def save_base_to_save_file(objects_data, base_identifier,  save_slot, new_base_name = None):
    save_file = get_save_file(save_slot)
    data = save_file.load()
    
    # look for base in save file to see it it exist or not
    in_base = search_base_with_identifier(data, base_identifier)
    if in_base is None:
        return
    
    # here update objects list with list provided
    in_base[SaveTranslation.objects] = save_translation.translate_to_obf_data(objects_data)
    
    
    # update name of base if provided
    if new_base_name is not None:
        in_base[SaveTranslation.base_name] = new_base_name
    
    # save the file and make backup after update it
    save_file.make_backup()
    save_file.save()
    return "Base/Corvette saved sucessfully"

# a folder within save_directory , where backups will be stored
def get_backups_folder(save_links):
    folder = os.path.dirname(save_links[0])
    backup_folder = os.path.join(
        folder,"nms_base_builder_backup",
    )
    #create backup folder if it doesnt exist
    os.makedirs(backup_folder, exist_ok=True)
    return backup_folder

# make backup of both save files linked to a save slot
def backup_save_files(save_links):
    backup_folder = get_backups_folder(save_links)
    # add date and time in bakcup file's name to make make manual searching easier
    dat_and_time = datetime.now().strftime("d-%Y-%m-%d_t-%H-%M-%S-%f")[:-3]
    
    
    save_1 = save_links[0]
    save_2 = save_links[1]
    s1_name, s1_ext = os.path.splitext(os.path.basename(save_1))
    s2_name, s2_ext = os.path.splitext(os.path.basename(save_2))
    
    save_1_backup = os.path.join(
        backup_folder,
        f"{s1_name}{s1_ext}.{dat_and_time}.blender.bak"
    )
    save_2_backup = os.path.join(
        backup_folder,
        f"{s2_name}{s2_ext}.{dat_and_time}.blender.bak"
    )
    
    #make exact copies of those sace files and just change names
    shutil.copy2(save_1, save_1_backup)
    shutil.copy2(save_2, save_2_backup)
    
# Open backup for each OS type
def open_backup_folder_in_explorer(save_links):
    backup_folder = Path(get_backups_folder(save_links))

    if not backup_folder.exists():
        print(f"Folder does not exist: {backup_folder}")
        return

    if sys.platform == "win32": #windows
        os.startfile(backup_folder)
    elif sys.platform == "darwin":  # macOS
        subprocess.Popen(["open", str(backup_folder)])
    else:  # Linux
        subprocess.Popen(["xdg-open", str(backup_folder)])
    
    
def validate_save_folder(save_folder):
    save_folder = Path(save_folder)
    return save_folder.parts[-2:] == ("HelloGames", "NMS")
    
    
