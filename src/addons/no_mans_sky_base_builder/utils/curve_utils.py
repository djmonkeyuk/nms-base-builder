from . import blend_utils
import bpy

from mathutils.geometry import interpolate_bezier

def get_spline_segment_lengths(spline, resolution=12):
    """
    Approximates the length of each segment between control points
    to find the true physical distance along the curve.
    """
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)
    
    if count < 2:
        return [0.0], 0.0

    segment_lengths = []
    total_length = 0.0
    
    # Check if the curve forms a closed loop . 
    # If cyclic, the last point connects back to the first, adding an extra segment.
    is_cyclic = spline.use_cyclic_u
    segment_count = count if is_cyclic else count - 1

    for i in range(segment_count):
        p0 = points[i]
        # Modulo operator (%) ensures that if i+1 exceeds the point count, 
        # it wraps back to 0 (crucial for connecting the last point to the first in a cyclic loop).
        p1 = points[(i + 1) % count]
        
        if spline.type == 'BEZIER':
            # Bezier curves curve between points based on 'handles'. 
            # We sample points along this curve (resolution + 1) to approximate the actual curved length using short, straight lines.
            segment_pts = interpolate_bezier(
                p0.co, p0.handle_right, p1.handle_left, p1.co, resolution + 1
            )
            # Calculate distance between each sampled point and sum them up for the total segment length.
            seg_len = sum((segment_pts[j+1] - segment_pts[j]).length for j in range(len(segment_pts) - 1))
        else:
            # Poly or NURBS fallback. 
            # NURBS curves use 4D coordinates (X, Y, Z, W) where W is the vertex weight. 
            # We must strip the W weight to get standard 3D vectors before calculating distance.
            v0 = p0.co.xyz if len(p0.co) == 4 else p0.co
            v1 = p1.co.xyz if len(p1.co) == 4 else p1.co
            seg_len = (v0 - v1).length
            
        segment_lengths.append(seg_len)
        total_length += seg_len

    return segment_lengths, total_length

def get_curve_radius_tilt(curve_obj, factor, segment_lengths, total_length):
    """
    Calculates radius and tilt based on the actual physical arc-length of the curve,
    using Smoothstep to ensure seamless transitions between segments.
    """
    spline = curve_obj.data.splines[0]
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)
    
    if count == 0:
        return 1.0, 0.0
    if count == 1 or total_length == 0:
        return points[0].radius, points[0].tilt
        
    # 'factor' is a 0.0 to 1.0 percentage of how far along the curve the object should be.
    # Multiplying it by total_length gives us the exact physical distance from the start.
    target_length = factor * total_length
    accumulated_length = 0.0
    
    for i, seg_len in enumerate(segment_lengths):
        # We check if our target distance falls within the current segment.
        if accumulated_length + seg_len >= target_length or i == len(segment_lengths) - 1:
            
            # t is the linear interpolation factor within this specific segment.
            t = 0.0 if seg_len == 0 else (target_length - accumulated_length) / seg_len
            # This bends the linear 't' into a gentle 'S' curve, flattening out at 0.0 and 1.0
            smooth_t = t * t * (3.0 - 2.0 * t)
            
            p0 = points[i]
            p1 = points[(i + 1) % count]
            
            # Blend using smooth_t instead of t
            radius = (1.0 - smooth_t) * p0.radius + smooth_t * p1.radius
            tilt = (1.0 - smooth_t) * p0.tilt + smooth_t * p1.tilt
            
            return radius, tilt
            
        accumulated_length += seg_len

    # Fallback to the last point if the loop completes without returning due to floating point inaccuracies.
    return points[-1].radius, points[-1].tilt

def update_obj_transformations(obj, curve_obj, segment_lengths, total_length):
    radius_multiplier = curve_obj.get("radius_multiplier", 1.0)
    factor = obj.get("curve_factor")
    
    if factor is None:
        return
    
    radius, tilt = get_curve_radius_tilt(curve_obj, factor, segment_lengths, total_length)
    scale = radius * radius_multiplier 
    
    obj.scale.x = scale
    obj.scale.y = scale
    obj.scale.z = scale
    
    obj.location = (0.0, 0.0, 0.0)