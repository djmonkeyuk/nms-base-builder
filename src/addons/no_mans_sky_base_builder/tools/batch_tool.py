from ..utils import mirror_utils
import bpy
import os
import uuid
from ..utils import blend_utils, curve, material
from ..utils import python as python_utils
from .. import builder, part
from ..utils.mirror_utils import ShowMessageBox

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(FILE_PATH,"..","resources","nice_names.json")

GHOSTED_JSON = os.path.join(FILE_PATH,"..", "resources", "ghosted.json")
ghosted_reference = python_utils.load_dictionary(GHOSTED_JSON)
GHOSTED_ITEMS = ghosted_reference["GHOSTED"]
nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)
BUILDER = builder.Builder()

class BatchTool(bpy.types.PropertyGroup):
    
    nms_batch_replace_type: bpy.props.EnumProperty(
        name="Swap With",
        description="Replace all selected objects with another object of choosing",
        items = [
            ("target", "Target Object", "Replace selected objects with target object chosen"),
            ("object_id", "ObjectId", "Replace selected objects with target ObjectId"),
        ],
        options={'SKIP_SAVE'},
        default = "target"
    )
    
    object_id: bpy.props.StringProperty(
        name="ObjectID",
        description="Enter ObjectID of object you want selections to be replaced with",
        default="",
        maxlen=1024,
    )
    
    target_object: bpy.props.PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        options={'SKIP_SAVE'},
        description = "This object's origin will be take in to account for center of reflection"
    )
    
    color_picker: bpy.props.PointerProperty(
        name="Colour Picker",
        type=bpy.types.Object,
        options={'SKIP_SAVE'},
        description = "Pick an object to use are reference for colouring",
        update = lambda self, context: self.on_color_picked()
    )
    
    def on_color_picked(self):
        target_object = self.color_picker
        if target_object is None:
            return
        
        if "UserData" in target_object:
            target_userdata = target_object["UserData"]
            selected_objects = bpy.context.selected_objects
            for obj in selected_objects:
                material.restore_material(obj, target_userdata)
        self.color_picker = None
        

    def batch_replace_with_target_object(self):
        """Replace all selected objects with duplicates of the target object."""

        selected_objects = list(bpy.context.selected_objects)
        bpy.ops.object.select_all(action='DESELECT')

        if not selected_objects:
            title="Batch Replace Objects"
            message="Make sure you have an item selected."
            ShowMessageBox( message= message, title=title )
            return 0

        if self.nms_batch_replace_type == "target" and not self.target_object:
            title="Batch Replace Objects"
            message="Choose valid a target object to replace the selection with."
            ShowMessageBox( message= message, title=title )
            return 0
        elif self.nms_batch_replace_type == "object_id" and self.object_id not in nice_name_dictionary:
            title="Batch Replace Objects"
            message="Enter a valid ObjectID to replace the selection with."
            ShowMessageBox( message= message, title=title )
            return 0
        

        if self.nms_batch_replace_type == "target":
            target_object = self.target_object
            if "ObjectID" not in target_object:
                title="Batch Replace Objects"
                message="Target Object is Invalid"
                ShowMessageBox(message=message, title=title )
                return 0
        else :
            object_id = self.object_id
            new_obj = BUILDER.add_part(object_id)
            target_object = new_obj.object
        
        replaced_objects_list = []
        objects_to_delete = []
        
        # Get the current active collection to link the new objects to
        current_collection = bpy.context.collection

        for source_object in selected_objects:
            if source_object == target_object:
                continue
            
            if "ObjectID" in source_object:
                # This create a linked duplicate
                replaced_object = target_object.copy()
                if replaced_object.data:
                    replaced_object.data = replaced_object.data.copy()

                # Copy transforms
                replaced_object.matrix_world = source_object.matrix_world.copy()
                # Link the new object to the scene
                current_collection.objects.link(replaced_object)
                
                replaced_objects_list.append(replaced_object)
                objects_to_delete.append(source_object)
            elif "has_linked_objects" in source_object and source_object.get("has_linked_objects", False):
                source_object = curve.replace_curve_object(source_object, target_object)
                replaced_objects_list.append(source_object)
            
        # 5. Batch delete outside the loop using low-level API
        for obj in objects_to_delete:
            bpy.data.objects.remove(obj, do_unlink=True)
            
        if self.nms_batch_replace_type == "object_id":
            bpy.data.objects.remove(target_object, do_unlink=True)
        
        # Select the new objects
        if len(replaced_objects_list) > 0:
            blend_utils.select(replaced_objects_list)
        return len(replaced_objects_list)
    
    
    def select_same_colored_objects(self):
        """Selects objects with same UserData, for easy experimentation with colors"""
        
        selected_objects = bpy.context.selected_objects
        
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Find Objects with same Color"
            )
            return 0
        
        #Gather unique keys from selected obejcts
        keys_to_find = []
        for obj in selected_objects:
            if "ObjectID" not in obj:
                continue
            
            obj_id = obj["ObjectID"]
            user_data = obj["UserData"]
            if (obj_id,user_data) not in keys_to_find:
                keys_to_find.append((obj_id,user_data))
        
        #Iterate through all objects to collect matches with keys_to_find
        found_matches = []
        for obj in bpy.data.objects:
            if "ObjectID" not in obj:
                continue
            
            obj_id = obj["ObjectID"]
            user_data = obj["UserData"]
            
            new_key = (obj_id, user_data)
            if new_key in keys_to_find:
                found_matches.append(obj)
        
        if len(found_matches) > 0:
            blend_utils.select(found_matches)
            
        return len(found_matches) - len(keys_to_find)
    
    
    def select_same_objects(self):
        """Selects objects with same ObjectIDs"""
        
        selected_objects = bpy.context.selected_objects
        
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Select same Objects"
            )
            return 0
        
        #Gather unique keys from selected obejcts
        keys_to_find = []
        for obj in selected_objects:
            if "ObjectID" not in obj:
                continue
            
            obj_id = obj["ObjectID"]
            if obj_id not in keys_to_find:
                keys_to_find.append(obj_id)
        
        #Iterate through all objects to collect matches with keys_to_find
        found_matches = []
        for obj in bpy.data.objects:
            if "ObjectID" not in obj:
                continue
            
            obj_id = obj["ObjectID"]
            if obj_id in keys_to_find:
                found_matches.append(obj)
        
        if len(found_matches) > 0:
            blend_utils.select(found_matches)
            
        return len(found_matches) - len(keys_to_find)
    
    