# Data Schema

## customers.csv
Required columns:
- `id` (string): Unique customer ID.
- `lat` (float): Latitude or x-coordinate.
- `lon` (float): Longitude or y-coordinate.
- `demand` (int): Demand units to collect.
- `service` (int): Service time at customer.
Optional columns:
- `address` (string): Full street address for geocoding (used to populate `lat`/`lon`).

## vehicles.csv
Required columns:
- `id` (string): Unique vehicle ID.
- `capacity` (int): Vehicle capacity.
- `max_shift` (int): Maximum shift duration.

Optional columns:
- `startup_cost` (int): Fixed cost for using the vehicle (default 0).

## depots.csv
Required columns:
- `id` (string): Depot ID.
- `lat` (float): Latitude or x-coordinate.
- `lon` (float): Longitude or y-coordinate.
Optional columns:
- `address` (string): Full street address for geocoding (used to populate `lat`/`lon`).

## facilities.csv
Required columns:
- `id` (string): Disposal facility ID.
- `lat` (float): Latitude or x-coordinate.
- `lon` (float): Longitude or y-coordinate.
Optional columns:
- `address` (string): Full street address for geocoding (used to populate `lat`/`lon`).
