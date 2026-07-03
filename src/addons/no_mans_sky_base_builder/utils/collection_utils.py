import bpy

curve_prefix = "(linked-curve) "
curve_unliked_prefix = "(unlinked-curve) "
curve_suffix = "_nmsc"

def move_curve_to_collection(curve_obj):
    
    global curve_prefix 
    global curve_suffix
    
    #parent collection of curve
    master_col = get_parent_collection(curve_obj)
    if str(master_col.name).endswith(curve_suffix):
        master_col = get_parent_collection(master_col)
    
    if master_col is None:
        if "master_col" in curve_obj and curve_obj["master_col"] is not None:
            master_col = curve_obj["master_col"]
        else :
            master_col = bpy.context.scene.collection
            
    curve_obj["master_col"] = master_col
    
    #names for new collections to make
    curve_collection_name = f"{curve_prefix}{curve_obj.name}{curve_suffix}"
    curve_col = bpy.data.collections.get(curve_collection_name)
    
    # create a collection to house curve and  also house a collection that comtains all children of that curve
    if not curve_col:
        curve_col = create_collection(curve_collection_name, "COLOR_02")
        move_collection_into_collection(master_col, curve_col)
        curve_obj["parent_col"] = curve_col
        
    return curve_col

def rename_to_unliked(collection):
    global curve_prefix 
    global curve_unliked_prefix
    if str(collection.name).startswith(curve_prefix):
        new_name = curve_unliked_prefix + collection.name[len(curve_prefix):]
        collection.name = new_name

def  move_object_into_collection(collection, obj):
    if collection not in obj.users_collection:
        collection.objects.link(obj)
    
    # remove curve from any other collection
    for col in list(obj.users_collection):
        if col != collection:
            col.objects.unlink(obj)

def move_collection_into_collection(parent_collection, child_collection):
    if child_collection not in parent_collection.children.values():
            parent_collection.children.link(child_collection)

def create_collection(collection_name, color_tag = None):
    curve_col = bpy.data.collections.new(collection_name)
    if color_tag is not None:
        curve_col.color_tag = "COLOR_02"
        
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

# returns a collectin above a object/collection
# takes both an object and colletion as parameter
def get_parent_collection(item):
    if not item:
        return None
        
    # Case 1: If the item is an Object
    if isinstance(item, bpy.types.Object):
        if item.users_collection:
            # An object can technically be in multiple collections; 
            # this returns the first one it belongs to.
            return item.users_collection[0]
        return None

    # Case 2: If the item is a Collection
    if isinstance(item, bpy.types.Collection):
        # Check if it's nested directly under the Scene Master Collection
        scene_root = bpy.context.scene.collection
        if item in scene_root.children.values():
            return scene_root

        # Check all other collections
        for potential_parent in bpy.data.collections:
            if item in potential_parent.children.values():
                return potential_parent

    # If no parent is found, it is orphaned or deleted
    return None


