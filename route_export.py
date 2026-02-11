import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _osrm_route_request(
    coords,
    profile,
    base_url,
    user_agent,
    steps=True,
    geometries="geojson",
    overview="full",
    timeout_s=30,
):
    coords_str = ";".join([f"{lon},{lat}" for (lat, lon) in coords])
    params = {
        "geometries": geometries,
        "overview": overview,
        "steps": "true" if steps else "false",
    }
    url = f"{base_url.rstrip('/')}/route/v1/{profile}/{coords_str}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _simplify_steps(steps):
    simplified = []
    for step in steps:
        maneuver = step.get("maneuver", {})
        simplified.append(
            {
                "name": step.get("name", ""),
                "mode": step.get("mode", ""),
                "distance_m": step.get("distance", 0.0),
                "duration_s": step.get("duration", 0.0),
                "type": maneuver.get("type", ""),
                "modifier": maneuver.get("modifier", ""),
                "exit": maneuver.get("exit", None),
                "location": maneuver.get("location", None),
            }
        )
    return simplified


def export_routes_geojson(
    routes_by_vehicle,
    node_positions,
    output_geojson_path,
    output_directions_path=None,
    depot_id=None,
    facility_id=None,
    profile="driving",
    base_url="http://router.project-osrm.org",
    user_agent="RenovisionOSRM/0.1 (contact@example.com)",
    timeout_s=30,
    pause_s=0.2,
):
    features = []
    directions = {"vehicles": {}}

    for vehicle_id, route in routes_by_vehicle.items():
        if len(route) < 2:
            continue
        coords = [node_positions[node_id] for node_id in route]
        data = _osrm_route_request(
            coords,
            profile=profile,
            base_url=base_url,
            user_agent=user_agent,
            steps=True,
            timeout_s=timeout_s,
        )
        if "routes" not in data or not data["routes"]:
            raise ValueError(f"OSRM route failed for vehicle {vehicle_id}")

        route_data = data["routes"][0]
        geometry = route_data.get("geometry")
        distance_km = route_data.get("distance", 0.0) / 1000.0
        duration_min = route_data.get("duration", 0.0) / 60.0

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "vehicle": vehicle_id,
                    "distance_km": distance_km,
                    "duration_min": duration_min,
                    "stops": route,
                },
            }
        )

        legs = route_data.get("legs", [])
        leg_directions = []
        for idx, leg in enumerate(legs):
            leg_directions.append(
                {
                    "from": route[idx],
                    "to": route[idx + 1],
                    "distance_km": leg.get("distance", 0.0) / 1000.0,
                    "duration_min": leg.get("duration", 0.0) / 60.0,
                    "steps": _simplify_steps(leg.get("steps", [])),
                }
            )
        directions["vehicles"][vehicle_id] = leg_directions

        time.sleep(pause_s)

    # Add node points for context
    for node_id, (lat, lon) in node_positions.items():
        if node_id == depot_id:
            kind = "depot"
        elif node_id == facility_id:
            kind = "facility"
        else:
            kind = "customer"
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"node_id": node_id, "kind": kind},
            }
        )

    feature_collection = {"type": "FeatureCollection", "features": features}

    output_geojson_path = Path(output_geojson_path)
    output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    with output_geojson_path.open("w", encoding="utf-8", newline="") as f:
        json.dump(feature_collection, f, indent=2)

    if output_directions_path:
        output_directions_path = Path(output_directions_path)
        output_directions_path.parent.mkdir(parents=True, exist_ok=True)
        with output_directions_path.open("w", encoding="utf-8", newline="") as f:
            json.dump(directions, f, indent=2)

    return feature_collection, directions


