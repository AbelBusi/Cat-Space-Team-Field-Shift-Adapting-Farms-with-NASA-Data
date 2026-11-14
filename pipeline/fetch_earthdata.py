"""Downloads the login-only NASA datasets that are small enough to fetch whole, and turns them into
small per-place tables in data/ (places from data/places.csv).

First, ONE time, log in yourself (it asks for your Earthdata username and password and saves them in ~/.netrc):
    pipeline/.venv/bin/python -c "import earthaccess as ea; ea.login(strategy='interactive', persist=True)"
Then:
    pipeline/.venv/bin/python pipeline/fetch_earthdata.py            # grace, dem, imerg
    pipeline/.venv/bin/python pipeline/fetch_earthdata.py grace      # only one: grace | dem | imerg

Raw files go to data/manual/<dataset>/ (git-ignored). Sizes: GRACE 40 MB, NASADEM ~12 MB per place, IMERG 5 GB.
SMAP, HLS and ECOSTRESS are hundreds of GB as raw files: get them as point samples with AppEEARS (data/README.md).
"""
import calendar
import csv
import datetime
import json
import pathlib
import sys
import zipfile

import earthaccess as ea
import h5py
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "manual"


def places():
    with open(DATA / "places.csv", newline="") as f:
        return [{"id": r["ID"], "lat": float(r["Latitude"]), "lon": float(r["Longitude"])} for r in csv.DictReader(f)]


def save(folder, place_id, obj):
    (DATA / folder).mkdir(exist_ok=True)
    (DATA / folder / f"{place_id}.json").write_text(json.dumps(obj, indent=1))
    print(f"  ok   {folder}/{place_id}.json")


def download(results, folder):
    out = RAW / folder
    out.mkdir(parents=True, exist_ok=True)
    files = ea.download(results, str(out))   # skips files that are already there
    return [pathlib.Path(f) for f in files]


def grace():
    """Underground + surface water: one global file, JPL mascons (≈3° blocks sampled on a 0.5° grid)."""
    print("grace:")
    [path] = download(ea.search_data(short_name="TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4"), "grace")
    with h5py.File(path, "r") as f:
        lat, lon = f["lat"][:], f["lon"][:]                       # lon is 0..360
        days = f["time"][:]                                      # days since 2002-01-01
        lwe = f["lwe_thickness"]                                 # (time, lat, lon), cm of water
        dates = [datetime.date(2002, 1, 1) + datetime.timedelta(days=float(d)) for d in days]
        years = np.array([(d - dates[0]).days / 365.25 for d in dates])
        for p in places():
            i, j = np.abs(lat - p["lat"]).argmin(), np.abs(lon - (p["lon"] % 360)).argmin()
            cm = lwe[:, i, j].astype(float) * float(f["scale_factor"][i, j])   # JPL CRI gain factor for land
            trend = float(np.polyfit(years, cm, 1)[0])
            save("grace", p["id"], {
                "source": "JPL GRACE/GRACE-FO mascon CRI RL06.3 v04", "units": "cm of water, anomaly vs 2004-2009, scale_factor applied",
                "trend_cm_per_year": round(trend, 3), "cell": [float(lat[i]), float(lon[j])],
                "series": [{"date": d.isoformat(), "cm": round(v, 2)} for d, v in zip(dates, cm)]})


def dem():
    """Elevation and slope at each place from NASADEM (1 arc-second ≈ 30 m)."""
    print("dem:")
    for p in places():
        lat, lon = p["lat"], p["lon"]
        results = ea.search_data(short_name="NASADEM_HGT", bounding_box=(lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001))
        if not results:
            print(f"  skip {p['id']}: no NASADEM tile (water or outside 60°N–56°S)")
            continue
        [zpath] = download(results[:1], "nasadem")
        with zipfile.ZipFile(zpath) as z:
            name = next(n for n in z.namelist() if n.endswith(".hgt"))
            h = np.frombuffer(z.read(name), dtype=">i2").reshape(3601, 3601).astype(float)
        # Tile name is its south-west corner; row 0 is the north edge.
        lat0, lon0 = np.floor(lat), np.floor(lon)
        r, c = int(round((lat0 + 1 - lat) * 3600)), int(round((lon - lon0) * 3600))
        r, c = min(max(r, 1), 3599), min(max(c, 1), 3599)
        dy = 6_371_008.8 * np.pi / 180 / 3600            # metres per arc-second north-south
        dx = dy * np.cos(np.radians(lat))
        gy, gx = (h[r - 1, c] - h[r + 1, c]) / (2 * dy), (h[r, c + 1] - h[r, c - 1]) / (2 * dx)
        save("terrain", p["id"], {"source": "NASADEM_HGT v001", "elevation_m": int(h[r, c]),
                                  "slope_deg": round(float(np.degrees(np.arctan(np.hypot(gx, gy)))), 2)})


def imerg():
    """Monthly rain 2001-2024 from GPM IMERG Final V07 (0.1°). Downloads 288 global files (≈5 GB)."""
    print("imerg: downloading 288 monthly files (~5 GB), this takes a while...")
    paths = sorted(download(ea.search_data(short_name="GPM_3IMERGM", temporal=("2001-01-01", "2024-12-31")), "imerg"))
    pl = places()
    out = {p["id"]: {} for p in pl}
    for path in paths:
        month = path.name.split(".")[4][:6]                      # 3B-MO.MS.MRG.3IMERG.YYYYMMDD-...
        y, m = int(month[:4]), int(month[4:])
        with h5py.File(path, "r") as f:
            pr = f["Grid/precipitation"]                         # mm/hour, (time, lon 3600, lat 1800) in V07
            lon_first = pr.shape[1] == 3600
            for p in pl:
                i, j = int((p["lon"] + 180) / 0.1), int((p["lat"] + 90) / 0.1)
                v = float(pr[0, i, j] if lon_first else pr[0, j, i])
                out[p["id"]][f"{y}-{m:02d}"] = None if v < 0 else round(v * 24 * calendar.monthrange(y, m)[1], 1)
    for p in pl:
        save("imerg", p["id"], {"source": "GPM IMERG Final V07 monthly (GPM_3IMERGM)", "units": "mm per month", "monthly": out[p["id"]]})


if __name__ == "__main__":
    if not ea.login(strategy="netrc"):
        sys.exit("Not logged in. Run once:\n  pipeline/.venv/bin/python -c \"import earthaccess as ea; ea.login(strategy='interactive', persist=True)\"")
    jobs = {"grace": grace, "dem": dem, "imerg": imerg}
    for name in sys.argv[1:] or ["grace", "dem", "imerg"]:
        if name not in jobs:
            sys.exit(f"Unknown dataset {name!r}. Use: grace dem imerg")
        jobs[name]()
