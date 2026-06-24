import os
import bpy
import uuid
from . import blend_utils, curve_utils
from . import python as python_utils

from .. import builder, part
BUILDER = builder.Builder()

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(FILE_PATH,"..","resources","nice_names.json")
nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)

def update_curve_duplicates(curve_obj, new_radius_multier = None):
    """Refreshes transformations for all objects assigned to this curve."""
    if not curve_obj.get("has_linked_objects"):
        return
    
    spline = curve_obj.data.splines[0]
    segment_lengths, total_length = curve_utils.get_spline_segment_lengths(spline)
    
    if new_radius_multier is not None:
        curve_obj["radius_multiplier"] = new_radius_multier
        
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            curve_utils.update_obj_transformations(obj, curve_obj, segment_lengths, total_length)
    

def duplicate_along_curve(builder, object, curve, number_of_duplicates=10, radius_multiplier=1.0):
    curve["has_linked_objects"] = True
    curve["radius_multiplier"] = radius_multiplier
    
    if object is not None:
        curve["dup_ObjectID"] = object["ObjectID"]
        curve["dup_UserData"] = object["UserData"]
    
    # Calculate the fractional distance between objects. 
    gap_distance = 0.0 if number_of_duplicates <= 1 else 1.0 / (number_of_duplicates - 1)
    
    # Gather all objects currently following this curve
    existing_objs = [obj for obj in bpy.context.scene.objects if obj.get("curve_parent") == curve.name]
    current_count = len(existing_objs)
    
    # here we check if number of objects needed on curve are more or less than previously duplicated objects.
    # if number objects previously duplicated is more than what we need on curve, we remove extra objects
    if number_of_duplicates < current_count:
        remove_count = current_count - number_of_duplicates
        removed = 0
        
        # Loop backwards through the list to safely pop items without breaking index order
        for i in range(len(existing_objs) - 1, -1, -1):
            if removed >= remove_count:
                break
                
            obj_to_remove = existing_objs[i]
            existing_objs.pop(i)
            bpy.data.objects.remove(obj_to_remove, do_unlink=True)
            removed += 1
                
    # Add additional obejcts if needed to reach desired number of objects
    elif number_of_duplicates > current_count:
        
        object_id = curve["dup_ObjectID"]
        user_data = curve["dup_UserData"]
        
        for _ in range(number_of_duplicates - current_count):
            new_item = builder.add_part(object_id, user_data=user_data)
            new_obj = new_item.object
            
            constraint = new_obj.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True
            
            new_obj["curve_parent"] = curve.name
            new_obj["curve_parent_ref"] = curve
            
            existing_objs.append(new_obj)
            
            new_obj.hide_select = True
            new_obj.lock_location = (True, True, True)

    # calcuate segment_length and total length of curve once
    spline = curve.data.splines[0]
    segment_lengths, total_length = curve_utils.get_spline_segment_lengths(spline)

    # itreate over all objects and update their transformations
    for i, obj in enumerate(existing_objs):
        percentage_count = i * gap_distance
        
        constraint = next((c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve), None)
        if constraint:
            constraint.offset_factor = percentage_count
            
        obj["curve_factor"] = percentage_count
        curve_utils.update_obj_transformations(obj, curve, segment_lengths, total_length)
        
    curve["objects_count"] = len(existing_objs)
    
    return existing_objs

# check if given object is a supported curve or not
def is_bezier_or_nurbs_path(curve):
    if not curve or curve.type != 'CURVE':
        return False
    for spline in curve.data.splines:
        if spline.type in {'BEZIER', 'NURBS'}:
            return True
    return False

        
def apply_curve_transforms_and_detach(curve):
    """
    Bakes the visual transforms created by the FOLLOW_PATH constraint into actual 
    loc/rot/scale data, then deletes the constraint so objects stay in place.
    """
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Please provide a valid curve object.")
    
    detached_count = 0
    duplicates = []
    
    # Force Blender to evaluate the scene tree. 
    # If we don't do this, 'obj.matrix_world' might return stale data from before 
    bpy.context.view_layer.update()
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]
            
            # Clean up custom properties
            if "curve_parent_ref" in obj:
                del obj["curve_parent_ref"]
                
            if "base_scale" in obj:
                del obj["base_scale"]
                
            if "curve_factor" in obj:
                del obj["curve_factor"]
                
            del obj["curve_parent"]
                
            if constraints_to_remove:
                # Capture the exact 3D space matrix dictated by the constraint
                baked_matrix = obj.matrix_world.copy()
                
                for c in constraints_to_remove:
                    obj.constraints.remove(c)
                
                # Re-apply the matrix so the object doesn't physically move when the constraint drops
                obj.matrix_world = baked_matrix
                detached_count += 1
                
            obj.hide_select = False
            obj.lock_location = (False, False, False)
            duplicates.append(obj)
    
    blend_utils.select(duplicates)
    
    # Clean up custom curve properties
    if "has_linked_objects" in curve:
        del curve["has_linked_objects"]
    
    if "dup_ObjectID" in curve:
        del curve["dup_ObjectID"]
        del curve["dup_UserData"]
        
    if "radius_multiplier" in curve:
        del curve["radius_multiplier"]
        
    if "objects_count" in curve:
        del curve["objects_count"]
        
    if "unique_id" in curve:
        del curve["unique_id"]
     
    return detached_count

