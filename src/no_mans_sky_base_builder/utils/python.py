"""Convenient Python related methods."""
import json


def load_dictionary(json_path):
    """Build dictionary from json path.
    
    Args:
        json_path(str): The path to the JSON file.
    
    Returns:
        dict: The dictionary representation of a JSON data set.
    """
    dictionary = {}
    with open(json_path, "r") as stream:
        dictionary = json.load(stream)
    return dictionary


def get_adjacent_dict_key(data, current, step="next"):
    """Get the next key in the dictionary
    
    Args:
        data (dict): The data to inspect.
        current`(str): The current key.
        ste (str): next/prev: The direction in which to look for the next
            key.

    Returns:
        str: The next or previous key.
    ."""
    # Sort the keys by the order sub-key.
    keys = data
    current_index = 0
    if current in keys:
        current_index = keys.index(current)
    if step == "next":
        next_index = current_index + 1
    elif step == "prev":
        next_index = current_index - 1

    if next_index > len(keys) - 1:
        next_index = 0

    if next_index < 0:
        next_index = len(keys) - 1

    return keys[next_index]


def prefer_int(value):
    """Run this method with a value if NMS prefers it to be an int.
    
    Otherwise it returns the string value.
    """
    try:
        converted_value = int(value)
    except BaseException:
        converted_value = value
    return converted_value