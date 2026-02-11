import csv
from pathlib import Path

from entities import Customer, Depot, DisposalFacility, Vehicle


def _require_fields(row, required, path):
    missing = []
    for f in required:
        if f not in row:
            missing.append(f)
            continue
        value = row[f]
        if value is None:
            missing.append(f)
            continue
        if str(value).strip() == "":
            missing.append(f)
    if missing:
        raise ValueError(f"Missing fields {missing} in {path}")


def _to_int(value, field, path):
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {field} in {path}: {value}") from exc


def _to_float(value, field, path):
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {field} in {path}: {value}") from exc


def load_customers_csv(path):
    path = Path(path)
    customers = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _require_fields(row, ["id", "lat", "lon", "demand", "service"], path)
            customers.append(
                Customer(
                    id=row["id"],
                    demand=_to_int(row["demand"], "demand", path),
                    service=_to_int(row["service"], "service", path),
                    lat=_to_float(row["lat"], "lat", path),
                    lon=_to_float(row["lon"], "lon", path),
                )
            )
    if not customers:
        raise ValueError(f"No customers found in {path}")
    return customers


def load_vehicles_csv(path):
    path = Path(path)
    vehicles = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _require_fields(row, ["id", "capacity", "max_shift"], path)
            startup_cost = row.get("startup_cost", "")
            vehicles.append(
                Vehicle(
                    id=row["id"],
                    capacity=_to_int(row["capacity"], "capacity", path),
                    max_shift=_to_int(row["max_shift"], "max_shift", path),
                    startup_cost=_to_int(startup_cost, "startup_cost", path)
                    if startup_cost != ""
                    else 0,
                )
            )
    if not vehicles:
        raise ValueError(f"No vehicles found in {path}")
    return vehicles


def load_depots_csv(path):
    path = Path(path)
    depots = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _require_fields(row, ["id", "lat", "lon"], path)
            depots.append(
                Depot(
                    id=row["id"],
                    lat=_to_float(row["lat"], "lat", path),
                    lon=_to_float(row["lon"], "lon", path),
                )
            )
    if not depots:
        raise ValueError(f"No depots found in {path}")
    return depots


def load_facilities_csv(path):
    path = Path(path)
    facilities = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _require_fields(row, ["id", "lat", "lon"], path)
            facilities.append(
                DisposalFacility(
                    id=row["id"],
                    lat=_to_float(row["lat"], "lat", path),
                    lon=_to_float(row["lon"], "lon", path),
                )
            )
    if not facilities:
        raise ValueError(f"No facilities found in {path}")
    return facilities
