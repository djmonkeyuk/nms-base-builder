import no_mans_sky_base_builder.part as part


class BRIDGECONNECTOR(part.Part):
    def __init__(self, bpy_object=None, *args, **kwargs):
        super(BRIDGECONNECTOR, self).__init__(bpy_object=bpy_object, *args, **kwargs)

        # Lock all channels.
        if not bpy_object:
            self.object.lock_location = [True, True, True]
            self.object.lock_rotation = [True, True, True]
            self.object.lock_scale = [True, True, True]

