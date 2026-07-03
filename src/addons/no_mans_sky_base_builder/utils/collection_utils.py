import bpy


def move_curve_to_collection(curve_obj):
    
    curve_suffix = "_nmsc"
    child_suffix = "_nmscld"
    
    #parent collection of curve
    original_collections = list(curve_obj.users_collection)
    master_col = original_collections[0] if original_collections else bpy.context.scene.collection
    if str(master_col.name).endswith(curve_suffix):
        master_col = get_parent_collection(master_col)
    
    if master_col is None:
        if "master_col" in curve_obj and curve_obj["master_col"] is not None:
            master_col = curve_obj["master_col"]
        else :
            master_col = bpy.context.scene.collection
            
    curve_obj["master_col"] = master_col
    
    #names for new collections to make
    curve_collection_name = f"{curve_obj.name}{curve_suffix}"
    child_collection_name = f"{curve_obj.name}{child_suffix}"
    
    curve_col = bpy.data.collections.get(curve_collection_name)
    #child_col = bpy.data.collections.get(child_collection_name)
    
    # create a collection to house curve and  also house a collection that comtains all children of that curve
    if not curve_col:
        curve_col = bpy.data.collections.new(curve_collection_name)
        curve_col.color_tag = "COLOR_02"
        if curve_col not in master_col.children.values():
            master_col.children.link(curve_col)
        curve_obj["parent_col"] = curve_col
        
    if curve_col not in curve_obj.users_collection:
        curve_col.objects.link(curve_obj)
    
    # remove curve from any other collection
    for col in list(curve_obj.users_collection):
        if col != curve_col:
            col.objects.unlink(curve_obj)
        
    # create a collection to house children of curve and move it inside curve's collection
    #if not child_col:
    #    child_col = bpy.data.collections.new(child_collection_name)
    #    child_col.color_tag = "COLOR_07"
    #    bpy.context.scene.collection.children.link(child_col)
        
    #if child_col not in curve_col.children.values():
    #    curve_col.children.link(child_col)
        
    #remove child collection from any other previous collection to maintain clean hierarchy
    #scene_root = bpy.context.scene.collection
    #if curve_col != scene_root and child_col in scene_root.children.values():
    #    scene_root.children.unlink(child_col)
        
    #for potential_parent in bpy.data.collections:
    #    if potential_parent != curve_col:
    #        if child_col in potential_parent.children.values():
    #            potential_parent.children.unlink(child_col)

        
    return curve_col


# delete a collection and all objects inside it
# it takes a collection as parameter
def delete_collection(collection):
    if not collection:
        print(f"Collection not found.")
        return

    collection_name = collection.name  # Store name before deletion

    # recursively delete sub-collections first
    for child in list(collection.children):
        delete_collection(child)

    # delete all objects inside this specific collection
    for obj in list(collection.objects):
        # Unlink the object from this collection
        collection.objects.unlink(obj)
        
        # Delete object only if it's not used by any other collection
        if len(obj.users_collection) == 0:
            try:
                bpy.data.objects.remove(obj)
            except RuntimeError:
                pass  # Object might be in use, skip it

    # delete the collection itself
    try:
        bpy.data.collections.remove(collection)
        print(f"Successfully deleted collection '{collection_name}' and its contents.")
    except RuntimeError as e:
        print(f"Could not delete collection '{collection_name}': {e}")

# get parent collection of a collection
# it takes a collection as parameter not an object
def get_parent_collection(current_coll):
    if not current_coll:
        return None
        
    # check if it's nested directly under the Scene Master Collection
    scene_root = bpy.context.scene.collection
    if current_coll in scene_root.children.values():
        return scene_root

    # Check all other collections
    for potential_parent in bpy.data.collections:
        if current_coll in potential_parent.children.values():
            return potential_parent

    # If no parent is found,it is orphaned or deleted
    return None


