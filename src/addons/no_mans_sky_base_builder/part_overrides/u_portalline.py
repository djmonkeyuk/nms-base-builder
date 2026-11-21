from ..part_overrides import line
from ..utils import material


class U_PORTALLINE(line.Line):
    def __init__(self, *args, **kwargs):
        super(U_PORTALLINE, self).__init__(*args, **kwargs)
        material.assign_portal_material(self.object)

    def assign_line_material(self):
        material.assign_portal_material(self.object)
