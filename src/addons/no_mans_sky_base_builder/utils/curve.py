from . import blend_utils
import bpy
import math

from . import curve_utils

from .. import builder
BUILDER = builder.Builder()

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
    
    # Calculate the fractional distance between objects. 
    gap_distance = 0.0 if number_of_duplicates <= 1 else 1.0 / (number_of_duplicates - 1)

    if object.get("curve_parent") != curve.name:
        object["curve_parent"] = curve.name
        curve["original_object"] = object
        
        object.hide_select = True
        object.lock_location = (True, True, True)
        
        has_constraint = any(c.type == 'FOLLOW_PATH' and c.target == curve for c in object.constraints)
        if not has_constraint:
            constraint = object.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            # use_fixed_location maps the curve length to a normalized 0.0 to 1.0 range.
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True

        # Orient the first object to face the curve direction
        object.rotation_euler = (math.pi/2, 0, 0)

    # Gather all objects currently following this curve
    existing_objs = [obj for obj in bpy.context.scene.objects if obj.get("curve_parent") == curve.name]

    object_id = object["ObjectID"]
    user_data = object["UserData"]
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
            # Protect the original object from being deleted
            if obj_to_remove != object: 
                existing_objs.pop(i)
                bpy.data.objects.remove(obj_to_remove, do_unlink=True)
                removed += 1
                
    # Add additional obejcts if needed to reach desired number of objects
    elif number_of_duplicates > current_count:
        for _ in range(number_of_duplicates - current_count):
            new_item = builder.add_part(object_id, user_data=user_data)
            new_obj = new_item.object
            
            constraint = new_obj.constraints.new(type='FOLLOW_PATH')
            constraint.target = curve
            constraint.use_fixed_location = True
            constraint.use_curve_follow = True
            
            new_obj["curve_parent"] = curve.name
            new_obj["curve_parent_ref"] = curve
            
            new_obj.rotation_euler = object.rotation_euler.copy()
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
    curve["has_linked_objects"] = False
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
    if is_bezier_or_nurbs_path(obj) and obj.get("has_linked_objects",False):
        return obj
    elif "curve_parent" in obj and "curve_parent_ref" in obj:
        return obj["curve_parent_ref"]
    return None
    