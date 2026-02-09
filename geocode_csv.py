import argparse
import csv
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _load_cache(path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(path, cache):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def nominatim_geocode(address, user_agent, timeout_s=10):
    params = {
        "q": address,
        "format": "jsonv2",
        "limit": 1,
    }
    url = "https://nominatim.openstreetmap.org/search?" + urlencode(params)
    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def geocode_csv(
    input_path,
    output_path,
    address_fields,
    lat_field="lat",
    lon_field="lon",
    user_agent="RenovisionGeocoder/0.1 (contact@example.com)",
    cache_path=None,
    pause_s=1.0,
    timeout_s=10,
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    cache = _load_cache(Path(cache_path)) if cache_path else {}

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"No headers found in {input_path}")
        rows = list(reader)
        fieldnames = reader.fieldnames

    for row in rows:
        if row.get(lat_field) and row.get(lon_field):
            continue

        parts = []
        for field in address_fields:
            value = row.get(field, "").strip()
            if value:
                parts.append(value)
        address = ", ".join(parts)
        if not address:
            raise ValueError(
                f"Row is missing both {lat_field}/{lon_field} and address fields {address_fields}: {row}"
            )

        if address in cache:
            lat, lon = cache[address]
        else:
            result = nominatim_geocode(address, user_agent=user_agent, timeout_s=timeout_s)
            if result is None:
                raise ValueError(f"Could not geocode address: {address}")
            lat, lon = result
            cache[address] = [lat, lon]
            time.sleep(pause_s)

        row[lat_field] = str(lat)
        row[lon_field] = str(lon)

    if lat_field not in fieldnames:
        fieldnames.append(lat_field)
    if lon_field not in fieldnames:
        fieldnames.append(lon_field)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if cache_path:
        _save_cache(Path(cache_path), cache)


def main():
    parser = argparse.ArgumentParser(
        description="Geocode CSV rows using Nominatim and write lat/lon columns."
    )
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument(
        "--address-fields",
        default="address",
        help="Comma-separated list of fields to build the address",
    )
    parser.add_argument("--lat-field", default="lat", help="Latitude column name")
    parser.add_argument("--lon-field", default="lon", help="Longitude column name")
    parser.add_argument(
        "--user-agent",
        default="RenovisionGeocoder/0.1 (contact@example.com)",
        help="User-Agent string required by Nominatim (set to your email/contact)",
    )
    parser.add_argument(
        "--cache-file",
        default="data/geocode_cache.json",
        help="Cache file to avoid repeated geocoding",
    )
    parser.add_argument("--pause-s", type=float, default=1.0, help="Seconds between API calls")
    parser.add_argument("--timeout-s", type=int, default=10, help="HTTP timeout in seconds")
    args = parser.parse_args()

    address_fields = [f.strip() for f in args.address_fields.split(",") if f.strip()]
    if not address_fields:
        raise ValueError("At least one address field is required.")

    geocode_csv(
        args.input,
        args.output,
        address_fields=address_fields,
        lat_field=args.lat_field,
        lon_field=args.lon_field,
        user_agent=args.user_agent,
        cache_path=args.cache_file,
        pause_s=args.pause_s,
        timeout_s=args.timeout_s,
    )


if __name__ == "__main__":
    main()
