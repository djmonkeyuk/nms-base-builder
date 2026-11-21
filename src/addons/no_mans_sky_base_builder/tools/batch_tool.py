import bpy

from ..builder import get_builder
from ..group import Group
from ..utils import blend_utils, curve, material
from ..utils.blend_utils import ShowMessageBox


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
        description = "Object the selection is replaced with"
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

    # Replace ---
    def batch_replace_with_target_object(self):
        """Replace all selected objects with duplicates of the target object."""
        selected_objects = list(bpy.context.selected_objects)
        blend_utils.deselect_all()

        title = "Batch Replace Objects"
        if not selected_objects:
            ShowMessageBox(message="Make sure you have an item selected.", title=title)
            return 0

        if self.nms_batch_replace_type == "target":
            target_object = self.target_object
            if target_object is None:
                ShowMessageBox(message="Choose valid a target object to replace the selection with.", title=title)
                return 0
            if "ObjectID" not in target_object and Group.PROP_GROUP_ID not in target_object:
                ShowMessageBox(message="Target Object is Invalid", title=title)
                return 0
            replaced_objects = self.batch_replace(target_object, selected_objects)
        else:
            if self.object_id not in get_builder().nice_name_dictionary:
                ShowMessageBox(message="Enter a valid ObjectID to replace the selection with.", title=title)
                return 0
            replaced_objects = self.batch_replace_with_object_id(self.object_id, selected_objects)

        if not replaced_objects:
            return 0

        try:
            blend_utils.select(replaced_objects)
        except ReferenceError as error:
            print(error)

        return len(replaced_objects)

    def batch_replace_with_object_id(self, object_id, objects_to_replace):
        # a temporary part to copy from, removed once the replace is done
        target_object = get_builder().add_part(object_id).object
        replaced_objects = self.batch_replace(target_object, objects_to_replace)
        bpy.data.objects.remove(target_object, do_unlink=True)
        return replaced_objects

    def batch_replace(self, target_object, objects_to_replace):
        replaced_objects_list = []
        objects_to_delete = []

        # Get the current active collection to link the new objects to
        current_collection = bpy.context.collection

        for source_object in objects_to_replace:
            if source_object is None or source_object == target_object:
                continue

            if "ObjectID" in source_object or Group.PROP_GROUP_ID in source_object:
                replaced_object = target_object.copy()
                # colour lives on the mesh material, so every replacement needs its own mesh
                if replaced_object.data:
                    replaced_object.data = replaced_object.data.copy()

                replaced_object.matrix_world = source_object.matrix_world.copy()
                current_collection.objects.link(replaced_object)

                replaced_objects_list.append(replaced_object)
                objects_to_delete.append(source_object)
            elif source_object.get("has_linked_objects", False):
                new_curve, old_curve = curve.replace_curve_object(source_object, target_object)
                replaced_objects_list.append(new_curve)
                objects_to_delete.append(old_curve)

        # one batch, a remove() per object re-syncs the whole scene each time
        if objects_to_delete:
            bpy.data.batch_remove(objects_to_delete)

        return replaced_objects_list

    # Select ---
    def select_matching(self, get_key, title):
        """Select every object whose key matches one of the selected objects' keys.

        Returns:
            int: How many objects were found beyond the ones already selected.
        """
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            ShowMessageBox(message="Make sure you have an item selected.", title=title)
            return 0

        keys_to_find = set(filter(lambda key: key is not None, (get_key(obj) for obj in selected_objects)))
        found_matches = [obj for obj in bpy.context.view_layer.objects if get_key(obj) in keys_to_find]

        if found_matches:
            blend_utils.select(found_matches)

        return len(found_matches) - len(keys_to_find)

    def select_same_colored_objects(self):
        """Selects parts with the same ObjectID and UserData, for easy experimentation with colors"""
        def get_key(obj):
            if "ObjectID" not in obj:
                return None
            return (obj["ObjectID"], str(obj.get("UserData", 0)))

        return self.select_matching(get_key, "Find Objects with same Color")

    def select_all_same_colored_objects(self):
        """Selects parts with the same UserData, whatever part they are"""
        def get_key(obj):
            if "ObjectID" not in obj:
                return None
            return str(obj.get("UserData", 0))

        return self.select_matching(get_key, "Find Objects with same Color")

    def select_same_objects(self):
        """Selects parts with the same ObjectID and groups with the same GroupID"""
        def get_key(obj):
            return obj.get("ObjectID") or obj.get(Group.PROP_GROUP_ID)

        return self.select_matching(get_key, "Select same Objects")

    def select_all_groups(self):
        found_matches = [obj for obj in bpy.context.view_layer.objects if Group.PROP_GROUP_ID in obj]
        if found_matches:
            blend_utils.select(found_matches)
        return len(found_matches)
