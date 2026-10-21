import json
import os
import uuid

import bpy

from ..builder import paths

SIMPLIFIED_WORKSPACE_NAME = "No Man's Sky Base & Corvette Builder"

# deleted workspaces are backed up here, blender can't bring a deleted workspace back
BACKUP_PATH = os.path.join(paths.USER_PATH, "workspace_backups")


# Workspace Cleanup
# simplify blender to one workspace for base building
# returns json of everything changed, used by restore_workspace
def cleanup_workspace(context):
    layout_ws = bpy.data.workspaces.get("Layout")
    if layout_ws is None:
        return None

    win = context.window
    state = {
        "layout_name": layout_ws.name,
        "active_workspace": win.workspace.name if win.workspace else layout_ws.name,
        "deleted_workspaces": [],
        "backup_file": None,
        "statusbar": {screen.name: screen.show_statusbar for screen in bpy.data.screens},
        "properties": snapshot_properties_areas(),
        "timeline_closed": False,
    }

    # snapshot list before iterating because collection changes during deletion
    other_workspaces = [ws for ws in bpy.data.workspaces if ws != layout_ws]
    if other_workspaces:
        state["deleted_workspaces"] = [ws.name for ws in other_workspaces]
        state["backup_file"] = backup_workspaces(other_workspaces)

    for ws in other_workspaces:
        with bpy.context.temp_override(workspace=ws):
            bpy.ops.workspace.delete()

    # switch to layout and rename it
    win.workspace = layout_ws
    layout_ws.name = SIMPLIFIED_WORKSPACE_NAME

    # remove timeline area from bottom of layout workspace
    state["timeline_closed"] = remove_timeline_area(win)
    # remove extra tabs from properties panel
    simplify_object_properties()

    # hide status bar
    for screen in bpy.data.screens:
        screen.show_statusbar = False

    # trim the viewport toolbar down to what base building uses
    hide_viewport_tools(context)

    return json.dumps(state)


# undo cleanup_workspace using the state it returned
def restore_workspace(context, state_json):
    try:
        state = json.loads(state_json) if state_json else {}
    except ValueError:
        state = {}

    restore_viewport_tools()

    win = context.window
    layout_ws = bpy.data.workspaces.get(SIMPLIFIED_WORKSPACE_NAME) or win.workspace
    if layout_ws is not None:
        layout_ws.name = state.get("layout_name", "Layout")

    restore_backed_up_workspaces(win, state)

    if layout_ws is not None:
        win.workspace = layout_ws

    if state.get("timeline_closed", True):
        add_timeline_area(win)

    restore_properties_areas(state.get("properties", []))

    saved_statusbar = state.get("statusbar", {})
    for screen in bpy.data.screens:
        screen.show_statusbar = saved_statusbar.get(screen.name, True)

    # go back to the workspace that was open before simplifying
    active_ws = bpy.data.workspaces.get(state.get("active_workspace", ""))
    if active_ws is not None:
        win.workspace = active_ws


# Workspace Backup
# save workspaces to a blend file, returns its path
def backup_workspaces(workspaces):
    os.makedirs(BACKUP_PATH, exist_ok=True)
    backup_file = os.path.join(BACKUP_PATH, "{}.blend".format(uuid.uuid4()))
    if bpy.app.version >= (5, 1, 0):
        bpy.data.libraries.write(backup_file, set(workspaces), compress=True)
    else:
        # libraries.write crashes blender 4.5 when given workspaces or screens,
        # a copy of the whole file holds them too
        bpy.ops.wm.save_as_mainfile(filepath=backup_file, copy=True, compress=True)
    return backup_file


# add backed up workspaces back as normal workspace tabs, then delete the backup
def restore_backed_up_workspaces(win, state):
    backup_file = state.get("backup_file")
    if not backup_file or not os.path.isfile(backup_file):
        return

    for name in state.get("deleted_workspaces", []):
        if name in bpy.data.workspaces:
            continue
        with bpy.context.temp_override(window=win):
            bpy.ops.workspace.append_activate(idname=name, filepath=backup_file)

    try:
        os.remove(backup_file)
    except OSError:
        pass


# Areas
# close every timeline area, returns True if one was closed
def remove_timeline_area(win):
    screen = win.screen
    # snapshot first, closing an area changes screen.areas
    timeline_areas = [
        area for area in screen.areas
        if area.type == "DOPESHEET_EDITOR" and area.spaces.active.mode == "TIMELINE"
    ]
    for area in timeline_areas:
        with bpy.context.temp_override(window=win, screen=screen, area=area):
            bpy.ops.screen.area_close()
    return bool(timeline_areas)


# split the biggest 3d viewport and turn its lower part into a timeline
def add_timeline_area(win):
    screen = win.screen
    if any(area.type == "DOPESHEET_EDITOR" and area.spaces.active.mode == "TIMELINE" for area in screen.areas):
        return

    view3d_area = max(
        (area for area in screen.areas if area.type == "VIEW_3D"),
        key=lambda area: area.width * area.height,
        default=None,
    )
    if view3d_area is None:
        return

    areas_before = set(screen.areas)
    with bpy.context.temp_override(window=win, screen=screen, area=view3d_area):
        bpy.ops.screen.area_split(direction="HORIZONTAL", factor=0.15)

    new_areas = [area for area in screen.areas if area not in areas_before]
    if not new_areas:
        return

    # the split leaves two areas, the lower one becomes the timeline
    split_areas = new_areas + [view3d_area]
    timeline_area = min(split_areas, key=lambda area: area.y)
    for area in split_areas:
        area.type = "VIEW_3D"
    timeline_area.type = "DOPESHEET_EDITOR"
    timeline_area.spaces.active.mode = "TIMELINE"


