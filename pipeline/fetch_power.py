"""Monthly climate normals for any point on Earth from NASA POWER. No login or API key needed.

    python pipeline/fetch_power.py -6.77 -79.84      # Chiclayo, Peru

Saves pipeline/out/power_<lat>_<lon>.json and prints a table. This is the first real-data step:
the same numbers can replace the hypothetical "heat" and "rain" layers in build_data.py.
"""
import calendar
import json
import pathlib
import sys
import urllib.error
import urllib.request

PARAMS = {
    "T2M": "Mean air temperature (°C)",
    "T2M_MAX": "Hottest hour of that month in the whole record (°C)",  # heat peaks
    "T2M_MIN": "Coldest hour of that month in the whole record (°C)",  # frost risk
    "PRECTOTCORR": "Rain (mm/day)",              # converted to mm/month below
    "ALLSKY_SFC_SW_DWN": "Solar radiation (kWh/m²/day)",
    "RH2M": "Relative humidity (%)",
    "WS2M": "Wind at 2 m (m/s)",
}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
URL = ("https://power.larc.nasa.gov/api/temporal/climatology/point"
       "?parameters={p}&community=AG&latitude={lat}&longitude={lon}&format=JSON")


def fetch(lat, lon):
    url = URL.format(p=",".join(PARAMS), lat=lat, lon=lon)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"NASA POWER answered {e.code}: {e.read()[:300].decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach NASA POWER ({e.reason}). Check your internet connection.")
    raw = body["properties"]["parameter"]
    out = {}
    for p in PARAMS:
        vals = [None if raw[p][m] == -999 else raw[p][m] for m in MONTHS]  # -999 is POWER's "no data"
        if p == "PRECTOTCORR":
            vals = [None if v is None else round(v * calendar.monthrange(2001, i + 1)[1], 1) for i, v in enumerate(vals)]
        out[p] = vals
    return {"lat": lat, "lon": lon, "source": "NASA POWER climatology API, community AG",
            "api_version": body.get("header", {}).get("api", {}).get("version"), "monthly": out}


if __name__ == "__main__":
    try:
        lat, lon = float(sys.argv[1]), float(sys.argv[2])
    except (IndexError, ValueError):
        sys.exit("Usage: python pipeline/fetch_power.py <lat> <lon>   e.g. -6.77 -79.84")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        sys.exit("Latitude must be -90..90 and longitude -180..180.")

    data = fetch(lat, lon)
    path = pathlib.Path(__file__).parent / "out" / f"power_{lat}_{lon}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=1))

    print(f"{'':12}" + "".join(f"{m:>7}" for m in MONTHS))
    for p, vals in data["monthly"].items():
        label = "PRECTOT mm" if p == "PRECTOTCORR" else p[:12]
        print(f"{label:12}" + "".join(f"{'-' if v is None else v:>7}" for v in vals))
    print(f"\nSaved {path}")