def write_map_html(feature_collection, output_html_path, directions=None):
    output_html_path = Path(output_html_path)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)

    geojson_text = json.dumps(feature_collection)
    directions_text = json.dumps(directions or {})
    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Routes Map</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
  <style>
    html, body {{ height: 100%; margin: 0; font-family: Arial, sans-serif; }}
    .layout {{ display: flex; height: 100%; }}
    #map {{ flex: 2; }}
    #sidebar {{
      flex: 1;
      overflow: auto;
      border-left: 1px solid #e0e0e0;
      padding: 12px 14px;
      background: #fafafa;
    }}
    h2 {{ margin: 0 0 8px; font-size: 18px; }}
    h3 {{ margin: 12px 0 6px; font-size: 15px; }}
    .meta {{ color: #555; font-size: 12px; margin-bottom: 8px; }}
    .leg {{ margin: 8px 0 12px; }}
    .step {{ font-size: 13px; margin: 4px 0; }}
    .vehicle {{ border-bottom: 1px solid #e6e6e6; padding-bottom: 10px; margin-bottom: 12px; }}
    .stop-dot {{
      min-width: 20px;
      height: 20px;
      padding: 0 6px;
      border-radius: 10px;
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      line-height: 20px;
      text-align: center;
      white-space: nowrap;
      border: 2px solid #fff;
      box-shadow: 0 0 2px rgba(0,0,0,0.4);
      display: inline-block;
    }}
    .arrow-icon {{
      font-size: 12px;
      font-weight: 700;
      text-shadow: 0 0 2px #fff;
    }}
    @media (max-width: 900px) {{
      .layout {{ flex-direction: column; }}
      #map {{ height: 55%; }}
      #sidebar {{ height: 45%; border-left: none; border-top: 1px solid #e0e0e0; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <div id="map"></div>
    <div id="sidebar">
      <h2>Directions</h2>
      <div class="meta">Per-vehicle turn-by-turn directions</div>
      <div id="directions"></div>
    </div>
  </div>
  <script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""
  ></script>
  <script>
    const data = __GEOJSON_DATA__;
    const directions = __DIRECTIONS_DATA__;
    const map = L.map('map');
    const tiles = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }});
    tiles.addTo(map);

    const colors = {{
      V1: '#d62728',
      V2: '#9467bd',
      V3: '#8c564b'
    }};
    const dashPatterns = {{
      V1: null,
      V2: '6 6',
      V3: '12 6'
    }};

    const layer = L.geoJSON(data, {{
      style: f => {{
        if (f.geometry.type === 'LineString') {{
          const color = colors[f.properties.vehicle] || '#1f77b4';
          return {{
            color,
            weight: 4,
            opacity: 0.85,
            dashArray: dashPatterns[f.properties.vehicle] || null
          }};
        }}
        return {{ color: '#333' }};
      }},
      pointToLayer: (f, latlng) => {{
        const kind = f.properties.kind;
        let color = '#ff7f0e';
        if (kind === 'depot') color = '#1f77b4';
        if (kind === 'facility') color = '#2ca02c';
        return L.circleMarker(latlng, {{ radius: 5, color, fillColor: color, fillOpacity: 0.9 }});
      }},
      onEachFeature: (f, layer) => {{
        if (f.geometry.type === 'LineString') {{
          layer.bindPopup(`Vehicle: ${{f.properties.vehicle}}<br/>Distance: ${{f.properties.distance_km.toFixed(2)}} km<br/>Duration: ${{f.properties.duration_min.toFixed(1)}} min`);
        }} else if (f.geometry.type === 'Point') {{
          layer.bindPopup(`${{f.properties.kind}}: ${{f.properties.node_id}}`);
        }}
      }}
    }}).addTo(map);

    map.fitBounds(layer.getBounds(), {{ padding: [20, 20] }});

    const nodeCoords = {{}};
    const nodeKinds = {{}};
    data.features.forEach(f => {{
      if (f.geometry && f.geometry.type === 'Point' && f.properties && f.properties.node_id) {{
        const [lon, lat] = f.geometry.coordinates;
        nodeCoords[f.properties.node_id] = [lat, lon];
        nodeKinds[f.properties.node_id] = f.properties.kind;
      }}
    }});

    const ARROW_SPACING_M = 400;

    function angleDeg(a, b) {{
      const p1 = map.latLngToLayerPoint(a);
      const p2 = map.latLngToLayerPoint(b);
      const dy = p2.y - p1.y;
      const dx = p2.x - p1.x;
      return Math.atan2(dy, dx) * 180 / Math.PI;
    }}

    function addDirectionArrows() {{
      data.features.forEach(f => {{
        if (!f.geometry || f.geometry.type !== 'LineString') return;
        const vehicleId = f.properties.vehicle;
        const color = colors[vehicleId] || '#1f77b4';
        const latlngs = f.geometry.coordinates.map(c => L.latLng(c[1], c[0]));
        if (latlngs.length < 2) return;

        let distSoFar = 0;
        let nextAt = ARROW_SPACING_M;
        for (let i = 0; i < latlngs.length - 1; i++) {{
          const a = latlngs[i];
          const b = latlngs[i + 1];
          const segLen = map.distance(a, b);
          if (!isFinite(segLen) || segLen <= 0) continue;

          while (distSoFar + segLen >= nextAt) {{
            const t = (nextAt - distSoFar) / segLen;
            const pos = L.latLng(
              a.lat + (b.lat - a.lat) * t,
              a.lng + (b.lng - a.lng) * t
            );
            const angle = angleDeg(a, b);
            const icon = L.divIcon({{
              className: 'arrow-icon',
              html: `<div class="arrow-icon" style="color:${{color}}; transform: rotate(${{angle}}deg);">&#9654;</div>`,
              iconSize: [14, 14],
              iconAnchor: [7, 7]
            }});
            L.marker(pos, {{ icon, interactive: false }}).addTo(map);
            nextAt += ARROW_SPACING_M;
          }}
          distSoFar += segLen;
        }}
      }});
    }}

    function addStopMarkers() {{
      data.features.forEach(f => {{
        if (!f.geometry || f.geometry.type !== 'LineString') return;
        const vehicleId = f.properties.vehicle;
        const color = colors[vehicleId] || '#1f77b4';
        const stops = f.properties.stops || [];
        const seenSpecial = new Set();
        let serviceIndex = 0;
        stops.forEach((stopId) => {{
          const latlng = nodeCoords[stopId];
          if (!latlng) return;
          const kind = nodeKinds[stopId];
          let label = '';
          let markerColor = color;
          if (kind === 'depot') {{
            if (seenSpecial.has(stopId)) return;
            seenSpecial.add(stopId);
            label = 'Depot';
            markerColor = '#1f77b4';
          }} else if (kind === 'facility') {{
            if (seenSpecial.has(stopId)) return;
            seenSpecial.add(stopId);
            label = 'Disposal Facility';
            markerColor = '#2ca02c';
          }} else {{
            serviceIndex += 1;
            label = `${serviceIndex}`;
          }}
          const width = Math.max(22, label.length * 7 + 12);
          const icon = L.divIcon({{
            className: 'stop-icon',
            html: `<div class="stop-dot" style="background:${{markerColor}}; border-color:${{markerColor}};">${{label}}</div>`,
            iconSize: [width, 22],
            iconAnchor: [width / 2, 11]
          }});
          L.marker(latlng, {{ icon }}).addTo(map);
        }});
      }});
    }}

    function formatDistance(m) {{
      if (m >= 1000) return (m / 1000).toFixed(2) + ' km';
      return Math.round(m) + ' m';
    }}

    function formatDuration(s) {{
      if (s >= 3600) return (s / 3600).toFixed(2) + ' h';
      if (s >= 60) return (s / 60).toFixed(1) + ' min';
      return Math.round(s) + ' s';
    }}

    function instruction(step) {{
      const name = step.name || 'unnamed road';
      const mod = step.modifier ? step.modifier + ' ' : '';
      switch (step.type) {{
        case 'depart': return `Depart on ${name}`;
        case 'arrive': return 'Arrive at destination';
        case 'turn': return `Turn ${mod}onto ${name}`;
        case 'end of road': return `At end of road, turn ${mod}onto ${name}`;
        case 'continue': return `Continue ${mod}on ${name}`;
        case 'merge': return `Merge ${mod}onto ${name}`;
        case 'fork': return `Keep ${mod}to stay on ${name}`;
        case 'roundabout':
          if (step.exit) return `Enter roundabout and take exit ${step.exit}`;
          return 'Enter roundabout';
        case 'on ramp': return `Take ramp ${mod}onto ${name}`;
        case 'off ramp': return `Take exit ${mod}onto ${name}`;
        case 'new name': return `Continue as ${name}`;
        default: return `Continue on ${name}`;
      }}
    }}

    function renderDirections() {{
      const container = document.getElementById('directions');
      if (!directions.vehicles) {{
        container.innerHTML = '<div class="meta">No directions available.</div>';
        return;
      }}
      const vehicleIds = Object.keys(directions.vehicles);
      if (!vehicleIds.length) {{
        container.innerHTML = '<div class="meta">No routes to display.</div>';
        return;
      }}
      container.innerHTML = '';
      for (const vehicleId of vehicleIds) {{
        const legs = directions.vehicles[vehicleId];
        if (!legs || !legs.length) continue;
        const totalDist = legs.reduce((acc, l) => acc + (l.distance_km || 0), 0);
        const totalDur = legs.reduce((acc, l) => acc + (l.duration_min || 0), 0);
        const vehicleDiv = document.createElement('div');
        vehicleDiv.className = 'vehicle';
        vehicleDiv.innerHTML = `
          <h3>${vehicleId}</h3>
          <div class="meta">Total: ${totalDist.toFixed(2)} km · ${totalDur.toFixed(1)} min</div>
        `;

        legs.forEach((leg, idx) => {{
          const legDiv = document.createElement('div');
          legDiv.className = 'leg';
          const header = document.createElement('div');
          header.className = 'meta';
          header.textContent = `Leg ${idx + 1}: ${leg.from} → ${leg.to} (${leg.distance_km.toFixed(2)} km, ${leg.duration_min.toFixed(1)} min)`;
          legDiv.appendChild(header);

          (leg.steps || []).forEach(step => {{
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step';
            stepDiv.textContent = `${instruction(step)} · ${formatDistance(step.distance_m)} · ${formatDuration(step.duration_s)}`;
            legDiv.appendChild(stepDiv);
          }});

          vehicleDiv.appendChild(legDiv);
        }});

        container.appendChild(vehicleDiv);
      }}
    }}

    addDirectionArrows();
    addStopMarkers();
    renderDirections();
  </script>
</body>
</html>
"""
    html = html.replace("{{", "{").replace("}}", "}")
    html = html.replace("Â·", "-").replace("â†’", "->")
    html = html.replace("__GEOJSON_DATA__", geojson_text).replace("__DIRECTIONS_DATA__", directions_text)

    with output_html_path.open("w", encoding="utf-8", newline="") as f:
        f.write(html)
