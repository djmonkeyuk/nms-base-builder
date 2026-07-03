import os
import bpy
import uuid
import math
from . import blend_utils, curve_utils, collection_utils, material, mirror_utils
from . import python as python_utils
from .. import builder, part

BUILDER = builder.Builder()

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(FILE_PATH,"..","resources","nice_names.json")
nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)


# update children on curve
def update_curve_duplicates(curve_obj, new_radius_multier = None):
    """Refreshes transformations for all objects assigned to this curve."""
    if not curve_obj.get("has_linked_objects"):
        return
    
    # change scale of curve to 1 by multiplying it with points on it
    #if curve_obj.scale.x != 1.0 and curve_obj.get("parent_selected", True):
    #    curve_utils.normalise_curve_scale(curve_obj)
    
    val_data, total_length = curve_utils.build_curve_eval_data(curve_obj, resolution=64)
    
    if new_radius_multier is not None:
        curve_obj["radius_multiplier"] = new_radius_multier
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            curve_utils.update_obj_transformations(obj, curve_obj, val_data, total_length)


def duplicate_along_curve( object, curve, number_of_duplicates=10, radius_multiplier=1.0):
    curve["has_linked_objects"] = True
    curve["radius_multiplier"] = radius_multiplier
    
    if "initial_curve_scale" not in curve:
        curve["initial_curve_scale"] = curve.scale.x
    
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
        
        curve_col = collection_utils.move_curve_to_collection(curve)
        
        mater_col = curve["master_col"]
        parent_col = curve["parent_col"]
        
        
        for _ in range(number_of_duplicates - current_count):
            
            if len(existing_objs) == 0:
                
                last_rotation_euler = (math.pi,0,0)
                last_position = (0,0,0)
                base_scale = 1.0
                
                new_item = BUILDER.add_part(object_id, user_data=user_data)
                new_obj = new_item.object
                
                constraint = new_obj.constraints.new(type='FOLLOW_PATH')
                constraint.target = curve
                constraint.use_fixed_location = True
                constraint.use_curve_follow = True
                
                new_obj["curve_parent"] = curve.name
                new_obj["base_scale"] = base_scale
                new_obj.rotation_euler = last_rotation_euler
                new_obj.location = last_position
                new_obj.hide_select = True
                
                if curve_col not in new_obj.users_collection:
                    curve_col.objects.link(new_obj)
                    
                for col in list(new_obj.users_collection):
                    if col != curve_col:
                        col.objects.unlink(new_obj)

                material.restore_material(new_obj, user_data)
                
            else :
                new_obj = existing_objs[-1].copy()
                parent_col.objects.link(new_obj)
                
            
            existing_objs.append(new_obj)

    # calcuate segment_length and total length of curve once
    val_data, total_length = curve_utils.build_curve_eval_data(curve, resolution=64)

    # itreate over all objects and update their transformations
    for i, obj in enumerate(existing_objs):
        percentage_count = i * gap_distance
        
        constraint = next((c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve), None)
        if constraint:
            constraint.offset_factor = percentage_count
            
        obj["curve_factor"] = percentage_count
        curve_utils.update_obj_transformations(obj, curve, val_data, total_length)
        
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
    
    renamed_child_collection = False
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]
            
            # Clean up custom properties
            if "base_scale" in obj:
                del obj["base_scale"]
                
            if "curve_factor" in obj:
                del obj["curve_factor"]
                
            if "child_col" in obj:
                if not renamed_child_collection:
                    child_col = obj["child_col"]
                    child_col.name = f"(unlinked-children) {child_col.name}"
                    renamed_child_collection = True
                del obj["child_col"]
                
            if "parent_col" in obj:
                del obj["parent_col"]
                
            if "master_col" in obj:
                del obj["master_col"]
                
            del obj["curve_parent"]
                
            if constraints_to_remove:
                # Capture the exact 3D space matrix dictated by the constraint
                baked_matrix = obj.matrix_world.copy()
                
                for c in constraints_to_remove:
                    obj.constraints.remove(c)
                    
                # Re-apply the matrix so the object doesn't physically move when the constraint drops
                obj.matrix_world = baked_matrix
                detached_count += 1
            
            obj.data = obj.data.copy()
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
        
    if "parent_col" in curve:
        parent_col = curve["parent_col"]
        collection_utils.rename_to_unliked(parent_col)
        del curve["parent_col"]
        
    if "master_col" in curve:
        del curve["master_col"]
     
    return detached_count

# make all objects linked ao a curve unselectable
def lock_all_objects(curve_obj, lock_location = True):
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            obj.hide_select = True
            #if lock_location:
                #obj.lock_location = (lock_location, lock_location, lock_location)
            
# make all objects linked to a curve selectable
def unlock_all_objects(curve_obj, lock_location = False):
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            obj.hide_select = False
            #obj.lock_location = (lock_location, lock_location, lock_location)

