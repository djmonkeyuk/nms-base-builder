from ..utils import mirror_utils
import bpy
import os
import uuid
from ..utils import blend_utils, curve
from ..utils import python as python_utils
from .. import part
from ..utils.blend_utils import ShowMessageBox

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
NICE_JSON = os.path.join(FILE_PATH,"..","resources","nice_names.json")

GHOSTED_JSON = os.path.join(FILE_PATH,"..", "resources", "ghosted.json")
ghosted_reference = python_utils.load_dictionary(GHOSTED_JSON)
GHOSTED_ITEMS = ghosted_reference["GHOSTED"]
nice_name_dictionary = python_utils.load_dictionary(NICE_JSON)

class Properties(bpy.types.PropertyGroup):
    
    # For displaying field to edit number of objects on curve
    active_curve_number_of_objects: bpy.props.IntProperty(
        name="Number of Objects",
        default = 10,
        update = lambda self, context: curve.update_selected_curves(),

        min=1,       # Absolute lowest value allowed
        max=1000,      # Absolute highest value allowed
        soft_min=5,  # Slider UI floor
        soft_max=500  # Slider UI ceiling
    )
    
    # For displaying a field that takes a float value that will be miltiplied over every object on curve
    active_curve_radius_multiplier: bpy.props.FloatProperty(
        name="Overall Radius",
        default = 1.0,
        update = lambda self, context: curve.update_selected_curves(),

        min=0.0,       # Absolute lowest value allowed
        max=100.0,      # Absolute highest value allowed
        soft_min=0.01,  # Slider UI floor
        soft_max=5.0   # Slider UI ceiling
    )

    # slider values at the last curve update, the difference is applied to selected curves
    prev_curve_number_of_objects: bpy.props.IntProperty(default=10)
    prev_curve_radius_multiplier: bpy.props.FloatProperty(default=1.0)

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

    def show_curve_edit_options(self,curve_obj):
        self.show_gap_edit_field = True
        self.active_curve_name = curve_obj.name

        # switching curves must not read as a slider change
        with curve.suspend_updates():
            self.prev_curve_number_of_objects = curve_obj.get("objects_count",10)
            self.prev_curve_radius_multiplier = curve_obj.get("radius_multiplier",1.0)
            self.active_curve_number_of_objects = self.prev_curve_number_of_objects
            self.active_curve_radius_multiplier = self.prev_curve_radius_multiplier

        self.selected_curve_object_is_parent = curve_obj.get("parent_selected", True)

    def hide_curve_edit_options(self):
        self.show_gap_edit_field = False
        self.active_curve_name = ""

    def select_parent_curve(self):
        self.selected_curve_object_is_parent = True
        selected_objects = list(bpy.context.selected_objects)
        active_object = bpy.context.active_object
        if active_object is not None and active_object not in selected_objects:
            selected_objects.append(active_object)

        curves_to_select = []
        for obj in selected_objects:
            if curve.Curve.PROP_CURVE_PARENT not in obj or curve.Curve.PROP_CURVE_ID in obj:
                continue
            parent_curve = curve.select_parent_curve(obj)
            if parent_curve is not None and parent_curve not in curves_to_select:
                curves_to_select.append(parent_curve)

        if curves_to_select:
            blend_utils.select(curves_to_select)

    def select_children_of_curve(self):
        self.selected_curve_object_is_parent = False
        selected_objects = bpy.context.selected_objects

        if any(curve.Curve.PROP_CURVE_ID not in obj for obj in selected_objects):
            ShowMessageBox(
                message="All selected objects are not curves",
                title="Selection Failed"
            )
            return

        children_to_select = []
        for curve_obj in selected_objects:
            children = curve.select_children_of_curve(curve_obj)
            if children:
                children_to_select.extend(children)

        if children_to_select:
            blend_utils.select(children_to_select)

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
        if obj is None:
            return

        curve_obj = curve.get_curve_or_linked_curve(obj)
        if curve_obj is not None:
            self.show_curve_edit_options(curve_obj)
        else: 
            self.hide_curve_edit_options()