"""NDVI projections chained on the v3 soil water model: hindcast skill, useful lead and range corrections.

The NDVI model is the tested v1; only the soil water that feeds it changes (v3). Same hindcast design as
ml/notebooks/06_projections.ipynb (starts at the end of every quarter Dec 2017 - Sep 2022, leads 1-4, analog years
1998-2017 with no month after Dec 2017; second look Dec 2022 - Sep 2025). Writes ml/artifacts/v3_era5_rain/ndvi_chain.json.

    FIELDSHIFT_RAW_DIR=... ml/.venv/bin/python ml/scripts/v3_ndvi_chain.py
"""
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from fs_ml import data as D, evaluate as E, era5 as R, features as F, project as P  # noqa: E402
from fs_ml.predict import load  # noqa: E402

warnings.filterwarnings("ignore", message="(All-NaN slice|Mean of empty slice)")
ART = ML / "artifacts" / "v3_era5_rain"
ND = load("ndvi_quarterly")
prep = json.loads((ART / "sm_root_monthly" / "preprocessing.json").read_text())
m3 = xgb.XGBRegressor(); m3.load_model(ART / "sm_root_monthly" / "model.ubj")
V3 = {"model": m3, "features": prep["feature_names_in_order"]}


def build(load_years, suffix, keep):
    monthly, _ = D.load_gee_monthly(load_years); veg, _ = D.load_gee_quarterly(load_years)
    pw = {p: D.load_power(f"power_{p}{suffix}", load_years)[0] for p in ["t2m", "rh2m", "ws2m", "allsky"]}
    merra = pw["t2m"].merge(pw["rh2m"], on=["power_lat", "power_lon", "date"]).merge(pw["ws2m"], on=["power_lat", "power_lon", "date"])
    gaez = {k: D.load_gaez(k)[0] for k in F.GAEZ_FEATURES}
    cells = F.static_cells(D.cells_from_ids(monthly.cell_id), gaez, merra[["power_lat", "power_lon"]].drop_duplicates().reset_index(drop=True),
                           pw["allsky"][["power_lat", "power_lon"]].drop_duplicates().reset_index(drop=True))
    mp = F.build_monthly_panel(monthly, cells, merra, pw["allsky"]); qp = F.build_quarterly_panel(mp, veg)
    extra = pd.DataFrame({"cell_id": cells.cell_id.to_numpy(), "block": np.asarray(E.spatial_blocks(cells.lat, cells.lon))})
    return mp.merge(extra, on="cell_id")[lambda d: d.year.between(*keep)], qp.merge(extra, on="cell_id")[lambda d: d.year.between(*keep)]


parts = [build((1998, 2017), "", (1998, 2017)), build((2017, 2022), "_2018_2022", (2018, 2022)), build((2022, 2025), "_2023_2025", (2023, 2025))]
MP = pd.concat([p[0] for p in parts], ignore_index=True); QP = pd.concat([p[1] for p in parts], ignore_index=True)
MP = R.add_to_monthly(MP, R.load_era5_rain(MP.cell_id.unique()))
CUBE = P.build_cube(MP, QP)
QY = np.array([q.year for q in CUBE.quarters]); QQ = np.array([q.quarter for q in CUBE.quarters])
CLIM = {q: np.nanmean(CUBE.ndvi[:, (QQ == q) & (QY <= 2017)], axis=1) for q in range(1, 5)}
CLIM = {q: np.where(np.isnan(v), np.nanmean(v), v) for q, v in CLIM.items()}


def hindcast(first, last_start, last_q):
    out = []
    for q0 in pd.period_range(first, last_start, freq="Q"):
        s = q0.to_timestamp(how="end").normalize().replace(day=1)
        h = min(4, (pd.Period(last_q) - q0).n)
        sm = P.project_sm(V3, CUBE, s, 3 * h, list(range(1998, 2018)), until="2017-12-01")
        run = P.project_ndvi(ND, CUBE, sm)
        lo, med, hi = np.quantile(run["members"], [0.05, 0.5, 0.95], axis=0)
        obs0 = CUBE.ndvi[:, CUBE.quarters.get_loc(q0)]
        for k, q in enumerate(run["quarters"]):
            y = CUBE.ndvi[:, CUBE.quarters.get_loc(q)]; ok = ~np.isnan(y)
            pers = np.where(np.isnan(obs0), CLIM[q.quarter], obs0)
            out.append(pd.DataFrame({"lead": k + 1, "block": CUBE.cells.block[ok], "y": y[ok], "median": med[ok, k], "lo": lo[ok, k], "hi": hi[ok, k],
                                     "climatology": CLIM[q.quarter][ok], "persistence": pers[ok]}))
    return pd.concat(out, ignore_index=True)


HV, HT = hindcast("2017Q4", "2022Q3", "2022Q4"), hindcast("2022Q4", "2025Q3", "2025Q4")
rows = []
for L, g in HV.groupby("lead"):
    t = E.block_bootstrap(g.y.to_numpy(), {"projection": g["median"].to_numpy(), "climatology": g.climatology.to_numpy(), "persistence": g.persistence.to_numpy()},
                          g.block.to_numpy(), "projection", 1000, 42).set_index(["model", "metric"])
    best = "climatology" if t.loc[("climatology", "RMSE"), "value"] < t.loc[("persistence", "RMSE"), "value"] else "persistence"
    sk = t.loc[("projection", f"skill vs {best}")]
    rows.append({"lead": int(L), "best_rule": best, "skill": float(sk.value), "skill_ci_low": float(sk.ci_low), "skill_ci_high": float(sk.ci_high)})
useful = 0
for r in rows:
    if r["skill_ci_low"] > 0: useful = r["lead"]
    else: break
sc = np.maximum(HV.lo - HV.y, HV.y - HV.hi)
corr = {int(L): float(np.sort(v)[min(len(v), math.ceil((len(v) + 1) * 0.9)) - 1]) for L, v in sc.groupby(HV.lead)}
c = HT.lead.map(corr); cov = float(((HT.y >= HT.lo - c) & (HT.y <= HT.hi + c)).mean())
out = {"what": "NDVI v1 model chained on the v3 soil water model", "skill_by_lead_validation": rows, "useful_lead_quarters": useful,
       "correction_by_lead": corr, "coverage_90_2023_2025": cov}
(ART / "ndvi_chain.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
