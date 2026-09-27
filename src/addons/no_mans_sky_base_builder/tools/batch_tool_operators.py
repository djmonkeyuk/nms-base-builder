import bpy

PATTERN_PRESETS = {
    'EVERY_OTHER':      "10",
    'EVERY_THIRD':      "100",
    'EVERY_FOURTH':     "1000",
    'TWO_ON_ONE_OFF':   "110",
    'THREE_ON_ONE_OFF': "1110",
    'ALT_PAIRS':        "1100",
}

class SelectSameColoredObjects(bpy.types.Operator):
    """Select objects with similar colors for easy experimentation."""

    bl_idname = "object.nms_select_same_colors"
    bl_label = "Select same colors"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        batch_tool = scene.nms_batch_tool
        
        found_matches =  batch_tool.select_same_colored_objects()
        self.report({'INFO'}, f"found {found_matches} matches")
        return {"FINISHED"}


class SelectAllSameColoredObjects(bpy.types.Operator):
    """Select every part with the same colour, whatever part it is."""

    bl_idname = "object.nms_select_all_same_colors"
    bl_label = "Select all same colors"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        found_matches = context.scene.nms_batch_tool.select_all_same_colored_objects()
        self.report({'INFO'}, f"found {found_matches} matches")
        return {"FINISHED"}


class SelectSameObjects(bpy.types.Operator):
    """Select objects with similar colors for easy experimentation."""

    bl_idname = "object.nms_select_same_objects"
    bl_label = "Select same colors"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        scene = context.scene
        batch_tool = scene.nms_batch_tool
        
        found_matches =  batch_tool.select_same_objects()
        self.report({'INFO'}, f"found {found_matches} matches")
        return {"FINISHED"}
    

class BatchReplaceTarget(bpy.types.Operator):
    """Replace selected objects with duplicates of the target object."""

    bl_idname = "object.nms_batch_replace_target"
    bl_label = "Batch Replace"
    bl_options = {"UNDO", "REGISTER"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, title="Batch Replace", confirm_text="Replace"
        )

    def execute(self, context):
        batch_tool = context.scene.nms_batch_tool
        replaced_count = batch_tool.batch_replace_with_target_object()
        self.report({'INFO'}, f"replaced {replaced_count} objects")

        # the target is usually removed by the replace, clearing it while the
        # operator is still running makes blender show a warning popup
        def clear_picker():
            batch_tool.target_object = None
            return None

        bpy.app.timers.register(clear_picker, first_interval=0.0)
        return {"FINISHED"}

    def draw(self, context):
        batch_tool = context.scene.nms_batch_tool

        column = self.layout.column(align=True)
        column.label(text="Replace with a", icon="GROUP_VERTEX")
        column.row(align=True).prop(batch_tool, "nms_batch_replace_type", expand=True)
        column.separator()
        if batch_tool.nms_batch_replace_type == "target":
            column.label(text="Replace with a target object")
            column.prop(batch_tool, "target_object", text="")
        else:
            column.label(text="Replace with ObjectId")
            column.prop(batch_tool, "object_id", text="")
        column.separator()
    
    
