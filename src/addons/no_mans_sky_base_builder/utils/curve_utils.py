import math

from mathutils import Vector
from mathutils.geometry import interpolate_bezier

from . import mirror_utils

# Blender stores transforms as 32 bit floats, anything below this counts as unchanged
WRITE_EPSILON = 1e-6

# density integrals keyed by control point weights, so a changed weight never hits a stale entry
_density_cache = {}
_DENSITY_CACHE_LIMIT = 32


def build_curve_eval_data(curve_obj, resolution=16):
    """Sample radius and tilt along the curve.

    Returns:
        tuple: ([(accumulated length, radius, tilt)], total length)
    """
    spline = curve_obj.data.splines[0]
    points = spline.bezier_points if spline.bezier_points else spline.points
    count = len(points)

    if count < 2:
        return [(0.0, points[0].radius if count else 1.0, points[0].tilt if count else 0.0)], 0.0

    eval_data = [(0.0, points[0].radius, points[0].tilt)]
    accumulated_length = 0.0
    segment_count = count if spline.use_cyclic_u else count - 1

    if spline.type == 'BEZIER':
        for i in range(segment_count):
            p0 = points[i]
            p1 = points[(i + 1) % count]
            segment_pts = interpolate_bezier(
                p0.co, p0.handle_right, p1.handle_left, p1.co, resolution + 1
            )

            rad0, tilt0 = p0.radius, p0.tilt
            rad_delta = p1.radius - rad0
            tilt_delta = p1.tilt - tilt0

            for j in range(resolution):
                accumulated_length += (segment_pts[j + 1] - segment_pts[j]).length
                t = (j + 1) / resolution
                eval_data.append(
                    (accumulated_length, rad0 + t * rad_delta, tilt0 + t * tilt_delta)
                )
    else:
        for i in range(segment_count):
            p0 = points[i]
            p1 = points[(i + 1) % count]
            v0 = p0.co.xyz if len(p0.co) == 4 else p0.co
            v1 = p1.co.xyz if len(p1.co) == 4 else p1.co
            accumulated_length += (v1 - v0).length
            eval_data.append((accumulated_length, p1.radius, p1.tilt))

    return eval_data, accumulated_length


def get_exact_radius_tilt(eval_data, total_length, factor):
    """Radius and tilt at a curve factor, smoothed with cubic hermite interpolation."""
    data_len = len(eval_data)

    if data_len == 0:
        return 1.0, 0.0
    if data_len == 1 or total_length == 0.0:
        return eval_data[0][1], eval_data[0][2]

    target_length = factor * total_length
    if target_length <= 0.0:
        return eval_data[0][1], eval_data[0][2]
    if target_length >= total_length:
        return eval_data[-1][1], eval_data[-1][2]

    # binary search for the sample pair around target_length
    left, right = 0, data_len - 1
    while left < right - 1:
        mid = (left + right) // 2
        if eval_data[mid][0] <= target_length:
            left = mid
        else:
            right = mid

    dist_a, rad_a, tilt_a = eval_data[left]
    dist_b, rad_b, tilt_b = eval_data[right]
    segment_len = dist_b - dist_a
    if segment_len == 0:
        return rad_a, tilt_a

    t = (target_length - dist_a) / segment_len
    dist_prev, rad_prev, tilt_prev = eval_data[max(0, left - 1)]
    dist_next, rad_next, tilt_next = eval_data[min(data_len - 1, right + 1)]

    def hermite_interp(y_prev, y_a, y_b, y_next):
        dx_10 = dist_b - dist_prev
        dx_31 = dist_next - dist_a
        m1 = (y_b - y_prev) * (segment_len / dx_10) if dx_10 > 0 else 0.0
        m2 = (y_next - y_a) * (segment_len / dx_31) if dx_31 > 0 else 0.0

        t2 = t * t
        t3 = t2 * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        return h00 * y_a + h10 * m1 + h01 * y_b + h11 * m2

    radius = hermite_interp(rad_prev, rad_a, rad_b, rad_next)
    tilt = hermite_interp(tilt_prev, tilt_a, tilt_b, tilt_next)
    return radius, tilt


