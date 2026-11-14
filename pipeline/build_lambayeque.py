"""Builds web/public/data/lambayeque.json: the Lambayeque 0.1° grid (IMERG's own 420 cells) with every
downloaded NASA dataset folded in. The web app reads this one small file.

Inputs (data/manual/, see data/STRUCTURE.md):
  imerg/   288 monthly GPM IMERG V07 files, already cut to the bbox
  nasadem/ NASADEM_HGT 1" tiles (zip: .hgt big-endian int16 + .swb water mask)
  grace/   JPL GRACE/GRACE-FO mascon CRI RL06.3 v04

    pipeline/.venv/bin/python pipeline/build_lambayeque.py
"""
import calendar
import datetime
import glob
import json
import pathlib
import zipfile

import numpy as np
import xarray as xr

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/manual"
OUT = ROOT / "web/public/data/lambayeque.json"
BBOX = {"west": -80.7, "south": -7.2, "east": -78.8, "north": -5.4}
# Coastal El Niño years: Jan-Apr NOAA Niño 1+2 anomaly >= 0.8 °C (same list as NINO_COASTAL in web/src/lib/nasa.js).
# The ONI (central Pacific) list misses them: with ONI years, Chiclayo even shows LESS rain than usual.
NINO_YEARS = [2016, 2017, 2023]


def imerg():
    files = sorted(glob.glob(str(RAW / "imerg/*.nc4")))
    assert len(files) == 288, f"expected 288 IMERG months, found {len(files)}"
    first = xr.open_dataset(files[0], group="Grid", decode_times=False)
    lat, lon = first.lat.values, first.lon.values                       # 20 lats (south→north), 21 lons
    mm = np.zeros((288, len(lat), len(lon)), np.float32)
    years = []
    for n, f in enumerate(files):
        ym = f.split("3IMERG.")[1][:6]                                 # month from the file name (time uses a julian calendar)
        y, m = int(ym[:4]), int(ym[4:])
        years.append(y)
        p = xr.open_dataset(f, group="Grid", decode_times=False).precipitation.values[0].T   # (lon, lat) → (lat, lon)
        mm[n] = np.where(p < 0, np.nan, p * 24 * calendar.monthrange(y, m)[1])              # mm/hr → mm/month
    by = mm.reshape(24, 12, len(lat), len(lon))
    yrs = np.arange(2001, 2025)
    nino = np.isin(yrs, NINO_YEARS)
    return lat, lon, {
        "typical": np.nanmean(by, axis=0),                              # (12, lat, lon)
        "nino": np.nanmean(by[nino], axis=0),
        "annual": np.nansum(by, axis=1),                                # (24, lat, lon)
    }


def terrain(lat, lon):
    """Mean elevation, mean slope and land share for each 0.1° IMERG cell, from NASADEM at ~90 m."""
    step = 3                                                            # 1" → 3" (~90 m) keeps it light
    n = 3600 // step
    lat0, lon0 = -8, -81                                                # mosaic south-west corner (3 × 3 tiles)
    elev = np.full((3 * n, 3 * n), np.nan, np.float32)                  # row 0 = north edge
    for z in glob.glob(str(RAW / "nasadem/*.zip")):
        tile = pathlib.Path(z).stem.split("_")[-1]                      # e.g. s07w080 = SW corner lat -7, lon -80
        tlat, tlon = -int(tile[1:3]), -int(tile[4:7])
        with zipfile.ZipFile(z) as zf:
            h = np.frombuffer(zf.read(f"{tile}.hgt"), ">i2").reshape(3601, 3601)[:3600, :3600]
            w = np.frombuffer(zf.read(f"{tile}.swb"), "u1").reshape(3601, 3601)[:3600, :3600]
        h = np.where((w > 0) | (h < 0), np.nan, h).astype(np.float32)[::step, ::step]   # sea, lakes and voids → NaN
        r = (lat0 + 3 - (tlat + 1)) * n                                 # mosaic row of the tile's north edge
        c = (tlon - lon0) * n
        elev[r:r + n, c:c + n] = h
    res = step / 3600 * 111_320                                         # metres per pixel north-south
    gy, gx = np.gradient(elev, res, res * np.cos(np.radians(-6.5)))
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    out = {k: np.full((len(lat), len(lon)), np.nan) for k in ("elev", "slope", "land")}
    for i, la in enumerate(lat):
        for j, lo in enumerate(lon):
            r0, r1 = int((lat0 + 3 - (la + 0.05)) * n), int((lat0 + 3 - (la - 0.05)) * n)
            c0, c1 = int((lo - 0.05 - lon0) * n), int((lo + 0.05 - lon0) * n)
            e, s = elev[r0:r1, c0:c1], slope[r0:r1, c0:c1]
            land = np.isfinite(e)
            out["land"][i, j] = land.mean()
            if land.any():
                out["elev"][i, j] = np.nanmean(e)
                out["slope"][i, j] = np.nanmean(s)
    return out


