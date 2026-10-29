from .. import part
from ..utils import pipe_utils


class BASE_BUBPIPE(part.Part):
    """The bubble duct model is centred, it is moved so it shows where the game puts it."""

    def retrieve_object_from_id(self, object_id):
        bpy_object = super(BASE_BUBPIPE, self).retrieve_object_from_id(object_id)
        # duplicates share the mesh, so only the first one moves it
        pipe_utils.move_to_game_frame(bpy_object)
        return bpy_object
