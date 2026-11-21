"""The material logic other addons can replace.

Other addons can supply their own material logic from their register():

    nms_builder.set_material_provider(MyMaterials())  # MyMaterials subclasses MaterialProvider

and undo it from unregister() with set_material_provider(None).

The rest of the addon never calls this module directly, it goes through the
functions in material.py which forward to the active provider.
"""

import bpy

from . import userdata
from .material import (BAKED_INDEX_COLOURS, GHOSTED_ITEMS,
                       get_nice_name_from_indicies)

__all__ = [
    "MaterialProvider",
    "get_material_provider",
    "set_material_provider",
]


class MaterialProvider:
    """Creates and assigns the materials used by the addon.

    Override only what you need, the other methods go through self so
    replacing validate_material() alone changes every material the addon makes.
    Keep "transparent" in the name of ghosted materials, the ghost toggle
    looks for it.
    """

    def validate_material(self, colour_name, colour_value):
        """Creates or returns a material based on its name.

        Args:
            colour_name (str): The name of the material.
            colour_value (list): RGBA values representing the colour.

        Returns:
            bpy.Material: The Blender material.
        """
        # Retrieve material if it already exists.
        colour_material = bpy.data.materials.get(colour_name, None)
        # Create material.
        if not colour_material:
            colour_material = bpy.data.materials.new(name=colour_name)
            colour_material.diffuse_color = colour_value
        return colour_material

    def set_material(self, item, material):
        """Set the material on an item.

        Args:
            item (bpy.Object): The Blender object to assign the material to.
            material (bpy.Material): The material to assign.

        Returns:
            bpy.Material: The Blender material.
        """
        # Don't bother if we can't even apply material to object.
        if not hasattr(item.data, "materials"):
            return

        # already coloured, skip so a shared mesh isn't copied for nothing
        if item.data.materials and item.data.materials[0] == material:
            return material

        # colour lives on the mesh, so a shared mesh would recolour every part using it
        if item.data.users > 1 and "curve_parent" not in item:
            item.data = item.data.copy()

        # Assign Material
        if not item.data.materials:
            # Add the material to the object
            item.data.materials.append(material)
        else:
            # If a material already exists, swap it.
            item.data.materials[0] = material
        return material

    def assign_power_material(self, item):
        """Assign light blue material to object.

        Args:
            item (bpy.Object): The Blender object to assign the material to.
        """
        material = self.validate_material("powerline_material", [0.0, 0.5, 1.0, 0.5])
        self.set_material(item, material)

    def assign_portal_material(self, item):
        """Assign teal material to object.

        Args:
            item (bpy.Object): The Blender object to assign the material to.
        """
        material = self.validate_material("portalline_material", [0.0, 1.0, 1.0, 0.5])
        self.set_material(item, material)

    def assign_pipe_material(self, item):
        """Assign grey material to object.

        Args:
            item (bpy.Object): The Blender object to assign the material to.
        """
        material = self.validate_material("pipeline_material", [0.3, 0.3, 0.3, 0.9])
        self.set_material(item, material)

    def assign_bytebeat_material(self, item):
        """Assign light purple material to object.

        Args:
            item (bpy.Object): The Blender object to assign the material to.
        """
        material = self.validate_material("bytebeat_material", [0.8, 0.0, 0.8, 0.5])
        self.set_material(item, material)

    def assign_preset_material(self, item):
        """Assign gold material to object.

        Args:
            item (bpy.Object): The Blender object to assign the material to.
        """
        # Material name.
        material_name = "preset_material"
        # Add transparent tag to material name.
        item_name = item.get("ObjectID", "")
        if item_name in GHOSTED_ITEMS:
            material_name += "_transparent"

        material = self.validate_material(material_name, [0.8, 0.300186, 0.178301, 1.0])
        self.set_material(item, material)

    def assign_default_material(self, item, index=0):
        """Given a blender object. Assign the default material,

        Args:
            item (bpy_types.Object): A Blender object.

        Returns:
            bpy_types.Material: The material that is applied.
        """
        # Apply Custom Variable.
        item["UserData"] = str(index)
        # Get colour values.
        colour_values = [0.8, 0.8, 0.8, 1.0]
        # Get or create the material.
        material = self.validate_material("default_material", colour_values)
        self.set_material(item, material)
        return material

    def get_colour_from_palette_data(self, colour_index, material_index):
        """Get colour data from palette data.

        Args:
            index (int): The colour index.
        """
        return BAKED_INDEX_COLOURS.get(colour_index, [0.8, 0.8, 0.8, 1.0])

    def restore_material(self, item, user_data_value):
        # Validate material+color index
        try:
            user_data_value = int(user_data_value)
        except ValueError:
            return
        col = userdata.get_colour(user_data_value)
        mat = userdata.get_material(user_data_value)
        self.assign_material(item, col, mat)

    def assign_material(self, item, colour_index=0, material_index=0):
        """Given a blender object. assign a material and UserData index.

        Args:
            item (bpy_types.Object): A Blender object.
            colour_index (int): The colour index determined by No Man's Sky.
            material (str): The material type.

        Returns:
            bpy_types.Material: The material that is applied.
        """
        # Some Defaults
        alpha_value = 1.0

        # Apply Custom Variable.
        reference_value = int(item.get("UserData", 0))
        new_userdata_value = userdata.update_colour_material(
            reference_value, colour_index=colour_index, material_index=material_index
        )
        item["UserData"] = str(new_userdata_value)

        # Create Material
        colour_name = "{0}_material".format(new_userdata_value)
        # Add transparent tag to material name.
        item_name = item.get("ObjectID", "")
        if item_name in GHOSTED_ITEMS:
            colour_name += "_transparent"

        # Get colour values.
        primary = self.get_colour_from_palette_data(colour_index, material_index)
        if isinstance(primary, str):
            primary = eval(primary)
        # copy so the baked palette entry isn't extended in place
        primary = list(primary)
        if len(primary) < 4:
            primary.append(alpha_value)

        # Get or create the material.
        material = self.validate_material(colour_name, primary)

        # Add Metadata to object.
        nice_name = get_nice_name_from_indicies(colour_index, material_index)
        if nice_name and ":" in nice_name:
            item["readonly:Material"] = nice_name.split(":")[0].strip()
            item["readonly:Colour"] = nice_name.split(":")[1].strip()

        self.set_material(item, material)
        return material


_default_provider = None
_active_provider = None


def get_material_provider():
    global _default_provider, _active_provider
    if _active_provider is None:
        if _default_provider is None:
            _default_provider = MaterialProvider()
        _active_provider = _default_provider
    return _active_provider


def set_material_provider(provider):
    # None restores the addon's own materials
    global _active_provider
    if provider is not None and not isinstance(provider, MaterialProvider):
        raise TypeError("set_material_provider expects a MaterialProvider instance or None")
    _active_provider = provider
