import os
from ..utils import python as python_utils

# load save map that contains collection of only used keys
FILE_PATH = os.path.dirname(os.path.realpath(__file__))
SAVE_MAP_JSON_FILE = os.path.join(FILE_PATH, "save_map_dictionary.json")

#store dictionary in reversed and original order for efficient searching
save_map_dictionary_reversed = python_utils.load_dictionary(SAVE_MAP_JSON_FILE)
save_map_dictionary = {v: k for k, v in save_map_dictionary_reversed.items()}

# helpers to map keys
eng_to_obf_translator = lambda k: save_map_dictionary.get(k, k)
obf_to_eng_translator = lambda k: save_map_dictionary_reversed.get(k, k)

#  translate to english data
def translate_to_eng_data(data):
    return translate_data(data,obf_to_eng_translator)

# translate to obfuscated data
def translate_to_obf_data(data):
    return translate_data(data,eng_to_obf_translator)

#collection of most used keys
class SaveTranslation:
    #hignly used obfuscated strings for traversing save file
    base_context                = eng_to_obf_translator("BaseContext")
    player_state_data           = eng_to_obf_translator("PlayerStateData")
    persistent_player_bases     = eng_to_obf_translator("PersistentPlayerBases")
    base_name                   = eng_to_obf_translator("Name")
    base_type                   = eng_to_obf_translator("BaseType")
    persistent_base_types       = eng_to_obf_translator("PersistentBaseTypes")
    galactic_address            = eng_to_obf_translator("GalacticAddress")
    save_name                   = eng_to_obf_translator("SaveName")
    user_data                   = eng_to_obf_translator("UserData")
    objects                     = eng_to_obf_translator("Objects")
    active_context              = eng_to_obf_translator("ActiveContext")
    expedition_context          = eng_to_obf_translator("ExpeditionContext")
    ship_ownership              = eng_to_obf_translator("ShipOwnership")
    freighter_name              = eng_to_obf_translator("PlayerFreighterName")
    
    
# this function recursively replaces each key in object with respect to mapping provided by translator
def translate_data(obj,translator):
        if isinstance(obj, dict):
            new_dict = {} 
            for key, value in obj.items():
                # Translate the key if it exists in the map, otherwise keep the original
                new_key = translator(key)
                # Recursively process the value (to handle nested dicts/lists)
                new_dict[new_key] = translate_data(value, translator)
                
            return new_dict
        elif isinstance(obj, list):
            # if child is a list, process every item in it
            return [translate_data(item, translator) for item in obj]
        else:
            return obj

