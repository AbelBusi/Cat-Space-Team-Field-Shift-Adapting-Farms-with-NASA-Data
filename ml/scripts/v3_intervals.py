"""The 90 % interval of v3's one-step predictions, built exactly like v1's (ml/artifacts/final_model/sm_root_monthly/intervals.json):
split conformal on the absolute errors of Validation 2018-2022, one width per season, tested on 2023-2025.
The same code is run on v1 first, to show it reproduces v1's stored widths. Writes
ml/artifacts/v3_era5_rain/sm_root_monthly/intervals.json (the numbers notebook 08 reported as coverage_90_by_season).

    FIELDSHIFT_RAW_DIR=... ml/.venv/bin/python ml/scripts/v3_intervals.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from fs_ml import data as D, evaluate as E, era5 as R, features as F  # noqa: E402
from fs_ml.predict import load  # noqa: E402

warnings.filterwarnings("ignore", message="(All-NaN slice|Mean of empty slice)")
ART = ML / "artifacts" / "v3_era5_rain" / "sm_root_monthly"
V1 = load("sm_root_monthly")
prep = json.loads((ART / "preprocessing.json").read_text())
m3 = xgb.XGBRegressor(); m3.load_model(ART / "model.ubj")


def build(load_years, suffix, keep):
    monthly, _ = D.load_gee_monthly(load_years)
    pw = {p: D.load_power(f"power_{p}{suffix}", load_years)[0] for p in ["t2m", "rh2m", "ws2m", "allsky"]}
    merra = pw["t2m"].merge(pw["rh2m"], on=["power_lat", "power_lon", "date"]).merge(pw["ws2m"], on=["power_lat", "power_lon", "date"])
    gaez = {k: D.load_gaez(k)[0] for k in F.GAEZ_FEATURES}
    cells = F.static_cells(D.cells_from_ids(monthly.cell_id), gaez, merra[["power_lat", "power_lon"]].drop_duplicates().reset_index(drop=True),
                           pw["allsky"][["power_lat", "power_lon"]].drop_duplicates().reset_index(drop=True))
    mp = F.build_monthly_panel(monthly, cells, merra, pw["allsky"])
    return mp[mp.year.between(*keep)]


MP = pd.concat([build((1998, 2017), "", (1998, 2017)), build((2017, 2022), "_2018_2022", (2018, 2022)),
                build((2022, 2025), "_2023_2025", (2023, 2025))], ignore_index=True)
MP = R.add_to_monthly(MP, R.load_era5_rain(MP.cell_id.unique()))
T = V1["card"]["target"]["column"]
SEASON = {"wet": "wet Jan-Apr", "dry": "dry May-Dec"}


def intervals(model, feats):
    out = {}
    for split, (a, b) in (("cal", (2018, 2022)), ("test", (2023, 2025))):
        d = MP[MP.year.between(a, b) & MP[T].notna()]
        out[split] = (model.predict(d[feats]) - d[T].to_numpy(), np.where(d.month <= 4, "wet", "dry"))
    (rc, sc), (rt, st) = out["cal"], out["test"]
    half = {SEASON[s]: float(E.conformal_halfwidth(rc[sc == s], 0.9)) for s in ("wet", "dry")}
    width = np.vectorize(lambda s: half[SEASON[s]])(st)
    return half, float((np.abs(rt) <= width).mean())


h1, c1 = intervals(V1["model"], V1["features"])
print("v1 reproduced:", h1, round(c1, 4), "| stored:", V1["intervals"]["half_width_90_by_season"], V1["intervals"]["tested_coverage"]["by_season_90"])
h3, c3 = intervals(m3, prep["feature_names_in_order"])
print("v3:", h3, round(c3, 4))
out = {"method": "split conformal, absolute errors of Validation 2018-2022, one width per season (same code as v1)", "nominal": 0.9,
       "half_width_90_by_season": h3, "tested_coverage": {"by_season_90": c3, "years": [2023, 2025]},
       "reproduces_v1": {"half_width_90_by_season": h1, "by_season_90": c1},
       "warning": "Not a probability. Coverage measured on 2023-2025; it can be lower in extreme years."}
(ART / "intervals.json").write_text(json.dumps(out, indent=2))
