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

class Properties(bpy.types.PropertyGroup):
    
    # For displaying field to edit number of objects on curve
    active_curve_number_of_objects: bpy.props.IntProperty(
        name="Number of Objects",
        default = 10,
        update = lambda self, context: self.on_curve_parameter_change(),
        
        min=1,       # Absolute lowest value allowed
        max=1000,      # Absolute highest value allowed
        soft_min=5,  # Slider UI floor
        soft_max=500  # Slider UI ceiling
    )
    
    # For displaying a field that takes a float value that will be miltiplied over every object on curve
    active_curve_radius_multiplier: bpy.props.FloatProperty(
        name="Overall Radius",
        default = 1.0,
        update = lambda self, context: self.on_curve_radius_multiplier_change(),
        
        min=0.0,       # Absolute lowest value allowed
        max=100.0,      # Absolute highest value allowed
        soft_min=0.01,  # Slider UI floor
        soft_max=5.0   # Slider UI ceiling
    )
    
    # For displaying name of target curve selected
    active_curve_name: bpy.props.StringProperty(
        name="active curve name",
        default = "",
        options={'SKIP_SAVE'},
    )
    
    # check to see if curve related options should be shown or not
    show_gap_edit_field : bpy.props.BoolProperty(
        name="Show gap edit field",
        default=False,
        options={'SKIP_SAVE'},
        #update = lambda self, context: self.on_show_gap_edit_field_change(),
    )
    
    # to show respective options when curve is switched to objects or curve mode
    selected_curve_object_is_parent: bpy.props.BoolProperty(
        name="Is parent of Child",
        default=True,
        options={'SKIP_SAVE'},
    )
    
    active_object = None
    
    #active_object_pos_x : bpy.props.FloatProperty(name="X", default = 0.0)
    #active_object_pos_y : bpy.props.FloatProperty(name="y", default = 0.0)
    #active_object_pos_z : bpy.props.FloatProperty(name="z", default = 0.0)
    
    #active_object_rot_x : bpy.props.FloatProperty(name="X", default = 0.0)
    #active_object_rot_y : bpy.props.FloatProperty(name="y", default = 0.0)
    #active_object_rot_z : bpy.props.FloatProperty(name="z", default = 0.0)
    
    #active_object_scale : bpy.props.FloatProperty(name="scale", default = 1.0)
    
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
                None,
                curve_obj,
                self.active_curve_number_of_objects,
                curve_obj.get("radius_multiplier",1.0)
            )
    
    def show_curve_edit_options(self,curve_obj):
        self.show_gap_edit_field = True
        self.active_curve_name = curve_obj.name
        self.active_curve_number_of_objects = curve_obj.get("objects_count",10)
        self.active_curve_radius_multiplier = curve_obj.get("radius_multiplier",1.0)
        self.selected_curve_object_is_parent = curve_obj["parent_selected"]

    def hide_curve_edit_options(self):
        self.show_gap_edit_field = False
        self.active_curve_name = ""
    
    def select_parent_curve(self):
        self.selected_curve_object_is_parent = True
        active_object = bpy.context.active_object
        curve.select_parent_curve(active_object)
        
    def select_children_of_curve(self):
        self.selected_curve_object_is_parent = False
        active_object = bpy.context.active_object
        curve.select_children_of_curve(active_object)
        
    def active_curve_is_highlighted(self):
        selected_objects = bpy.context.selected_objects
        active_object = bpy.context.view_layer.objects.active
        active_curve_name = self.active_curve_name
        if "has_linked_objects" in active_object:
            for obj in selected_objects:
                if obj.name == active_curve_name:
                    return True
        elif "curve_parent" in active_object:
            for obj in selected_objects:
                if obj.name == active_object.name:
                    return True
        
        
        for obj in selected_objects:
            if obj.name == active_curve_name:
                return True
        return False
    
    def set_active_obect(self, obj):
        curve_obj = curve.get_curve_or_linked_curve(obj)
        if curve_obj is not None:
            self.show_curve_edit_options(curve_obj)
        else: 
            self.hide_curve_edit_options()