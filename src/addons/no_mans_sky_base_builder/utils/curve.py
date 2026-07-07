import os
import bpy
import uuid
import math
from . import blend_utils, curve_utils, collection_utils, material, mirror_utils
from . import python as python_utils
from .. import builder, part

import inspect

BUILDER = builder.Builder()

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(FILE_PATH,"..","resources","nice_names.json")
nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)

def update_curves(updated_curves):
    scene = bpy.context.scene
    for curve_obj in updated_curves:
        properties = scene.nms_properties
        if "has_linked_objects" in curve_obj:
            try:
                if curve_obj.name == properties.active_curve_name:
                    new_radius_multiplier = properties.active_curve_radius_multiplier
                elif "radius_multiplier" in curve_obj:
                    new_radius_multiplier = curve_obj["radius_multiplier"]
                update_curve_children(curve_obj, new_radius_multiplier)
            except ReferenceError:
                continue

# update children on curve
def update_curve_children(curve_obj, new_radius_multier = None):
    """Refreshes transformations for all objects assigned to this curve."""
    if not curve_obj.get("has_linked_objects"):
        return
    
    val_data, total_length = curve_utils.build_curve_eval_data(curve_obj, resolution=64)
    
    if new_radius_multier is not None:
        curve_obj["radius_multiplier"] = new_radius_multier
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve_obj.name:
            curve_utils.update_obj_transformations(obj, curve_obj, val_data, total_length)


def duplicate_along_curve( bpy_object, curve, number_of_duplicates=10, radius_multiplier=1.0):
    curve["has_linked_objects"] = True
    curve["radius_multiplier"] = radius_multiplier
    
    if "initial_curve_scale" not in curve:
        curve["initial_curve_scale"] = curve.scale.x
    
    if bpy_object is not None:
        curve["dup_ObjectID"] = bpy_object["ObjectID"]
        curve["dup_UserData"] = bpy_object["UserData"]
    
    # Calculate the fractional distance between bpy_objects. 
    gap_distance = 1.0 / (number_of_duplicates - 1)
    
    # Gather all bpy_objects currently following this curve
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
        parent_col = curve["parent_col"]
        
        linked_curve_obj_col = collection_utils.get_collection(collection_utils.LINKED_CURVE_OBJ_COL)
        
        for _ in range(number_of_duplicates - current_count):
            if len(existing_objs) == 0:
                
                if bpy_object is None:
                    caller = inspect.stack()[1]
                    print("Called by:", caller.function)
                    print("bulding new object")
                    new_item = BUILDER.add_part(object_id, user_data=user_data)
                    new_obj = new_item.object
                else:
                    new_obj = bpy_object.copy()
                    new_obj.data = bpy_object.data.copy()
                    for constraint in list(new_obj.constraints):
                        new_obj.constraints.remove(constraint)
                
                constraint = new_obj.constraints.new(type='FOLLOW_PATH')
                constraint.target = curve
                constraint.use_fixed_location = True
                constraint.use_curve_follow = True
                
                new_obj["curve_parent"] = curve.name
                new_obj["base_scale"] = 1.0
                new_obj.rotation_euler = (math.pi,0,0)
                new_obj.location = (0,0,0)
                new_obj.hide_select = True
                
                collection_utils.move_object_into_collection(linked_curve_obj_col, new_obj)
                material.restore_material(new_obj, user_data)
                
            else :
                new_obj = existing_objs[-1].copy()
                new_obj["curve_parent"] = curve.name
                linked_curve_obj_col.objects.link(new_obj)
                
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
    
    
    unlinked_curve_obj_col = collection_utils.get_collection(collection_utils.UNLINKED_CURVE_OBJ_COL)
    
    for obj in bpy.context.scene.objects:
        if obj.get("curve_parent") == curve.name:
            constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve]
            
            # Clean up custom properties
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
            
            obj.data = obj.data.copy()
            obj.hide_select = False
            obj.lock_location = (False, False, False)
            duplicates.append(obj)
            
            collection_utils.move_object_into_collection(unlinked_curve_obj_col , obj)
    
    #blend_utils.select(duplicates)
    
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
     
    return curve, duplicates

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
    #curve["initial_curve_scale"] = 1
    
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
    
    # delete colelction containing children and curve     
    collection_utils.delete_collection(curve["parent_col"])
    
    # try deleting the curve if it is outside collection
    try:
        bpy.data.objects.remove(curve, do_unlink=True)
    except Exception as e:
        pass

    return deleted_count

