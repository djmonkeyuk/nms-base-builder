import no_mans_sky_base_builder.part_overrides.line as line
import no_mans_sky_base_builder.utils.material as material


class U_PIPELINE(line.Line):
    def __init__(self, *args, **kwargs):
        super(U_PIPELINE, self).__init__(*args, **kwargs)
        material.assign_pipe_material(self.object)