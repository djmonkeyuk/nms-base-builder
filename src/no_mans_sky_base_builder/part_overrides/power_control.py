"""Although the control point is not a base part. 

It's convenient to inherit from Part to get all the snap methods.

We override the object id classes so that it's stored in memory, rather
then on the node itself, so that it doesn't get exported along with everything
else when bringing it back into the game.

"""
import no_mans_sky_base_builder.part as part


class POWER_CONTROL(part.Part):
    def __init__(self, bpy_object=None, builder_object=None, *args, **kwargs):
        self.object = bpy_object
        self.__object_id = bpy_object["SnapID"]
        self.__builder_object = builder_object

    @property
    def builder(self):
        return self.__builder_object
        
    @property
    def object_id(self):
        return self.__object_id

    @object_id.setter
    def object_id(self, value):
        self.__object_id = value
