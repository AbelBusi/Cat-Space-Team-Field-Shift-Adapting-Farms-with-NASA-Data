"""Write ml-api/data/cube.npz: the monthly inputs 1998-2025 of every Lambayeque 2 km cell, built with the same fs_ml
code as every phase. The ML API runs the tested models on it (projections and what-if scenarios) without the raw CSVs.

    FIELDSHIFT_RAW_DIR=... ml/.venv/bin/python ml/scripts/export_api_cube.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as Poly

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from fs_ml import data as D, features as F, evaluate as E, project as P  # noqa: E402

OUT = ML.parent / "ml-api" / "data" / "cube.npz"
ADMIN = json.loads((ML.parent / "web/src/data/lambayeque_admin.json").read_text(encoding="utf-8"))


def build(load_years, suffix, keep):
    monthly, _ = D.load_gee_monthly(load_years); veg, _ = D.load_gee_quarterly(load_years)
    pw = {p: D.load_power(f"power_{p}{suffix}", load_years)[0] for p in ["t2m", "rh2m", "ws2m", "allsky"]}
    merra = pw["t2m"].merge(pw["rh2m"], on=["power_lat", "power_lon", "date"]).merge(pw["ws2m"], on=["power_lat", "power_lon", "date"])
    gaez = {k: D.load_gaez(k)[0] for k in F.GAEZ_FEATURES}
    cells = F.static_cells(D.cells_from_ids(monthly.cell_id), gaez, merra[["power_lat", "power_lon"]].drop_duplicates().reset_index(drop=True),
                           pw["allsky"][["power_lat", "power_lon"]].drop_duplicates().reset_index(drop=True))
    mp = F.build_monthly_panel(monthly, cells, merra, pw["allsky"]); qp = F.build_quarterly_panel(mp, veg)
    extra = pd.DataFrame({"cell_id": cells.cell_id.to_numpy(), "province": np.asarray(D.provinces_of(cells))})
    mp, qp = mp.merge(extra, on="cell_id"), qp.merge(extra, on="cell_id")
    return mp[mp.year.between(*keep)], qp[qp.year.between(*keep)]


parts = [build((1998, 2017), "", (1998, 2017)), build((2017, 2022), "_2018_2022", (2018, 2022)), build((2022, 2025), "_2023_2025", (2023, 2025))]
MP = pd.concat([p[0] for p in parts], ignore_index=True)
QP = pd.concat([p[1] for p in parts], ignore_index=True)
inside = set(MP.loc[MP.province != "outside", "cell_id"])
cube = P.build_cube(MP[MP.cell_id.isin(inside)], QP[QP.cell_id.isin(inside)])
c = cube.cells
pts = c[["lon", "lat"]].to_numpy()
district = np.full(len(c), "", dtype=object)
for prov in ADMIN["provinces"]:
    for d in prov["districts"]:
        m = np.zeros(len(c), bool)
        for ring in d["rings"]:
            m ^= Poly(np.asarray(ring)).contains_points(pts)
        district[m & (district == "")] = d["name"]

OUT.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(
    OUT,
    cell_id=c.cell_id.to_numpy(str), lat=c.lat.to_numpy(float), lon=c.lon.to_numpy(float),
    province=c.province.to_numpy(str), district=district.astype(str),
    **{f"soil__{k}": c[k].to_numpy(float) for k in F.SOIL},
    dates=cube.dates.strftime("%Y-%m-%d").to_numpy(str),
    quarters=np.array([str(q) for q in cube.quarters]), ndvi=cube.ndvi.astype(np.float32),
    **{f"v__{k}": v.astype(np.float32) for k, v in cube.v.items()},
)
print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB,", len(c), "cells,", cube.dates[0].date(), "->", cube.dates[-1].date())
