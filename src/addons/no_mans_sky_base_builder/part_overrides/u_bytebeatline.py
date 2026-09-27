from ..part_overrides import line
from ..utils import material


class U_BYTEBEATLINE(line.Line):
    def __init__(self, *args, **kwargs):
        super(U_BYTEBEATLINE, self).__init__(*args, **kwargs)

        material.assign_bytebeat_material(self.object)

    def assign_line_material(self):
        material.assign_bytebeat_material(self.object)
