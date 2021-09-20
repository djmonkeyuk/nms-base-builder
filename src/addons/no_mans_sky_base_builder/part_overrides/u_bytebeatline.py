import no_mans_sky_base_builder.part_overrides.line as line
import no_mans_sky_base_builder.utils.material as material


class U_BYTEBEATLINE(line.Line):
    def __init__(self, *args, **kwargs):
        super(U_BYTEBEATLINE, self).__init__(*args, **kwargs)

        material.assign_bytebeat_material(self.object)
