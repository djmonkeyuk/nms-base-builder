from mathutils.geometry import interpolate_bezier

def build_curve_eval_data(curve_obj, resolution=16):
    """
    Creates a high-resolution map of the curve.
    Instead of jumping from Control Point to Control Point, we sample
    the radius and tilt at dozens of micro-steps to perfectly match the curve's true shape.
    """
    spline = curve_obj.data.splines[0]
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)
    
    # Return structure: list of tuples (accumulated_length, radius, tilt)
    if count < 2:
        return [(0.0, points[0].radius if count else 1.0, points[0].tilt if count else 0.0)], 0.0

    eval_data = [] 
    accumulated_length = 0.0
    
    is_cyclic = spline.use_cyclic_u
    segment_count = count if is_cyclic else count - 1
    
    # Add starting point
    eval_data.append((0.0, points[0].radius, points[0].tilt))

    for i in range(segment_count):
        p0 = points[i]
        p1 = points[(i + 1) % count]
        
        if spline.type == 'BEZIER':
            # Get high-res 3D points to capture the true geometric bend
            segment_pts = interpolate_bezier(
                p0.co, p0.handle_right, p1.handle_left, p1.co, resolution + 1
            )
            
            # Step through each micro-segment
            for j in range(resolution):
                # Calculate the tiny distance of this specific step
                dist = (segment_pts[j+1] - segment_pts[j]).length
                accumulated_length += dist
                
                # The parametric 't' (0.0 to 1.0) along the BEZIER segment
                t = (j + 1) / resolution
                
                # Interpolate radius and tilt smoothly at this exact micro-step
                rad = (1.0 - t) * p0.radius + t * p1.radius
                tilt = (1.0 - t) * p0.tilt + t * p1.tilt
                
                eval_data.append((accumulated_length, rad, tilt))
                
        else:
            # Poly or NURBS fallback
            v0 = p0.co.xyz if len(p0.co) == 4 else p0.co
            v1 = p1.co.xyz if len(p1.co) == 4 else p1.co
            dist = (v0 - v1).length
            accumulated_length += dist
            
            # For linear curves, just append the end of the segment
            eval_data.append((accumulated_length, p1.radius, p1.tilt))

    return eval_data, accumulated_length

def get_exact_radius_tilt(eval_data, total_length, factor):
    """
    Searches the high-resolution map to find the exact radius and tilt
    based on the physical arc-length factor (0.0 to 1.0).
    """
    if not eval_data:
        return 1.0, 0.0
    if len(eval_data) == 1 or total_length == 0.0:
        return eval_data[0][1], eval_data[0][2]
        
    target_length = factor * total_length
    
    # Clamp bounds
    if target_length <= 0.0:
        return eval_data[0][1], eval_data[0][2]
    if target_length >= total_length:
        return eval_data[-1][1], eval_data[-1][2]
        
    # Find the two micro-segments our target falls exactly between
    for i in range(len(eval_data) - 1):
        dist_a, rad_a, tilt_a = eval_data[i]
        dist_b, rad_b, tilt_b = eval_data[i+1]
        
        if dist_a <= target_length <= dist_b:
            segment_len = dist_b - dist_a
            if segment_len == 0:
                return rad_a, tilt_a
                
            # Perform a tiny, highly accurate linear interpolation 
            # between the two micro-points
            t = (target_length - dist_a) / segment_len
            
            final_rad = (1.0 - t) * rad_a + t * rad_b
            final_tilt = (1.0 - t) * tilt_a + t * tilt_b
            return final_rad, final_tilt
            
    return eval_data[-1][1], eval_data[-1][2]


def update_obj_transformations(obj, curve_obj, eval_data, total_length):
    factor = obj.get("curve_factor")
    
    if factor is None:
        return
    
    curve_scale_multiplier = curve_obj.scale.x/curve_obj["initial_curve_scale"]
    radius_multiplier = curve_obj.get("radius_multiplier", 1.0)
    
    # Get accurate radius and tilt from our new high-res map
    radius, tilt = get_exact_radius_tilt(eval_data, total_length, factor)
    
    if curve_obj.get("parent_selected",True):
        base_scale = obj["base_scale"]
        obj["radius"] = radius
        
        scale = radius * radius_multiplier * base_scale * curve_scale_multiplier
        
        # Clamp scale to a microscopic value above zero. 
        # This prevents the matrix inversion that snaps objects to the world origin.
        if scale < 0.00001:
            scale = 0.00001
        
        obj.scale.x = scale
        obj.scale.y = scale
        obj.scale.z = scale
    
    
