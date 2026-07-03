import os
import json
import struct
import lz4.block
from pathlib import Path
import shutil

from .save_translation import SaveTranslation
from .save_editor_utils import BaseData, BaseType, ShowMessageBox

MAGIC = 0xFEEDA1E5
CHUNK_SIZE = 0x80000  # 524288 bytes

# this handles loading, saving and backup of a hg save file with provided path
class SaveFile:
    
    def __init__(self, path):
        self.path = Path(path)
        self.json_data = None

    # load hg save file
    def load(self):
        with open(self.path, "rb") as f:
            raw = f.read()
        offset = 0
        
        # I dont understand this portion
        decompressed = bytearray()
        while offset < len(raw):
            if offset + 16 > len(raw):
                raise ValueError("Invalid HG block header")
            magic, comp_size, decomp_size, _ = struct.unpack(  "<IIII", raw[offset:offset + 16])
            if magic != MAGIC:
                raise ValueError(f"Invalid magic at offset {offset}: {hex(magic)}")
            offset += 16
            comp_data = raw[offset:offset + comp_size]
            offset += comp_size
            chunk = lz4.block.decompress(comp_data,uncompressed_size=decomp_size)
            decompressed.extend(chunk)

        # FIND JSON SECTION
        data = bytes(decompressed)
        json_start = data.find(b'{')
        json_end = data.rfind(b'}')
        if json_start == -1 or json_end == -1:
            raise ValueError("Could not locate JSON data")
        json_bytes = data[json_start:json_end + 1]

        # safer decoding
        json_text = json_bytes.decode("utf-8", errors="replace")
        self.json_data = json.loads(json_text)
        return self.json_data
    
    # save data to save file
    def save(self, output_path=None):
        if self.json_data is None:
            raise ValueError("No JSON data loaded")

        output_path = output_path or self.path
        json_bytes = json.dumps(
            self.json_data,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")

        blocks = []

        for i in range(0, len(json_bytes), CHUNK_SIZE):
            chunk = json_bytes[i:i + CHUNK_SIZE]
            compressed = lz4.block.compress( chunk, store_size=False)
            header = struct.pack("<IIII",MAGIC,len(compressed),len(chunk),0)
            blocks.append(header + compressed)
        with open(output_path, "wb") as f:
            for block in blocks:
                f.write(block)
             
    # make backup of save file that is changed into a /blender_backup folder which is different from /nms_base_builder_backup folder
    def make_backup(self, output_path = None):
        path  = self.path
        folder = os.path.dirname(path)
        name, ext = os.path.splitext(os.path.basename(path))
        
        backup_folder = os.path.join(
            folder,"blender_backup"
        )
        os.makedirs(backup_folder, exist_ok=True)
        
        backup_file = os.path.join(
            backup_folder,
            f"{name}{ext}.blender.bak"
        )
        shutil.copy2(path, backup_file)

    # seach a paticular property in save file and stop as soon as you find it
    def search_property(self, property):
        offset = 0
        buffer = ""
        with open(self.path, "rb") as f:
            raw = f.read()
        while offset < len(raw):
            if offset + 16 > len(raw):
                raise ValueError("Invalid HG block header")
            magic, comp_size, decomp_size, _ = struct.unpack(  "<IIII", raw[offset:offset + 16])
            if magic != MAGIC:
                raise ValueError(f"Invalid magic at offset {offset}: {hex(magic)}")
            offset += 16
            comp_data = raw[offset:offset + comp_size]
            offset += comp_size
            chunk = lz4.block.decompress(comp_data,uncompressed_size=decomp_size)
            buffer += chunk.decode("utf-8", errors="ignore")
            key = '"'+property+'"'
            if key in buffer:
                i = buffer.find(key)
                snippet = buffer[i:i+200]
                try:
                    return snippet.split(":")[1].split('"')[1]
                except:
                    return None
                
        def cleanup(self):
            self.json_data = None
            
            
    # Return pointer to PersistentPlayerBases List in save data
    def get_bases_list_pointer(self):
        data = self.json_data
        save_type = data[SaveTranslation.active_context]
        key_base_list = SaveTranslation.base_context if save_type == "Main" else SaveTranslation.expedition_context
        return data[key_base_list][SaveTranslation.player_state_data][SaveTranslation.persistent_player_bases]

    # Return pointer to ShipOwnership List in save data
    def get_ship_ownership_pointer(self):
        data = self.json_data
        save_type = data[SaveTranslation.active_context]
        key_base_list = SaveTranslation.base_context if save_type == "Main" else SaveTranslation.expedition_context
        return data[key_base_list][SaveTranslation.player_state_data][SaveTranslation.ship_ownership]

    # Return pointer to PlayerFreighterName in save data
    def get_freighter_name(self):
        data = self.json_data
        save_type = data[SaveTranslation.active_context]
        key_base_list = SaveTranslation.base_context if save_type == "Main" else SaveTranslation.expedition_context
        return data[key_base_list][SaveTranslation.player_state_data][SaveTranslation.freighter_name]
    
    def get_name_from_ship_owsership(self, user_data):
        data = self.json_data
        save_type = data[SaveTranslation.active_context]
        key_base_list = SaveTranslation.base_context if save_type == "Main" else SaveTranslation.expedition_context
        ship_ownsership = data[key_base_list][SaveTranslation.player_state_data][SaveTranslation.ship_ownership]
        return ship_ownsership[user_data][SaveTranslation.base_name]
    
    def get_base_name(self, base):
        
        if base[SaveTranslation.base_type][SaveTranslation.persistent_base_types] == BaseType.FREIGHTER:
            base_name = self.get_freighter_name()
        else:
            base_name = base[SaveTranslation.base_name]
            if base_name == "Default":
                base_name = self.get_name_from_ship_owsership(base[SaveTranslation.user_data])
                
        return base_name
    
    # first check if base exist at an index, if not check for in in bases list
    def search_base_with_identifier(self, base_identifier: BaseData):
        
        base_list = self.get_bases_list_pointer()
        
        #try looking for base in bases list
        try:
            in_base = base_list[base_identifier.base_index]
        except IndexError:
            print("base not found")
            return None
        
        # return base if base found or else iterate over each base to check if it exist somewhere else
        base_found = self.matches_base(in_base,base_identifier)
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
                
                if self.matches_base(base, base_identifier):
                    #since a corvette can be identified with user_data, we return on first match
                    if(base_identifier.base_type == "PlayerShipBase"):
                        return base
                    else:
                        in_bases_list.append(base)
            if in_bases_list is not None:
                if len(in_bases_list) == 1:
                    return in_bases_list[0]
                elif len(in_bases_list) > 1 :
                    ShowMessageBox(message="Multiple bases.corvettes with same name found, try repinnig base/corvette")

        # reaching here means base doesnt exist
        return None
    

    # since there is no unique identifier for a base, we can compare bases by matching their fingerprints
    def matches_base(self, base, identifier : BaseData):
        data = self.json_data
        if base[SaveTranslation.base_type][SaveTranslation.persistent_base_types] == BaseType.FREIGHTER:
            base_name = self.get_freighter_name()
        else:
            base_name = base[SaveTranslation.base_name]
            
        if base_name == "Default":
            base_name = self.get_name_from_ship_owsership(base[SaveTranslation.user_data])
            
        base_tuple = (
            base_name ,
            base[SaveTranslation.base_type][SaveTranslation.persistent_base_types],
            base[SaveTranslation.user_data]
        )
        
        identifier_tuple = (
            identifier.base_name,
            identifier.base_type,
            identifier.user_data
        )
        
        return base_tuple == identifier_tuple
            
            
    