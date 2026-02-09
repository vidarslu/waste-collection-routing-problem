import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _osrm_table_request(coords, profile, base_url, user_agent, timeout_s):
    coords_str = ";".join([f"{lon},{lat}" for (lat, lon) in coords])
    query = urlencode({"annotations": "distance,duration"})
    url = f"{base_url.rstrip('/')}/table/v1/{profile}/{coords_str}?{query}"
    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def osrm_table_matrices(
    node_positions,
    node_order=None,
    profile="driving",
    base_url="http://router.project-osrm.org",
    user_agent="RenovisionOSRM/0.1 (contact@example.com)",
    timeout_s=30,
):
    if node_order is None:
        node_order = list(node_positions.keys())
    coords = [node_positions[node_id] for node_id in node_order]

    data = _osrm_table_request(coords, profile, base_url, user_agent, timeout_s)
    distances = data.get("distances")
    durations = data.get("durations")
    if distances is None or durations is None:
        raise ValueError("OSRM response missing distances/durations.")

    distance_matrix = {}
    time_matrix = {}
    for i_idx, i in enumerate(node_order):
        for j_idx, j in enumerate(node_order):
            if i == j:
                continue
            dist_m = distances[i_idx][j_idx]
            dur_s = durations[i_idx][j_idx]
            if dist_m is None or dur_s is None:
                raise ValueError(f"Missing OSRM entry for ({i}, {j})")
            distance_matrix[i, j] = dist_m / 1000.0
            time_matrix[i, j] = dur_s / 60.0

    return distance_matrix, time_matrix


def load_matrix_cache(path, node_order):
    path = Path(path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("nodes") != node_order:
        return None

    distance_matrix = {}
    time_matrix = {}
    for key, value in data.get("distance_km", {}).items():
        i, j = key.split("|", 1)
        distance_matrix[i, j] = value
    for key, value in data.get("duration_min", {}).items():
        i, j = key.split("|", 1)
        time_matrix[i, j] = value

    return distance_matrix, time_matrix


def save_matrix_cache(path, node_order, distance_matrix, time_matrix):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    distance_km = {f"{i}|{j}": v for (i, j), v in distance_matrix.items()}
    duration_min = {f"{i}|{j}": v for (i, j), v in time_matrix.items()}
    payload = {
        "nodes": node_order,
        "distance_km": distance_km,
        "duration_min": duration_min,
    }

    with path.open("w", encoding="utf-8", newline="") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