def mirror_curve_data(curve_obj, axis='X'):
    """
    Mirrors a curve's points, handles, and tilt 
    along the specified local axis ('X', 'Y', or 'Z').
    """
    if not curve_obj or curve_obj.type != 'CURVE':
        raise TypeError("Please provide a valid curve object.")
    
    # Normalize the axis input and map it to a vector index (X:0, Y:1, Z:2)
    axis = axis.upper()
    if axis not in {'X', 'Y', 'Z'}:
        raise ValueError("Axis parameter must be 'X', 'Y', or 'Z'.")
    
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    
    # Operate on the curve's datablock
    curve_data = curve_obj.data
    
    for spline in curve_data.splines:
        if spline.type == 'BEZIER':
            # Store original handle types and force them to FREE
            stored_types = []
            for bp in spline.bezier_points:
                stored_types.append({
                    'left': bp.handle_left_type,
                    'right': bp.handle_right_type
                })
                bp.handle_left_type = 'FREE'
                bp.handle_right_type = 'FREE'
                
            #  Mirror the coordinates, handles, and tilt safely
            for bp in spline.bezier_points:
                bp.co[axis_idx] *= -1.0
                bp.handle_left[axis_idx] *= -1.0
                bp.handle_right[axis_idx] *= -1.0
                bp.tilt *= -1.0
                
            # Restore the original handle types
            # will allow Blender to rebuild them with perfect symmetry.
            for bp, orig_type in zip(spline.bezier_points, stored_types):
                bp.handle_left_type = orig_type['left']
                bp.handle_right_type = orig_type['right']
                
        elif spline.type in {'NURBS', 'POLY'}:
            for pt in spline.points:
                # NURBS/POLY points are stored as 4D vectors (x, y, z, w)
                pt.co[axis_idx] *= -1.0
                pt.tilt *= -1.0
                

def normalise_curve_scale(curve_obj):
    """This prevents explosion of position transformations by resetting object scale to 1 without applying"""
    if curve_obj.type != 'CURVE':
        print(f"'{curve_obj.name}' is not a curve object.")
        return
    
    # Optimization: Skip if already normalized
    if curve_obj.scale[:] == (1.0, 1.0, 1.0):
        return
    
    # Get current scale
    scale_x, scale_y, scale_z = curve_obj.scale
    
    # Scale all curve data points
    for spline in curve_obj.data.splines:
        
        # Handle Bezier curves
        if spline.type == 'BEZIER':
            for point in spline.bezier_points:
                left_type = point.handle_left_type
                right_type = point.handle_right_type
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'

                # Scale the main control point
                point.co.x *= scale_x
                point.co.y *= scale_y
                point.co.z *= scale_z
                
                # Scale the left handle
                point.handle_left.x *= scale_x
                point.handle_left.y *= scale_y
                point.handle_left.z *= scale_z
                
                # Scale the right handle
                point.handle_right.x *= scale_x
                point.handle_right.y *= scale_y
                point.handle_right.z *= scale_z

                point.handle_left_type = left_type
                point.handle_right_type = right_type
                
        # Handle NURBS and Poly curves
        else:
            for point in spline.points:
                # Note: NURBS points are 4D (x, y, z, w). 
                # Scaling x, y, and z is correct; the weight (w) remains untouched.
                point.co.x *= scale_x
                point.co.y *= scale_y
                point.co.z *= scale_z
    
    # Reset object scale to 1
    curve_obj.scale = (1, 1, 1)

    if "initial_curve_scale" in curve_obj and scale_x != 0:
        curve_obj["initial_curve_scale"] = curve_obj["initial_curve_scale"] / scale_x