# select parent curve of object
# make its children unselectable and make only curve selectable
def select_parent_curve(object):
    parent_curve_name = object.get("curve_parent", None)
    if parent_curve_name is None:
        return
    
    parent_curve = bpy.data.objects.get(parent_curve_name)
    if parent_curve is not None:
        parent_curve.hide_select = False
        parent_curve["parent_selected"] = True
        for obj in bpy.context.scene.objects:
            if obj.get("curve_parent") == parent_curve.name:
                obj.hide_select = True
                #obj.lock_location = (True, True, True)
                #obj["base_scale"] = obj.scale.x/(parent_curve["radius_multiplier"]*obj["radius"])
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
            
    curve_utils.normalise_curve_scale(curve)
    curve["initial_curve_scale"] = 1
    
    curve.hide_select = True
    curve["parent_selected"] = False
    blend_utils.select(children)
    
# return objects if object is a curve and has lihked objects
# or object is not curve, check if it is part of a curve, and returh curve linked to it
def get_curve_or_linked_curve(obj):
    if obj is None:
        return None
    
    if is_bezier_or_nurbs_path(obj) and obj.get("has_linked_objects",False):
        return obj
    elif "curve_parent" in obj:
        return bpy.data.objects.get(obj["curve_parent"])
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

def mirror_curve(curve_obj, axis = "Z", center = None, auto_duplicate = False):
    """
    Duplicates a curve object and applies a pure mathematical mirror to its data.
    """
    if not is_bezier_or_nurbs_path(curve_obj):
        return None
    
    # Duplicate the object and its data block so they don't share identical vertices
    if auto_duplicate:
        new_curve_obj = curve_obj.copy()
        new_curve_obj.data = curve_obj.data.copy()
        new_curve_obj["unique_id"] = str(uuid.uuid4())
        if "parent_col" in curve_obj and curve_obj.get("parent_col") is not None:
            collection = curve_obj["parent_col"]
            collection.objects.link(new_curve_obj)
        else:
            bpy.context.collection.objects.link(new_curve_obj)
    else:
        new_curve_obj = curve_obj
                    
    
    #Apply the mathematical mirror
    curve_utils.mirror_curve_data(new_curve_obj, axis)
    
    location = new_curve_obj.location
    if axis == "X":
        new_curve_obj.location.x  = mirror_utils.reflect_point_across(location.x, center.x)
        new_curve_obj.rotation_euler.y *= -1
        new_curve_obj.rotation_euler.z *= -1
    elif axis == "Y":
        new_curve_obj.location.y = mirror_utils.reflect_point_across(location.y, center.y)
        new_curve_obj.rotation_euler.x *= -1
        new_curve_obj.rotation_euler.z *= -1
    elif axis == "Z":
        new_curve_obj.location.z = mirror_utils.reflect_point_across(location.z, center.z)
        new_curve_obj.rotation_euler.x *= -1
        new_curve_obj.rotation_euler.y *= -1
    
    obj_id = new_curve_obj["dup_ObjectID"]
    mirror_obj_id = part.Part.get_mirror_part_id(obj_id)
    mirror_part_exist =  mirror_obj_id in nice_name_dictionary.keys()
    
    if mirror_part_exist:
        new_curve_obj["dup_ObjectID"] = mirror_obj_id
        
    sync_curves(new_curve_obj, curve_obj, True, axis)
    return new_curve_obj


def sync_curves(target_curve, source_curve, do_mirror = False, axis = None):
    
    radius_multiplier = target_curve["radius_multiplier"]
    number_of_objects = target_curve["objects_count"]
     
    
    target_dupe_obejcts = duplicate_along_curve(None, target_curve, number_of_objects, radius_multiplier)   
    source_dupe_objects = [obj for obj in bpy.context.scene.objects if obj.get("curve_parent") == source_curve.name]
   
    for index,source in enumerate(source_dupe_objects):
        if index >= len(target_dupe_obejcts):
            break
        
        target = target_dupe_obejcts[index]
        #if not do_mirror:
        #    target.data = source.data.copy()
            
        target.rotation_euler = source.rotation_euler.copy()
        target.scale = source.scale.copy()
        target.location = source.location.copy()
        target["base_scale"] = source["base_scale"]
            
        if do_mirror:
            target.location.x = -target.location.x
            target.rotation_euler.y = -target.rotation_euler.y
            target.rotation_euler.z = -target.rotation_euler.z
            
            if axis is not None and axis == "Z":
                target.rotation_euler.x += math.pi
                target.rotation_euler.z += math.pi
            
    target_curve["unique_id"] = str(uuid.uuid4())
    

def calculate_base_scale(curve, obj):
    curve_scale_multiplier = curve.scale.x/curve["initial_curve_scale"]
    radius_multiplier = curve["radius_multiplier"]
    point_radius = obj["radius"]
    return obj.scale.x/( point_radius* radius_multiplier * curve_scale_multiplier )
    





    