class BatchSelectRandom(bpy.types.Operator):
    """Select a random percentage of objects"""
    bl_idname = "object.nms_batch_select_random"
    bl_label = "Select Random"
    bl_description = "Randomly select objects"
    bl_options = {'REGISTER', 'UNDO'}

    ratio: bpy.props.FloatProperty(
        name="Selection %",
        description="Percentage of objects to select",
        default=0.50,
        min=0.0,
        max=1.0,
        subtype='FACTOR'
    )

    seed: bpy.props.IntProperty(
        name="Seed",
        default=0,
        min=0
    )

    action: bpy.props.EnumProperty(
        name="Action",
        items=[
            ('SELECT', "Select", "Randomly select objects", 'SELECT_EXTEND', 0),
            ('DESELECT', "Deselect", "Randomly deselect objects", 'SELECT_SUBTRACT', 1),
        ],
        default='SELECT',
    )

    def invoke(self, context, event):
        # Store original selection
        self.original_selection = {
            obj.name for obj in context.selected_objects
        }
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = True 
        
        row = layout.row()
        row.prop(self, "action", expand=True)
        layout.separator()
        
        layout.prop(self, "ratio", text = "Ratio")
        layout.prop(self, "seed", text = "Random Seed")

    def execute(self, context):
        bpy.ops.object.select_random(
            ratio=self.ratio,
            seed=self.seed,
            action=self.action,
        )
        return {'FINISHED'}
    
    
    def check(self, context):
        self.apply_preview(context)
        return True

    def apply_preview(self, context):
        # Restore original selection
        for obj in context.scene.objects:
            obj.select_set(obj.name in self.original_selection)

        bpy.ops.object.select_random(
            ratio=self.ratio,
            seed=self.seed,
            action=self.action,
        )

    def execute(self, context):
        # Preview has already applied the final result
        return {'FINISHED'}

    def cancel(self, context):
        # Restore original selection if dialog is cancelled
        for obj in context.scene.objects:
            obj.select_set(obj.name in self.original_selection)
            
            

class BatchSelectPattern(bpy.types.Operator):
    """Select objects using a repeating pattern"""
    bl_idname = "object.nms_batch_select_pattern"
    bl_label = "Pattern Selection"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        name="Action",
        items=[
            ('SELECT', "Select", ""),
            ('DESELECT', "Deselect", ""),
        ],
        default='SELECT'
    )

    preset: bpy.props.EnumProperty(
        name="Pattern",
        items=[
            ('EVERY_OTHER', "Every Other", ""),
            ('EVERY_THIRD', "Every Third", ""),
            ('EVERY_FOURTH', "Every Fourth", ""),
            ('TWO_ON_ONE_OFF', "2 On, 1 Off", ""),
            ('THREE_ON_ONE_OFF', "3 On, 1 Off", ""),
            ('ALT_PAIRS', "Alternate Pairs", ""),
            ('CUSTOM', "Custom", ""),
        ],
        default='EVERY_OTHER'
    )

    custom_pattern: bpy.props.StringProperty(
        name="Custom Pattern",
        default="1010"
    )

    def invoke(self, context, event):

        self.original_selection = {
            obj.name for obj in context.selected_objects
        }

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        row.prop(self, "action", expand=True)

        layout.separator()

        layout.prop(self, "preset")

        if self.preset == 'CUSTOM':
            layout.prop(self, "custom_pattern")

    def check(self, context):
        self.apply_pattern(context)
        return True

    def execute(self, context):
        return {'FINISHED'}

    def cancel(self, context):

        for obj in context.scene.objects:
            obj.select_set(obj.name in self.original_selection)

    def apply_pattern(self, context):

        # Restore original selection
        for obj in context.scene.objects:
            obj.select_set(obj.name in self.original_selection)

        # Ordered list of currently selected objects
        objects = list(context.selected_objects)

        if not objects:
            return

        if self.preset == 'CUSTOM':
            pattern = "".join(c for c in self.custom_pattern if c in "01")
        else:
            pattern = PATTERN_PRESETS[self.preset]

        if not pattern:
            return
        plen = len(pattern)
        for i, obj in enumerate(objects):
            enabled = pattern[i % plen] == "1"
            if self.action == 'SELECT':
                obj.select_set(enabled)
            else:
                if enabled:
                    obj.select_set(False)


class SelectAllGroups(bpy.types.Operator):
    """Select every group in the scene."""

    bl_idname = "object.nms_select_all_groups"
    bl_label = "Select Groups"
    bl_options = {"UNDO", "REGISTER"}

    def execute(self, context):
        group_count = context.scene.nms_batch_tool.select_all_groups()
        self.report({'INFO'}, f"found {group_count} groups")
        return {"FINISHED"}


classes = (
    SelectSameColoredObjects,
    SelectAllSameColoredObjects,
    SelectSameObjects,
    BatchReplaceTarget,
    BatchSelectRandom,
    BatchSelectPattern,
    SelectAllGroups,
)