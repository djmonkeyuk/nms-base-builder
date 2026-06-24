from ..utils import mirror_utils
import bpy
import os
import uuid
from ..utils import blend_utils, curve
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

from mathutils import Vector

class BuildTool(bpy.types.PropertyGroup):
    
    # checkbox to hide/show advanced mirroring options
    check_show_advanced_options: bpy.props.BoolProperty(
        name="Show advanved options",
        description = "Show/Hide advanced mirroring options.",
        default=False,
        options={'SKIP_SAVE'}
    )
    
    # if checked true, auto duplication of objects during mirroring will occur
    check_auto_duplicate: bpy.props.BoolProperty(
        name="Auto duplicate",
        description = (
            "if checked, Perform Mirror button will auto duplicate objects before mirroring action. \n"
            "Helps skip duplication action before mirroring."
            ),
        default=False,
        options={'SKIP_SAVE'}
    )
    
    # direction for mirror in advanced mirroring options
    # There can only be three options X,Y and Z
    mirror_direction: bpy.props.EnumProperty(
        name="Mirror Direction",
        description = "Direction in which mirroring will occur",
        items = [
            ("X", "X", "mirror in X direction"),
            ("Y", "Y", "mirror in Y direction"),
            ("Z", "Z", "mirror in Z direction"),
        ],
        options={'SKIP_SAVE'},
        default = 'X'
    )
    
    # for selecting center of reflection
    # world origin will always be 0,0,0
    # 3d curson can be changed at any time with shift + right click
    # Object can be any object and it's origin will be take in to account for center of reflection
    center_of_reflection: bpy.props.EnumProperty(
        name="Reflection Center",
        description = "Select center of reflection, a point arround which mirroring will take place",
        items = [
            ("World Origin", "World Origin", "World origin will always be 0,0,0","OBJECT_ORIGIN",0),
            ("3D cursor", "3D cursor", "3d curson can be changed at any time with shift + right click","CURSOR",1),
            ("Object", "Object", "An object's origin will be take in to account for center of reflection","CON_PIVOT",2),
        ],
        options={'SKIP_SAVE'},
        default = 'World Origin'
    )
    
    target_object: bpy.props.PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        options={'SKIP_SAVE'},
        description = "This object's origin will be take in to account for center of reflection"
    )
    
    active_curve_gap_percentage : bpy.props.FloatProperty(
        name="Number of Objects",
        default = 0.3,
        update = lambda self, context: self.on_curve_parameter_change(),
        
        min=0.0,       # Absolute lowest value allowed
        max=1.0,      # Absolute highest value allowed
        soft_min=0.01,  # Slider UI floor
        soft_max=0.5   # Slider UI ceiling
    )
    
    active_curve_number_of_objects: bpy.props.IntProperty(
        name="Number of Objects",
        default = 10,
        update = lambda self, context: self.on_curve_parameter_change(),
        
        min=1,       # Absolute lowest value allowed
        max=1000,      # Absolute highest value allowed
        soft_min=5,  # Slider UI floor
        soft_max=500  # Slider UI ceiling
    )
    
    active_curve_radius_multiplier: bpy.props.FloatProperty(
        name="Overall Radius",
        default = 1.0,
        update = lambda self, context: self.on_curve_radius_multiplier_change(),
        
        min=0.0,       # Absolute lowest value allowed
        max=100.0,      # Absolute highest value allowed
        soft_min=0.01,  # Slider UI floor
        soft_max=5.0   # Slider UI ceiling
    )
    
    active_curve_name: bpy.props.StringProperty(
        name="active curve name",
        default = "",
        options={'SKIP_SAVE'},
    )
    
    
    show_gap_edit_field : bpy.props.BoolProperty(
        name="Show gap edit field",
        default=False,
        options={'SKIP_SAVE'},
        #update = lambda self, context: self.on_show_gap_edit_field_change(),
    )
    
    check_pause_curve_link : bpy.props.BoolProperty(
        name="Pause curve link",
        default=False,
        options={'SKIP_SAVE'},
    ) 
    
    selected_curve_object_is_parent: bpy.props.BoolProperty(
        name="Is parent of Child",
        default=True,
        options={'SKIP_SAVE'},
    )
    
        
    def on_curve_radius_multiplier_change(self):
        active = bpy.context.view_layer.objects.active
        curve_obj = curve.get_curve_or_linked_curve(active)
        
        if curve_obj is None: 
            return
        
        original_object_id = curve_obj.get("dup_ObjectID",None)
        if curve_obj and original_object_id:
            curve.update_curve_duplicates(curve_obj, self.active_curve_radius_multiplier)
        
    def on_curve_parameter_change(self):
        active = bpy.context.view_layer.objects.active
        curve_obj = curve.get_curve_or_linked_curve(active)
        
        if curve_obj is None: 
            return
        
        original_object_id = curve_obj.get("dup_ObjectID",None)
        if curve_obj and original_object_id:
            curve.duplicate_along_curve(
                BUILDER, 
                None,
                curve_obj,
                self.active_curve_number_of_objects,
                self.active_curve_radius_multiplier
            )
    
    def mirror(self, axis = None, center = None, change_orientation = False):
        """Mirror the object along X axis (if possible)."""
        # Store selection.
        selected_objects = bpy.context.selected_objects

        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Mirror"
            )
            return

        # Get Selected item.
        new_items = []
        for target in selected_objects:
            # Part
            if "ObjectID" in target:
                object_id = target["ObjectID"]
                mirror_id = part.Part.get_mirror_part_id(object_id)
                
                if self.check_auto_duplicate:
                    new_item = target.copy()
                    new_item.data = target.data.copy()
                    bpy.context.collection.objects.link(new_item)
                else :
                    new_item = target
                
                mirror_part_exist =  mirror_id in nice_name_dictionary.keys()
                
                # Build Item.
                if mirror_part_exist:
                    new_item = BUILDER.mirror_part(target)

                if not change_orientation:
                    mirrored_matrix_world = mirror_utils.mirror_matrix_world_universal(object_id, new_item.matrix_world, axis,center)
                    new_item.matrix_world = mirrored_matrix_world
                else :
                    mirrored_matrix_world = mirror_utils.change_orientation(object_id,new_item.matrix_world, axis, mirror_part_exist)
                    new_item.matrix_world = mirrored_matrix_world
                        
                if hasattr(new_item, "object"):
                    new_items.append(new_item.object)
                else:
                    new_items.append(new_item)
        blend_utils.select(new_items)
        return {"FINISHED"}
    
    # called my Perform Mirror button in advanced mirroring options
    def advanced_mirror(self):
        mirror_direction = self.mirror_direction
        
        # Only mirroring direction is needed if world origin is take as center of reflection
        if self.center_of_reflection == "World Origin":
            self.mirror(axis = mirror_direction, center = Vector((0,0,0)))
        # gather location of active object and use that as center of reflection
        elif self.center_of_reflection == "3D cursor":
            cursor_location = bpy.context.scene.cursor.location
            center = Vector((
                cursor_location.x,
                cursor_location.y,
                cursor_location.z
            ))
            self.mirror(axis = mirror_direction, center = center)
        # target object's origin will be passed here for center of reflection
        elif self.center_of_reflection == "Object":
            if self.target_object:
                center = Vector((
                    self.target_object.location.x,
                    self.target_object.location.y,
                    self.target_object.location.z
                ))
                self.mirror(axis = mirror_direction, center = center)
            else:
                ShowMessageBox(
                    message="Make sure you have target object selected", title="Object Mirror"
                )
                
    def flip(self):
        """Mirror the object along X axis (if possible)."""
        # Store selection.
        selected_objects = bpy.context.selected_objects
        new_items = []
        # Validate
        if not selected_objects:
            ShowMessageBox(message="Make sure you have an item selected.", title="Flip")
            return

        # Get Selected item.
        for target in selected_objects:
            # Part
            if "ObjectID" in target:
                object_id = target["ObjectID"]
                mirror_id = part.Part.get_flip_part_id(object_id)
                new_item = target
                if mirror_id in nice_name_dictionary.keys():
                    # Build Item.
                    new_item = BUILDER.flip_part(target)
                    new_items.append(new_item)

                if hasattr(new_item, "object"):
                    new_items.append(new_item.object)
                else:
                    new_items.append(new_item)

        blend_utils.select(new_items)
        
    def duplicate_along_curve(self, number_of_objects, radius_multiplier = 1.0):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects

        if len(selected_objects) != 2:
            message = (
                "Make sure you have two items selected. Select the item to"
                " duplicate, then the curve you want to snap to."
            )
            ShowMessageBox(message=message, title="Duplicate Along Curve")
            return {"FINISHED"}
        

        # Figure out selection.
        if curve.is_bezier_or_nurbs_path(selected_objects[0]):
            curve_object = selected_objects[0]
            dup_object = selected_objects[1]
        elif curve.is_bezier_or_nurbs_path(selected_objects[1]):
            curve_object = selected_objects[1]
            dup_object = selected_objects[0]
        else : 
            message = (
                "Make sure you have two items selected.\n"
                "One of them must be a curve and other must be object for dupication."
            )
            ShowMessageBox(message=message, title="Duplicate Along Curve")
            return {"FINISHED"}
        
        curve_object["unique_id"] = str(uuid.uuid4())
        curve_object.show_in_front = True
        self.active_curve_radius_multiplier = radius_multiplier
        self.active_curve_number_of_objects = number_of_objects
        self.active_curve_name = curve_object.name
        self.show_gap_edit_field = True
        
        # Perform duplication along curve.
        curve.duplicate_along_curve(
            BUILDER, dup_object, curve_object, number_of_objects,radius_multiplier
        )
        
        # lock all objects on curve so that only curve is selectable
        curve.lock_all_objects(curve_object)
        blend_utils.select(curve_object)
        

    def delete(self):
        """Delete the selected object and everything below."""
        # Store selection.
        selected_objects = bpy.context.selected_objects
        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Select an item to delete from the scene.", title="Delete"
            )
            return

        for item in selected_objects:
            blend_utils.delete(item)

    def duplicate(self):
        """Snaps one object to another based on selection."""
        # Store selection.
        selected_objects = bpy.context.selected_objects

        # Validate
        if not selected_objects:
            ShowMessageBox(
                message="Make sure you have an item selected.", title="Duplicate"
            )
            return

        # Get Selected item.
        target = blend_utils.get_current_selection()

        if "ObjectID" not in target and "PresetID" not in target:
            message = (
                "This item can not be duplicated via the No Man's Sky tool. "
                "Try using Blender hotkey instead (Shift-D)."
            )
            ShowMessageBox(message=message, title="Duplicate")
            return

        # Part
        if "ObjectID" in target:
            object_id = target["ObjectID"]
            user_data = target["UserData"]
            # Build Item.
            new_item = BUILDER.add_part(object_id, user_data=user_data)
            new_item.select()
        if "PresetID" in target:
            preset_id = target["PresetID"]
            # Build Item.
            new_item = BUILDER.add_preset(preset_id)
            new_item.select()

        # Build Rig if need to.
        if hasattr(new_item, "build_rig"):
            new_item.build_rig()
        # Snap.
        target = BUILDER.get_builder_object_from_bpy_object(target)
        new_item.snap_to(target)
        
    def snap(
        self, next_source=False, prev_source=False, next_target=False, prev_target=False
    ):
        """Snaps one object to another based on selection."""
        selected_objects = bpy.context.selected_objects

        source = None
        target = None
        # If only one item is selected, see if it has a snapped to variable to
        # use.
        if len(selected_objects) == 1:
            source = bpy.context.view_layer.objects.active
            if "snapped_to" in source:
                target = bpy.data.objects[source["snapped_to"]]
            else:
                message = (
                    "This item has not been snapped to anything. Please select "
                    "the item you want to snap it to"
                )
                ShowMessageBox(message=message, title="Snap")
                return {"FINISHED"}

        # If 2 are selected, use them as the snapping items.
        elif len(selected_objects) == 2:
            target = bpy.context.view_layer.objects.active
            source = [obj for obj in selected_objects if obj != target][0]

        # If otherwise, we should skip and warn the user.
        else:
            message = (
                "Make sure you have two items selected. Select the item you"
                " want to snap to, then the item you want to snap."
            )
            ShowMessageBox(message=message, title="Snap")
            return {"FINISHED"}

        # Perform Snap
        source = BUILDER.get_builder_object_from_bpy_object(source)
        target = BUILDER.get_builder_object_from_bpy_object(target)
        if source and target:
            source.snap_to(
                target,
                next_source=next_source,
                prev_source=prev_source,
                next_target=next_target,
                prev_target=prev_target,
            )
        
    def show_curve_edit_options(self,curve_obj):
        #if not self.show_gap_edit_field:
        self.show_gap_edit_field = True
        self.active_curve_name = curve_obj.name
        self.active_curve_number_of_objects = curve_obj.get("objects_count",10)
        self.active_curve_radius_multiplier = curve_obj.get("radius_multiplier",1.0)
        

    def hide_curve_edit_options(self):
        #if not self.show_gap_edit_field:
        self.show_gap_edit_field = False

    
    def select_parent_curve(self):
        self.selected_curve_object_is_parent = True
        active_object = bpy.context.active_object
        curve.select_parent_curve(active_object)
        
    def select_children_of_curve(self):
        self.selected_curve_object_is_parent = False
        active_object = bpy.context.active_object
        curve.select_children_of_curve(active_object)