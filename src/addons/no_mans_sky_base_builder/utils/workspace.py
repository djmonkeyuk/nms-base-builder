import bpy

# Workspace Cleanup
def cleanup_workspace(context) -> None:
    
    new_workspace_name = "NMS base builder"
    
    layout_ws = bpy.data.workspaces.get("Layout")
    if layout_ws is None:
        return
  
    # Snapshot list before iterating because collection changes during deletion
    other_workspaces = [ws for ws in bpy.data.workspaces if ws != layout_ws]
    for ws in other_workspaces:
        with bpy.context.temp_override(workspace=ws):
            bpy.ops.workspace.delete()

    # Switch to Layout and rename it
    bpy.context.window.workspace = layout_ws
    layout_ws.name = new_workspace_name
    
    # remove timeline area from bttom of layout workspace
    remove_timeline_area()
    # remove extra tabs from properties panel
    simplify_object_properties()
    
    # hide status bar
    for screen in bpy.data.screens:
        screen.show_statusbar = False
    
    
def remove_timeline_area():
    win = bpy.context.window
    screen = win.screen
    timeline_area_panel_filter = ( area for area in screen.areas if area.type == "DOPESHEET_EDITOR" and area.spaces.active.mode == "TIMELINE")
    timeline_area_iterator = next(timeline_area_panel_filter,None)
    if timeline_area_iterator:
        with bpy.context.temp_override(window=win, screen=screen, area=timeline_area_iterator):
            bpy.ops.screen.area_close()
    
    
def simplify_object_properties():
    # Loop through all open windows to find the active screen reliably
    for window in bpy.context.window_manager.windows:
        
        # Check if the window actually has a screen right now
        if not window.screen:
            continue
        
        for area in window.screen.areas:
            if area.type != 'PROPERTIES':
                continue
                
            space = area.spaces.active
            if not space:
                continue
                
            # Loop through all attributes in the space properties
            for attr in dir(space):
                if attr.startswith("show_properties_"):
                    try:
                        setattr(space, attr, False)
                    except AttributeError:
                        pass
            
            # Turn the Object tab back on and set context
            # there can be an exception when no object is selected, at that time, there is no objects porperty in tabs
            try:
                space.show_properties_object = True
                space.context = 'OBJECT'
            except TypeError:
                pass
            
            # Refresh the UI
            area.tag_redraw()