# make all objects linked ao a curve unselectable
def lock_all_objects(curve_obj, lock_location = True):
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            obj.hide_select = True
            if lock_location:
                obj.lock_location = (lock_location, lock_location, lock_location)
            
# make all objects linked to a curve selectable
def unlock_all_objects(curve_obj, lock_location = False):
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            obj.hide_select = False
            obj.lock_location = (lock_location, lock_location, lock_location)

# select parent curve of object
# make its children unselectable and make only curve selectable
def select_parent_curve(object):
    parent_curve = object.get("curve_parent_ref", None)
    if parent_curve:
        parent_curve.hide_select = False
        lock_all_objects(parent_curve)
        blend_utils.select(parent_curve)
            
# select all children of curve present
# make all children linked to curve selectable and make curve unselectable
def select_children_of_curve(curve):
    if not is_bezier_or_nurbs_path(curve):
        return
    
    children = []
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            obj.hide_select = False
            children.append(obj)
    
    curve.hide_select = True
    blend_utils.select(children)
    
# return objects if object is a curve and has lihked objects
# or object is not curve, check if it is part of a curve, and returh curve linked to it
def get_curve_or_linked_curve(obj):
    if obj is None:
        return None
    
    if is_bezier_or_nurbs_path(obj) and obj.get("has_linked_objects",False):
        return obj
    elif "curve_parent" in obj and "curve_parent_ref" in obj:
        return obj["curve_parent_ref"]
    return None

# delete selected curve and children linked to it
def delete_curve_and_children(curve):
    if curve is None:
        raise TypeError("Selected object is None")
    
    if not is_bezier_or_nurbs_path(curve):
        raise TypeError("Object is not a curve")
    
    if not curve["has_linked_objects"]:
        return TypeError("Object has no linked children")

    deleted_count = 0
    # Delete all linked objects first
    for obj in list(bpy.data.objects):
        if obj.get("curve_parent") == curve.name:
            bpy.data.objects.remove(obj, do_unlink=True)
            deleted_count += 1

    # Delete the curve
    bpy.data.objects.remove(curve, do_unlink=True)

    return deleted_count
    
    
def create_mirrored_curve_copy(original_curve_obj, mirror_axis='X'):
    """
    Duplicates a curve object and applies a pure mathematical mirror to its data.
    """
    if not is_bezier_or_nurbs_path(original_curve_obj):
        return None
    
    # Duplicate the object and its data block so they don't share identical vertices
    new_curve_obj = original_curve_obj
    
    
    #Apply the mathematical mirror
    curve_utils.mirror_curve_data_x(new_curve_obj)
    new_curve_obj.location.x = -new_curve_obj.location.x
    new_curve_obj.rotation_euler.y = -new_curve_obj.rotation_euler.y
    new_curve_obj.rotation_euler.z = -new_curve_obj.rotation_euler.z
    
    mirror_obj_id = part.Part.get_mirror_part_id(new_curve_obj["dup_ObjectID"])
    mirror_part_exist =  mirror_obj_id in nice_name_dictionary.keys()
    if mirror_part_exist:
        new_curve_obj["dup_ObjectID"] = mirror_obj_id
        
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == new_curve_obj.name:
            if mirror_part_exist:
                obj = BUILDER.mirror_part(obj)
            obj.rotation_euler.y = -obj.rotation_euler.y
            obj.rotation_euler.z = -obj.rotation_euler.z
    
    new_curve_obj["unique_id"] = str(uuid.uuid4())
    bpy.context.view_layer.update()
    blend_utils.select(new_curve_obj)
    return new_curve_obj

def sync_curves(target_curve, source_curve):
    
    target_dupe_obejcts = [obj for obj in bpy.context.scene.objects if obj.get("curve_parent") == target_curve.name]
    source_dupe_objects = [obj for obj in bpy.context.scene.objects if obj.get("curve_parent") == source_curve.name]
   
    for index,source in enumerate(source_dupe_objects):
        target = target_dupe_obejcts[index]
        target.rotation_euler = source.rotation_euler.copy()
        target.scale = source.scale.copy()
        
    target_curve["unique_id"] = str(uuid.uuid4())


    