# replace curve objects on curve with source object provided
def replace_curve_object(curve_obj, source_obj):
    
    new_curve_obj = curve_obj.copy()
    new_curve_obj.data = curve_obj.data.copy()
    new_curve_obj["unique_id"] = str(uuid.uuid4())
    
    for collection in curve_obj.users_collection:
        collection.objects.link(new_curve_obj)
    
    new_curve_obj["dup_ObjectID"] = source_obj["ObjectID"]
    new_curve_obj["dup_UserData"] = source_obj["UserData"]
    
    sync_curves(new_curve_obj , curve_obj, duping_object_source= source_obj)
    
    return new_curve_obj, curve_obj

# reset a curve to its default stage and delete all clildren on it
def reset_curve(curve):
    if curve is None:
        raise TypeError("curve is None")
    
    if not is_bezier_or_nurbs_path(curve) or "has_linked_objects" not in curve:
        raise TypeError("object is not a valid curve")
    
    curve_obj, duplciates = apply_curve_transforms_and_detach(curve)
    if duplciates is not None:
        for obj in duplciates:
            bpy.data.objects.remove(obj, do_unlink=True)
    return curve_obj

# mirror a curve and objects dupicated along it
def mirror_curve(curve_obj, axis = "Z", center = None, auto_duplicate = False):
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
                    
    
    #Apply the mathematical mirror to curve objects
    curve_utils.mirror_curve_data(new_curve_obj, axis)
    
    # Mirror positin of curve according to center of reflection
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
    
    # update objectID of mirror part of that object exist
    obj_id = new_curve_obj["dup_ObjectID"]
    mirror_obj_id = part.Part.get_mirror_part_id(obj_id)
    mirror_part_exist =  mirror_obj_id in nice_name_dictionary.keys()
    if mirror_part_exist:
        new_curve_obj["dup_ObjectID"] = mirror_obj_id
    
    # syncing curves will make objects duplicating on them have identical transformations
    sync_curves(new_curve_obj, curve_obj, True, axis, from_mirror= True)
    return new_curve_obj


# this function takes two curves as argument
# iterage over objects of source curve and copy transformations of those objects to their alternatives in target curve
# this in a way creates eact copy of these curves no matter how much obects have been manupulated by user
# do_mirror: this argument dictates if child objects need to be mirrored
# asix: this dictates which direction objects need to be mirrored
# last two objects dictate which function is calling them, 
def sync_curves(target_curve, source_curve, do_mirror = False, axis = None, from_mirror = False, duping_object_source = None):

    target_curve["unique_id"] = str(uuid.uuid4())
    
    # all child objects of source curve
    source_dupe_objects = [obj for obj in bpy.context.scene.objects if obj.get("curve_parent") == source_curve.name]
    
    radius_multiplier = target_curve["radius_multiplier"]
    number_of_objects = target_curve["objects_count"]
    
    if duping_object_source is not None:
        duping_obejct = duping_object_source
    elif len(source_dupe_objects) > 0 and not from_mirror:
        duping_obejct = source_dupe_objects[0]
    else:
        duping_obejct = None
    # all child objects of parent curve
    target_dupe_obejcts = duplicate_along_curve(duping_obejct, target_curve, number_of_objects, radius_multiplier)
    
    if len(target_dupe_obejcts)>0:
        target = target_dupe_obejcts[0]
        material.restore_material(target, target["UserData"])
        
    
    # these curves are almost identical
    # blender stores bpy.context.scene.objects in sorted order, so duplicated objects will alsmo match that order.
    # objects on same index will have save transformations
    for index,source in enumerate(source_dupe_objects):
        if index >= len(target_dupe_obejcts):
            break
        
        target = target_dupe_obejcts[index]
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
    
    
    
    # Refresh evaluation data for the newly synced children
    update_curve_children(target_curve, radius_multiplier)
    
# scale of a child object of curve is mix of multiple products
# base scale is scale of object before getting influenced by curve's points
def calculate_base_scale(curve, obj):
    curve_scale_multiplier = curve.scale.x/curve["initial_curve_scale"]
    radius_multiplier = curve["radius_multiplier"]
    point_radius = obj["radius"]
    return obj.scale.x/( point_radius* radius_multiplier * curve_scale_multiplier )

# change color of objects on curve
def apply_color(curve_obj, user_data):
    
    if curve_obj is None:
        return None
    
    if "has_linked_objects" in curve_obj and is_bezier_or_nurbs_path(curve_obj):
        curve_obj["dup_UserData"] = user_data
        for child_obj in bpy.context.scene.objects:
            if "curve_parent" in child_obj and child_obj["curve_parent"] == curve_obj.name:
                material.restore_material(child_obj, user_data)
                break