# yields (screen name, index, area) for every properties area in every window
def get_properties_areas():
    for window in bpy.context.window_manager.windows:
        if not window.screen:
            continue
        properties_areas = [area for area in window.screen.areas if area.type == "PROPERTIES"]
        for index, area in enumerate(properties_areas):
            yield window.screen.name, index, area


# record the visible tabs and active tab of every properties area
def snapshot_properties_areas():
    snapshot = []
    for screen_name, index, area in get_properties_areas():
        space = area.spaces.active
        if not space:
            continue
        snapshot.append({
            "screen": screen_name,
            "index": index,
            "context": space.context,
            "tabs": {attr: getattr(space, attr) for attr in dir(space) if attr.startswith("show_properties_")},
        })
    return snapshot


def restore_properties_areas(snapshot):
    saved = {(entry["screen"], entry["index"]): entry for entry in snapshot}
    for screen_name, index, area in get_properties_areas():
        space = area.spaces.active
        entry = saved.get((screen_name, index))
        if not space:
            continue

        tabs = entry["tabs"] if entry else {}
        for attr in dir(space):
            if attr.startswith("show_properties_"):
                try:
                    setattr(space, attr, tabs.get(attr, True))
                except (AttributeError, TypeError):
                    pass

        if entry:
            try:
                space.context = entry["context"]
            except TypeError:
                pass
        area.tag_redraw()


# hide every properties tab except object
def simplify_object_properties():
    for _screen_name, _index, area in get_properties_areas():
        space = area.spaces.active
        if not space:
            continue

        for attr in dir(space):
            if attr.startswith("show_properties_"):
                try:
                    setattr(space, attr, False)
                except AttributeError:
                    pass

        # there is no object tab when no object is selected
        try:
            space.show_properties_object = True
            space.context = 'OBJECT'
        except TypeError:
            pass

        area.tag_redraw()


# Toolbar Cleanup
# tools removed from the 3d viewport toolbar, none of them are used for base building
HIDDEN_VIEW3D_TOOLS = {
    "builtin.annotate",
    "builtin.annotate_line",
    "builtin.annotate_polygon",
    "builtin.annotate_eraser",
    "builtin.measure",
    "builtin.primitive_cube_add",
    "builtin.primitive_cone_add",
    "builtin.primitive_cylinder_add",
    "builtin.primitive_uv_sphere_add",
    "builtin.primitive_ico_sphere_add",
    # the breakdowner button, in object mode since blender 5.2
    "builtin.breakdowner",
    "builtin.push",
    "builtin.relax",
}

# blender's own VIEW3D_PT_tools_active.tools_from_context, kept to restore the toolbar
ORIGINAL_TOOLS_FROM_CONTEXT = None


# drop hidden tools from toolbar entries
# an entry is None (separator), a ToolDef, a tuple of ToolDefs or a callable
def strip_tool_items(items):
    result = []
    for item in items:
        if item is None:
            # only keep a separator that follows something kept
            if result and result[-1] is not None:
                result.append(None)
            continue

        # ToolDef is a namedtuple, so it is checked before tuples
        if hasattr(item, "idname"):
            if item.idname not in HIDDEN_VIEW3D_TOOLS:
                result.append(item)
            continue

        if isinstance(item, (tuple, list)):
            kept = strip_tool_items(item)
            if kept:
                result.append(type(item)(kept))
            continue

        # callables generate their tools at draw time
        result.append(item)

    # a trailing separator draws a gap at the bottom of the toolbar
    while result and result[-1] is None:
        result.pop()

    return result


def get_view3d_tool_panel():
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active

    return VIEW3D_PT_tools_active


def redraw_toolbars():
    window_manager = bpy.data.window_managers[0] if bpy.data.window_managers else None
    if window_manager is None:
        return
    for window in window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


# switch any window using a hidden tool back to the select tool
def reset_hidden_active_tools(context=None):
    window_manager = bpy.data.window_managers[0] if bpy.data.window_managers else None
    if window_manager is None:
        return

    mode = getattr(context or bpy.context, "mode", None) or "OBJECT"

    # windows come from the window manager, context.workspace isn't reliable right after the switch
    for window in window_manager.windows:
        workspace = window.workspace
        if workspace is None:
            continue

        active = workspace.tools.from_space_view3d_mode(mode, create=False)
        if active is None or active.idname not in HIDDEN_VIEW3D_TOOLS:
            continue

        area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
        if area is None:
            continue

        with bpy.context.temp_override(window=window, screen=window.screen, area=area):
            bpy.ops.wm.tool_set_by_id(name="builtin.select_box", space_type="VIEW_3D")


# remove hidden tools from the toolbar
# wraps tools_from_context, the hook blender uses to filter its tools,
# so registering and unregistering tools keeps working normally
def hide_viewport_tools(context=None):
    global ORIGINAL_TOOLS_FROM_CONTEXT

    panel = get_view3d_tool_panel()

    if ORIGINAL_TOOLS_FROM_CONTEXT is None:
        ORIGINAL_TOOLS_FROM_CONTEXT = panel.tools_from_context.__func__
        original = ORIGINAL_TOOLS_FROM_CONTEXT

        def tools_from_context(cls, context, mode=None):
            yield from strip_tool_items(original(cls, context, mode))

        panel.tools_from_context = classmethod(tools_from_context)

    reset_hidden_active_tools(context)
    redraw_toolbars()


# put the stock blender toolbar back
def restore_viewport_tools():
    global ORIGINAL_TOOLS_FROM_CONTEXT

    if ORIGINAL_TOOLS_FROM_CONTEXT is None:
        return

    get_view3d_tool_panel().tools_from_context = classmethod(ORIGINAL_TOOLS_FROM_CONTEXT)
    ORIGINAL_TOOLS_FROM_CONTEXT = None

    redraw_toolbars()
