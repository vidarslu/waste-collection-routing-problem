# Waste Collection Routing Optimization

This repository works on a model to optimize real-world garbage collection operations. The time horizon is operational, and the objective is cost reduction.


Waste collection routing prototype. This repository contains a Gurobi-based optimization model, data schemas, and helper utilities to ingest CSVs, build an instance, solve, and visualize routes.

## Quick Start
1. Update CSVs in `data/` to reflect your customers, vehicles, depot, and facility.
2. Run the solver:

```bash
python model.py
```

## Project Structure
- `model.py`: Main optimization model, solver configuration, route summary, and visualization.
- `entities.py`: Domain classes for vehicles, customers, depot, and disposal facility.
- `data_io.py`: CSV loaders with validation.
- `instance_builder.py`: Converts domain objects into model inputs (sets, parameters, travel costs/times).
- `data/`: Sample CSV inputs for customers, vehicles, depot, and facility.
- `DATA_SCHEMA.md`: CSV format specification.
- `model_doc.tex`: LaTeX documentation of the mathematical model.
- `ROADMAP.md`: Product roadmap checklist.

## Notes
- The current model assumes exactly one depot and one disposal facility.
- Travel costs/times are derived from Euclidean distances between coordinates (placeholder for map APIs).

## Real Locations (Addresses -> Lat/Lon)
If you have real addresses, geocode them into `lat`/`lon` and switch to great-circle distances.

1. Add an `address` column (and optionally other address parts) to `data/customers.csv`, `data/depots.csv`, and `data/facilities.csv`.
2. Run the geocoder to fill missing `lat`/`lon`:

```bash
python geocode_csv.py --input data/customers.csv --output data/customers_geocoded.csv --address-fields address --user-agent "YourApp/1.0 (you@example.com)"
python geocode_csv.py --input data/depots.csv --output data/depots_geocoded.csv --address-fields address --user-agent "YourApp/1.0 (you@example.com)"
python geocode_csv.py --input data/facilities.csv --output data/facilities_geocoded.csv --address-fields address --user-agent "YourApp/1.0 (you@example.com)"
```

3. Point `model.py` (or your own runner) at the geocoded files and set `DISTANCE_MODE = "haversine_km"`.

The geocoder uses OpenStreetMap Nominatim, respects a pause between calls, and writes a cache file to avoid repeat lookups.

## Road Distances (OSM / OSRM)
For actual road distances and drive times, the project can query OSRM's public demo server (OpenStreetMap data) to build a distance/time matrix.

1. Ensure your CSVs have valid `lat`/`lon`.
2. In `model.py`, set `USE_ROAD_DISTANCES = True` and update `OSRM_USER_AGENT` with your contact.
3. Run `python model.py` to fetch and cache the matrix at `data/road_matrix.json`.

Notes:
- The OSRM public server is intended for small demos; for production, run your own OSRM instance or use a managed routing provider.
- The road time matrix is in minutes; keep your `max_shift` and `service` units consistent.

## Map Output + Directions
To visualize routes on a real map and save driving directions:

1. Ensure `lat`/`lon` are real coordinates and set `USE_ROAD_DISTANCES = True` (optional but recommended).
2. In `model.py`, keep `EXPORT_ROUTES = True` and set `OSRM_ROUTE_USER_AGENT` to your contact.
3. Run `python model.py`.

Outputs:
- `data/routes.geojson`: GeoJSON with route lines and stop points.
- `data/directions.json`: Step-by-step OSRM directions per vehicle and leg.
- `data/routes_map.html`: A Leaflet map you can open in a browser to view the exact driving routes.