def build_curve_context(curve_obj):
    """Curve values shared by every child, read once per update.

    Returns:
        tuple: (parent_selected, curve scale multiplier, radius multiplier)
    """
    return (
        curve_obj.get("parent_selected", True),
        curve_obj.scale.x / curve_obj.get("initial_curve_scale", 1.0),
        curve_obj.get("radius_multiplier", 1.0),
    )


def update_obj_transformations(obj, curve_obj, eval_data, total_length, curve_context=None):
    factor = obj.get("curve_factor")
    update_object_factor(obj, curve_obj, factor)

    if factor is None:
        return

    if curve_context is None:
        curve_context = build_curve_context(curve_obj)
    parent_selected, curve_scale_multiplier, radius_multiplier = curve_context

    if not parent_selected:
        return

    radius, tilt = get_exact_radius_tilt(eval_data, total_length, factor)
    if obj.get("radius") != radius:
        obj["radius"] = radius

    scale = radius * radius_multiplier * obj.get("base_scale", 1.0) * curve_scale_multiplier

    # a zero scale breaks the matrix inversion and snaps objects to the origin
    if scale < 0.00001:
        scale = 0.00001

    # writing a transform re-evaluates the object even when unchanged, so only write real changes
    tolerance = WRITE_EPSILON * max(1.0, abs(scale))
    current_scale = obj.scale
    if (abs(current_scale.x - scale) > tolerance
            or abs(current_scale.y - scale) > tolerance
            or abs(current_scale.z - scale) > tolerance):
        obj.scale = (scale, scale, scale)


def update_object_factor(obj, curve_obj, factor, constraint=None):
    if factor is None:
        return
    if constraint is None:
        constraint = next(
            (c for c in obj.constraints if c.type == 'FOLLOW_PATH' and c.target == curve_obj),
            None,
        )
    # setting offset_factor re-evaluates the constraint even when the value is the same
    if constraint and abs(constraint.offset_factor - factor) > WRITE_EPSILON:
        constraint.offset_factor = factor
    if obj.get("curve_factor") != factor:
        obj["curve_factor"] = factor


def mirror_curve(curve_obj, axis='X', center=Vector((0, 0, 0))):
    """Mirror a curve's points, handles and tilt, then its location around center."""
    if not curve_obj or curve_obj.type != 'CURVE':
        raise TypeError("Please provide a valid curve object.")

    axis = axis.upper()
    if axis not in {'X', 'Y', 'Z'}:
        raise ValueError("Axis parameter must be 'X', 'Y', or 'Z'.")

    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[axis]

    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            points = spline.bezier_points
            # handles must be FREE while mirrored, then blender rebuilds them symmetrically
            stored_types = [(bp.handle_left_type, bp.handle_right_type) for bp in points]
            for bp in points:
                bp.handle_left_type = 'FREE'
                bp.handle_right_type = 'FREE'

            for bp in points:
                bp.co[axis_idx] *= -1.0
                bp.handle_left[axis_idx] *= -1.0
                bp.handle_right[axis_idx] *= -1.0
                bp.tilt *= -1.0

            for bp, (left_type, right_type) in zip(points, stored_types):
                bp.handle_left_type = left_type
                bp.handle_right_type = right_type
        else:
            for pt in spline.points:
                pt.co[axis_idx] *= -1.0
                pt.tilt *= -1.0

    curve_obj.location = mirror_utils.reflect_point(curve_obj.location, center, axis)
    if axis == "X":
        curve_obj.rotation_euler.y *= -1
        curve_obj.rotation_euler.z *= -1
    elif axis == "Y":
        curve_obj.rotation_euler.x *= -1
        curve_obj.rotation_euler.z *= -1
    elif axis == "Z":
        curve_obj.rotation_euler.x *= -1
        curve_obj.rotation_euler.y *= -1


