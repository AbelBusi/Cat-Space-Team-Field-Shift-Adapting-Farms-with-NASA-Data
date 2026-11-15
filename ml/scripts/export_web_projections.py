"""Write web/public/data/projections.json from ml/artifacts/projections (notebook 06) for the "What's ahead" screens.

Only cells inside Lambayeque (OpenStreetMap boundary) are kept. Values are integers ×1000 to keep the file small.
Usual values = mean of the observed GEE tables 1998-2025 per cell and month (soil water) or quarter (NDVI).

    FIELDSHIFT_RAW_DIR=... ml/.venv/bin/python ml/scripts/export_web_projections.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as Poly

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from fs_ml import data as D  # noqa: E402

ART = ML / "artifacts" / "projections"
OUT = ML.parent / "web" / "public" / "data" / "projections.json"
ADMIN = json.loads((ML.parent / "web/src/data/lambayeque_admin.json").read_text(encoding="utf-8"))
K = 1000
BANDS = {"base", "el_nino"}            # ensembles of real years: their 90 % range is shown
DRY_SEASON = ["2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]

proj = pd.read_parquet(ART / "projection_2026_cells.parquet")
card = json.loads((ART / "projection_card.json").read_text())
skill = pd.read_csv(ART / "hindcast_skill_by_lead.csv")

cells = proj[proj.province != "outside"].drop_duplicates("cell_id")[["cell_id", "lat", "lon", "province"]].sort_values("cell_id").reset_index(drop=True)
xy = cells.cell_id.str.split(",", expand=True).astype(int)
cells["x"], cells["y"] = xy[0], xy[1]
pts = cells[["lon", "lat"]].to_numpy()
cells["district"] = None
for prov in ADMIN["provinces"]:
    for d in prov["districts"]:
        inside = np.zeros(len(cells), bool)
        for ring in d["rings"]:
            inside ^= Poly(np.asarray(ring)).contains_points(pts)
        cells.loc[inside & cells.district.isna(), "district"] = d["name"]
cells["district"] = cells.district.fillna("")
provinces = sorted(cells.province.unique())
districts = sorted(d for d in cells.district.unique() if d)

# usual values 1998-2025 (observed)
monthly = pd.concat([D.load_gee_monthly((1998, 2025))[0]])
monthly["month"] = monthly.date.dt.month
clim_sm = monthly.groupby(["cell_id", "month"]).sm_root_m3m3.mean().unstack().reindex(cells.cell_id)
veg = D.load_gee_quarterly((1998, 2025))[0]
clim_nd = veg.groupby(["cell_id", "quarter"]).ndvi.mean().unstack().reindex(cells.cell_id)

def block(var, n_periods):
    p = proj[(proj.variable == var) & proj.cell_id.isin(cells.cell_id)]
    out, periods = {}, None
    for scen, g in p.groupby("scenario", sort=False):
        g = g.set_index(["cell_id", "lead"]).sort_index()
        periods = g.reset_index().drop_duplicates("lead").sort_values("lead").period.tolist()
        arr = lambda col: (g[col].unstack("lead").reindex(cells.cell_id).to_numpy(float) * K).round()
        flat = lambda a: [None if np.isnan(v) else int(v) for v in a.reshape(-1)]
        out[scen] = {"median": flat(arr("median"))}
        if scen in BANDS:
            out[scen] |= {"low": flat(arr("low_90")), "high": flat(arr("high_90"))}
        out[scen]["members"] = int(g.members.iloc[0])
    assert len(periods) == n_periods
    return out, periods

sm, sm_periods = block("soil_water_28_100cm", 12)
nd, nd_periods = block("ndvi", 4)
usual_sm = (clim_sm[[int(p[5:7]) for p in sm_periods]].to_numpy() * K).round()
usual_nd = (clim_nd[[int(p[-1]) for p in nd_periods]].to_numpy() * K).round()
flat = lambda a: [None if np.isnan(v) else int(v) for v in a.reshape(-1)]

# district summary: dry-season soil water and Q3-Q4 greenness, per scenario (median of cell medians)
summ = []
p = proj[proj.cell_id.isin(cells.cell_id)].merge(cells[["cell_id", "district"]], on="cell_id")
for scen in p.scenario.unique():
    a = p[(p.scenario == scen) & (p.variable == "soil_water_28_100cm") & p.period.isin(DRY_SEASON)].groupby(["district", "cell_id"])["median"].mean().groupby("district").median()
    b = p[(p.scenario == scen) & (p.variable == "ndvi") & p.period.isin(["2026Q3", "2026Q4"])].groupby(["district", "cell_id"])["median"].mean().groupby("district").median()
    n = p[(p.scenario == scen) & (p.variable == "ndvi")].drop_duplicates("cell_id").groupby("district").size()
    for d in a.index:
        if d:
            summ.append({"district": d, "scenario": scen, "dry_season_soil_water": int(round(a[d] * K)), "q3q4_ndvi": int(round(b.get(d, np.nan) * K)) if d in b else None, "cells": int(n.get(d, 0))})

sk = lambda v: [{"lead": int(r.lead), "skill": round(r.skill, 3), "low": round(r.skill_ci_low, 3), "high": round(r.skill_ci_high, 3)}
                for r in skill[(skill.variable == v) & (skill.period == "validation")].itertuples()]
base_med = np.array([v for v in sm["base"]["median"] if v is not None])
nd_med = np.array([v for v in nd["base"]["median"] if v is not None])
doc = {
    "meta": {
        "start": "2025-12", "scale": K, "grid_step_deg": D.GRID_STEP,
        "periods": {"soil_water": sm_periods, "ndvi": nd_periods},
        "useful_lead": card["useful_lead"], "skill_by_lead": {"soil_water": sk("sm"), "ndvi": sk("ndvi")},
        "coverage_2023_2025": {k: round(v["coverage_90"], 3) for k, v in card["coverage_2023_2025"].items()},
        "scenarios": card["scenarios"], "domain": {"soil_water": [int(np.percentile(base_med, 2)), int(np.percentile(base_med, 98))],
                                                   "ndvi": [int(np.percentile(nd_med, 2)), int(np.percentile(nd_med, 98))]},
        "usual": "mean of the observed values 1998-2025 for that cell and month (soil water) or quarter (NDVI)",
        "source": "ml/notebooks/06_projections.ipynb with the tested XGBoost models (ml/artifacts/final_model); see docs/ML_PROJECTIONS.md",
        "not_for": card["not_for"],
    },
    "cells": {"x": cells.x.tolist(), "y": cells.y.tolist(), "province": [provinces.index(v) for v in cells.province],
              "district": [districts.index(v) if v else -1 for v in cells.district]},
    "provinces": provinces, "districts": districts,
    "soil_water": sm | {"usual": flat(usual_sm)}, "ndvi": nd | {"usual": flat(usual_nd)},
    "district_summary": summ,
}
OUT.write_text(json.dumps(doc, separators=(",", ":")))
print(OUT, f"{OUT.stat().st_size / 1e6:.2f} MB,", len(cells), "cells,", len(districts), "districts")
