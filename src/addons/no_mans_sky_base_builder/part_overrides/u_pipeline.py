from ..part_overrides import line
from ..utils import material


class U_PIPELINE(line.Line):
    def __init__(self, *args, **kwargs):
        super(U_PIPELINE, self).__init__(*args, **kwargs)
        material.assign_pipe_material(self.object)

    def assign_line_material(self):
        material.assign_pipe_material(self.object)