def normalise_curve_scale(curve_obj):
    """Bake object scale into the curve points, so children positions don't explode."""
    if curve_obj.type != 'CURVE':
        print(f"'{curve_obj.name}' is not a curve object.")
        return

    current_scale = curve_obj.scale[:]
    if current_scale == (1.0, 1.0, 1.0):
        return

    scale_x, scale_y, scale_z = current_scale
    scale_vector = Vector((scale_x, scale_y, scale_z))

    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            for point in spline.bezier_points:
                left_type = point.handle_left_type
                right_type = point.handle_right_type
                point.handle_left_type = 'FREE'
                point.handle_right_type = 'FREE'

                point.co *= scale_vector
                point.handle_left *= scale_vector
                point.handle_right *= scale_vector

                point.handle_left_type = left_type
                point.handle_right_type = right_type
        else:
            # NURBS points are 4D, the weight (w) stays untouched
            for point in spline.points:
                point.co.x *= scale_x
                point.co.y *= scale_y
                point.co.z *= scale_z

    curve_obj.scale = (1, 1, 1)

    if "initial_curve_scale" in curve_obj and scale_x != 0:
        curve_obj["initial_curve_scale"] = curve_obj["initial_curve_scale"] / scale_x


def get_control_points(curve_obj):
    if not curve_obj or curve_obj.type != 'CURVE':
        return None

    spline = curve_obj.data.splines[0]
    if spline.type == 'BEZIER':
        return spline.bezier_points
    if spline.type in {'POLY', 'NURBS'}:
        return spline.points
    return None


# Density ---
# each control point's softbody weight sets how tightly objects pack around it

def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def exponential_scale(x, steepness=5.0):
    return math.exp(steepness * (x - 0.5))


def get_density_map(curve):
    return [exponential_scale(point.weight_softbody) for point in get_control_points(curve)]


def half_the_weight_points(curve):
    # 0.5 is the neutral weight, it gives even spacing
    for point in get_control_points(curve):
        point.weight_softbody = 0.5


def get_density(density_map, factor):
    if len(density_map) == 1:
        return density_map[0]
    position = factor * (len(density_map) - 1)
    index = min(int(position), len(density_map) - 2)
    t = smoothstep(position - index)
    a = density_map[index]
    b = density_map[index + 1]
    return a + (b - a) * t


def factor_from_density(cumulative_density, sample_factors, target):
    low = 0
    high = len(cumulative_density) - 1
    while low < high:
        mid = (low + high) // 2
        if cumulative_density[mid] < target:
            low = mid + 1
        else:
            high = mid

    index = max(1, low)
    d0 = cumulative_density[index - 1]
    d1 = cumulative_density[index]
    f0 = sample_factors[index - 1]
    f1 = sample_factors[index]

    if d1 == d0:
        return f0
    return f0 + (f1 - f0) * (target - d0) / (d1 - d0)


def build_density_samples(curve, sample_count):
    """Sample the weight curve and integrate it, cached by weights and sample count.

    Returns:
        tuple: (sample factors, cumulative density, total density), shared so read only
    """
    density_map = tuple(get_density_map(curve))
    cache_key = (sample_count, density_map)
    cached = _density_cache.get(cache_key)
    if cached is not None:
        return cached

    sample_factors = [i / (sample_count - 1) for i in range(sample_count)]

    cumulative_density = [0.0]
    total_density = 0.0
    previous_density = get_density(density_map, sample_factors[0])
    for i in range(1, sample_count):
        current_density = get_density(density_map, sample_factors[i])
        dx = sample_factors[i] - sample_factors[i - 1]
        total_density += (previous_density + current_density) * 0.5 * dx
        cumulative_density.append(total_density)
        previous_density = current_density

    if len(_density_cache) >= _DENSITY_CACHE_LIMIT:
        _density_cache.clear()
    samples = (sample_factors, cumulative_density, total_density)
    _density_cache[cache_key] = samples
    return samples


def calculate_curve_factors(curve, existing_objs):
    object_count = len(existing_objs)
    if object_count == 0:
        return

    if object_count == 1:
        existing_objs[0]["curve_factor"] = 0.0
        return

    sample_factors, cumulative_density, total_density = build_density_samples(
        curve, max(128, object_count * 16)
    )
    for index, obj in enumerate(existing_objs):
        target_density = index / (object_count - 1) * total_density
        factor = factor_from_density(cumulative_density, sample_factors, target_density)
        if obj.get("curve_factor") != factor:
            obj["curve_factor"] = factor


def get_total_curve_density(curve, object_count=10):
    return build_density_samples(curve, max(128, object_count * 16))[2]
