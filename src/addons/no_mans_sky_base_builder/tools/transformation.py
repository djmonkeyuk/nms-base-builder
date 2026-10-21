import math

import bpy


def get_active_object():
    view_layer = getattr(bpy.context, "view_layer", None)
    return view_layer.objects.active if view_layer else None


# the scale field edits the active object's x, y and z together
def get_uniform_scale(self):
    active_object = get_active_object()
    return active_object.scale.x if active_object is not None else 1.0


def set_uniform_scale(self, value):
    active_object = get_active_object()
    if active_object is not None:
        active_object.scale = (value, value, value)


class Transformation(bpy.types.PropertyGroup):

    uniform_scale: bpy.props.FloatProperty(
        name="Scale",
        get=get_uniform_scale,
        set=set_uniform_scale,
        min=0.0,
        precision=6,
    )

    # drawn in place of location and rotation when there is no active object
    placeholder_vector: bpy.props.FloatVectorProperty(
        default=(0.0, 0.0, 0.0),
        size=3,
        options={'SKIP_SAVE'},
    )

    # transformations stored by Copy, applied to the selection by the paste buttons
    copied_position: bpy.props.FloatVectorProperty(
        name="Copied Location",
        default=(0.0, 0.0, 0.0),
        size=3,
    )

    copied_rotation: bpy.props.FloatVectorProperty(
        name="Copied Rotation",
        default=(0.0, 0.0, 0.0),
        size=3,
    )

    copied_scale: bpy.props.FloatVectorProperty(
        name="Copied Scale",
        default=(1.0, 1.0, 1.0),
        size=3,
    )

    def copy_transformations(self, obj):
        self.copied_position = obj.location
        self.copied_rotation = obj.rotation_euler
        self.copied_scale = obj.scale

    def paste_transformations(self, objects, location=False, rotation=False, scale=False):
        for obj in objects:
            if location:
                obj.location = self.copied_position
            if rotation:
                obj.rotation_euler = self.copied_rotation
            if scale:
                obj.scale = self.copied_scale

    @staticmethod
    def reset_transformations(objects):
        for obj in objects:
            # parts are built lying on their side, upright is 90 degrees on x
            x_rotation = math.pi / 2 if "ObjectID" in obj else 0.0
            obj.rotation_euler = (x_rotation, 0.0, 0.0)
            obj.scale = (1.0, 1.0, 1.0)