def grace():
    f = glob.glob(str(RAW / "grace/*.nc"))[0]
    g = xr.open_dataset(f, decode_times=False)
    box = dict(lat=slice(BBOX["south"] - 0.25, BBOX["north"] + 0.25), lon=slice(BBOX["west"] % 360 - 0.25, BBOX["east"] % 360 + 0.25))
    cm = (g.lwe_thickness.sel(**box) * g.scale_factor.sel(**box)).mean(dim=("lat", "lon")).values   # JPL CRI gain factors for land
    days = g.time.values
    dates = [(datetime.date(2002, 1, 1) + datetime.timedelta(days=float(d))).isoformat()[:7] for d in days]
    years = days / 365.25
    return {"dates": dates, "cm": [round(float(v), 2) for v in cm], "trend_cm_per_year": round(float(np.polyfit(years, cm, 1)[0]), 3)}


def flat(a, nd=1):
    """Cell-major list (index = lat_i * nlon + lon_j), NaN → None, rounded."""
    return [None if not np.isfinite(v) else round(float(v), nd) for v in np.asarray(a).ravel()]


if __name__ == "__main__":
    lat, lon, rain = imerg()
    ter = terrain(lat, lon)
    gr = grace()
    nl, nn = len(lat), len(lon)
    cells = lambda a: [flat(a[:, i, j], 0) for i in range(nl) for j in range(nn)]
    out = {
        "meta": {"region": "Lambayeque, Peru", "bbox": BBOX, "built": datetime.date.today().isoformat(),
                 "grid": {"lat": [round(float(x), 2) for x in lat], "lon": [round(float(x), 2) for x in lon], "step": 0.1,
                          "index": "cell = lat_index * len(lon) + lon_index"},
                 "sources": {"rain": "GPM IMERG Final V07 monthly (GPM_3IMERGM), 0.1°, 2001-2024",
                             "terrain": "NASADEM_HGT v001, resampled to ~90 m, water masked with .swb",
                             "water": "JPL GRACE/GRACE-FO mascon CRI RL06.3 v04, scale_factor applied, mean over the bbox"},
                 "nino_years": NINO_YEARS},
        "rain": {"typical": cells(rain["typical"]), "nino": cells(rain["nino"]), "annual_years": list(range(2001, 2025)),
                 "annual": cells(rain["annual"])},
        "terrain": {"elev_m": flat(ter["elev"], 0), "slope_deg": flat(ter["slope"], 1), "land_share": flat(ter["land"], 2)},
        "water": gr,
    }
    # Self-check
    assert len(out["rain"]["typical"]) == nl * nn and all(len(c) == 12 for c in out["rain"]["typical"])
    assert any(v is not None for v in out["terrain"]["elev_m"]), "no land found in NASADEM mosaic"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB): {nl}×{nn} cells, GRACE trend {gr['trend_cm_per_year']} cm/yr")
