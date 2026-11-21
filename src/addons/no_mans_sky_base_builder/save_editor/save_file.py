import os
import re
import json
import struct
import lz4.block
from pathlib import Path
import shutil

from .save_translation import SaveTranslation
from .save_editor_utils import BaseData, BaseType
from ..utils.blend_utils import ShowMessageBox

MAGIC = 0xFEEDA1E5
CHUNK_SIZE = 0x80000  # 524288 bytes

# turn the raw bytes between a json string's quotes into text, resolving escapes like \" and \n
def decode_json_string(raw):
    try:
        return json.loads(b'"' + raw + b'"')
    except ValueError:
        return raw.decode("utf-8", errors="replace")

# write a file so that it is either fully replaced or left untouched, never half written
# data goes to a temporary file next to it first, which is then swapped in with a single rename
def write_file_atomic(path, data):
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        with open(temp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        # the original file is still intact, only the temporary file needs removing
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise

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
    
    # compress loaded data into the bytes of a hg save file, without touching the disk
    def pack(self):
        if self.json_data is None:
            raise ValueError("No JSON data loaded")

        json_bytes = json.dumps(
            self.json_data,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8") + b"\x00"

        blocks = []

        for i in range(0, len(json_bytes), CHUNK_SIZE):
            chunk = json_bytes[i:i + CHUNK_SIZE]
            compressed = lz4.block.compress( chunk, store_size=False)
            header = struct.pack("<IIII",MAGIC,len(compressed),len(chunk),0)
            blocks.append(header + compressed)
        return b"".join(blocks)

    # save data to save file
    def save(self, output_path=None):
        write_file_atomic(Path(output_path or self.path), self.pack())

    # make backup of save file that is changed into a /blender_backup folder which is different from /nms_base_builder_backup folder
    # returns path of the backup
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
        return backup_file

    # search string properties in save file, decompressing one block at a time and stopping as soon as all are found
    # returns {property: value}, value is None for properties that were not found
    def search_properties(self, properties):
        patterns = {
            prop: re.compile(rb'"' + re.escape(prop.encode("utf-8")) + rb'"\s*:\s*"((?:[^"\\]|\\.)*)"')
            for prop in properties
        }
        found = {prop: None for prop in properties}
        buffer = bytearray()
        with open(self.path, "rb") as f:
            while patterns:
                header = f.read(16)
                if not header:
                    break
                if len(header) < 16:
                    raise ValueError("Invalid HG block header")
                magic, comp_size, decomp_size, _ = struct.unpack("<IIII", header)
                if magic != MAGIC:
                    raise ValueError(f"Invalid magic in {self.path.name}: {hex(magic)}")
                buffer += lz4.block.decompress(f.read(comp_size), uncompressed_size=decomp_size)

                # a value split across two blocks will not match yet, and is picked up after the next block
                for prop, pattern in list(patterns.items()):
                    match = pattern.search(buffer)
                    if match:
                        found[prop] = decode_json_string(match.group(1))
                        del patterns[prop]
        return found

    # seach a paticular property in save file and stop as soon as you find it
    def search_property(self, property):
        return self.search_properties([property])[property]


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
    
    # Return pointer to ShipOwnership Element in save data
    def get_ship_ownsership_element(self, userdata):
        ship_ownsership_pointer = self.get_ship_ownership_pointer()
        if userdata < 0 or len(ship_ownsership_pointer) >= userdata:
            print(f"UserData = {userdata} , value is invalid")
            return None
        return ship_ownsership_pointer[userdata]

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
    
    
            
            
    