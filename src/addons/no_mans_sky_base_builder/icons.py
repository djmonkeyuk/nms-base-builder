import bpy
import bpy.utils.previews
import os
import json


preview_collections = {}

def extract_pcoll():
    """Reads the JSON file and loads icons into the Blender preview collection."""
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir,"resources","icons.json")
    
    # Initialize a new preview collection
    pcoll = bpy.utils.previews.new()
    
    # Load the JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    base_path = data['base_path']
    icons = data['icons']
    
    # Resolve the absolute path to the icons directory
    icons_dir = os.path.normpath(os.path.join(current_dir,"images","icons"))
    
    # Iterate through the JSON and load each icon
    for icon_name, icon_filename in icons.items():
        icon_path = os.path.join(icons_dir, icon_filename)
        
        # Safety check to ensure the file exists before loading
        if not os.path.exists(icon_path):
            print(f"Warning: Icon not found at {icon_path}")
            continue
            
        # Load the image into the preview collection
        pcoll.load(icon_name, icon_path, 'IMAGE')
        
    # Store the collection in our global dictionary under a specific key
    return pcoll

def get_icons_pscroll():
    return preview_collections["ui_icons"]

def register_icons():
    pcoll = extract_pcoll()
    
    icon_dir = os.path.join(os.path.dirname(__file__), "images","plugin_icon.png")
    pcoll.load("plugin_icon", icon_dir, 'IMAGE')
    
    preview_collections["ui_icons"] = pcoll


def unregister_icons():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()