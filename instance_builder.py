import math


def _haversine_km(lat1, lon1, lat2, lon2):
    # Returns great-circle distance in kilometers.
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _distance_from_matrix(distance_matrix, i, j):
    if (i, j) in distance_matrix:
        return distance_matrix[i, j]
    if i in distance_matrix and j in distance_matrix[i]:
        return distance_matrix[i][j]
    raise KeyError(f"Missing distance for ({i}, {j}) in distance_matrix")


def build_instance(
    vehicles,
    customers,
    depots,
    facilities,
    cost_per_unit=1.0,
    time_per_unit=3.0,
    distance_mode="euclidean",
    distance_matrix=None,
    time_matrix=None,
):
    if len(depots) != 1:
        raise ValueError("Exactly one depot is supported in the current model.")
    if len(facilities) != 1:
        raise ValueError("Exactly one disposal facility is supported in the current model.")

    depot_obj = depots[0]
    facility_obj = facilities[0]

    V = [v.id for v in vehicles]
    C = [c.id for c in customers]
    D = [depot_obj.id]
    F = [facility_obj.id]
    N = D + C + F

    demands = {c.id: c.demand for c in customers}
    service_times = {c.id: c.service for c in customers}
    vehicle_capacities = {v.id: v.capacity for v in vehicles}
    vehicle_startup_costs = {v.id: v.startup_cost for v in vehicles}
    max_shift_duration_vehicles = {v.id: v.max_shift for v in vehicles}

    node_positions = {depot_obj.id: (depot_obj.lat, depot_obj.lon)}
    node_positions[facility_obj.id] = (facility_obj.lat, facility_obj.lon)
    for c in customers:
        node_positions[c.id] = (c.lat, c.lon)

    if distance_matrix is not None:
        def distance(a, b):
            return _distance_from_matrix(distance_matrix, a, b)
    elif distance_mode == "euclidean":
        def distance(a, b):
            (x1, y1) = node_positions[a]
            (x2, y2) = node_positions[b]
            return math.hypot(x1 - x2, y1 - y2)
    elif distance_mode == "haversine_km":
        def distance(a, b):
            (lat1, lon1) = node_positions[a]
            (lat2, lon2) = node_positions[b]
            return _haversine_km(lat1, lon1, lat2, lon2)
    else:
        raise ValueError(f"Unknown distance_mode: {distance_mode}")

    travel_costs = {}
    travel_times = {}
    for i in N:
        for j in N:
            if i == j:
                continue
            dist = distance(i, j)
            travel_costs[i, j] = max(1, int(round(dist * cost_per_unit)))
            if time_matrix is not None:
                raw_time = _distance_from_matrix(time_matrix, i, j)
                travel_times[i, j] = max(1, int(round(raw_time)))
            else:
                travel_times[i, j] = max(1, int(round(dist * time_per_unit)))

    return {
        "V": V,
        "C": C,
        "D": D,
        "F": F,
        "N": N,
        "demands": demands,
        "service_times": service_times,
        "vehicle_capacities": vehicle_capacities,
        "vehicle_startup_costs": vehicle_startup_costs,
        "max_shift_duration_vehicles": max_shift_duration_vehicles,
        "node_positions": node_positions,
        "travel_costs": travel_costs,
        "travel_times": travel_times,
    }
