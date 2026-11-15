"""The timeline of one 2 km cell: what was observed every month since 1998 (soil water in three ERA5-Land layers, CHIRPS
rain, NDVI by quarter), what the app's soil water model says for each of those months with the real weather, and the
projection that continues it. Observed and modelled values are always kept apart."""
from __future__ import annotations

import numpy as np

from . import state
from .common import EL_NINO_YEARS, NotFound
from .prediction import cell_info, find_cell, model_for, split_of

# ERA5-Land layers shown on the sides of the 3D field: (key in the cube, top cm, bottom cm). Layer 2 is display only.
LAYERS = [("sm_surface_m3m3", 0, 7), ("sm_layer2_m3m3", 7, 28), ("sm_root_m3m3", 28, 100)]


def _r(a, d: int = 4) -> list:
    return [None if not np.isfinite(x) else round(float(x), d) for x in np.asarray(a, float)]


def _layer(values: np.ndarray, months: np.ndarray) -> dict:
    """Observed series with the cell's own reference: the usual value of each calendar month and the 5-95 % range of
    its whole record (to colour a month from dry to wet for that place)."""
    with np.errstate(all="ignore"):
        usual = [float(np.nanmean(values[months == m])) if np.isfinite(values[months == m]).any() else np.nan for m in range(1, 13)]
        lo, hi = (np.nanpercentile(values, [5, 95]) if np.isfinite(values).any() else (np.nan, np.nan))
    return {"observed": _r(values), "usual_by_month": _r(usual), "p05": _r([lo])[0], "p95": _r([hi])[0]}


def timeline(loc) -> dict:
    from . import projections
    s = state.get(); cube = s.cube; i = find_cell(loc)
    months = cube.dates.month.to_numpy()
    root = cube.v["sm_root_m3m3"][i]
    if not np.isfinite(root).any():
        raise NotFound("this cell has no ERA5-Land soil water (a coastal cell outside the land mask)")
    layers = []
    for key, top, bottom in LAYERS:
        if key in cube.v:
            layers.append({"key": key, "top_cm": top, "bottom_cm": bottom, **_layer(cube.v[key][i], months),
                           "model_input": key != "sm_layer2_m3m3"})
    name = model_for("soil_water"); m = s.models[name]
    half = np.array([m["intervals"]["half_width_90_by_season"]["wet Jan-Apr" if mo <= 4 else "dry May-Dec"] for mo in months])
    pred = s.sm_pred[i]
    future = None
    try:
        sw, nd = projections.projection_at(loc, "soil_water", "base"), projections.projection_at(loc, "ndvi", "base")
        future = {"soil_water": {k: sw[k] for k in ("periods", "median", "low_90", "high_90", "usual", "members", "useful_lead")},
                  "ndvi": {k: nd[k] for k in ("periods", "median", "low_90", "high_90", "usual", "useful_lead")},
                  "what": "projection: the model run with the weather of each past year from the last observed month; not a forecast"}
    except NotFound:
        pass
    return {
        "location": cell_info(i),
        "months": [f"{d:%Y-%m}" for d in cube.dates],
        "split": [split_of(int(d.year)) for d in cube.dates],
        "layers": layers,
        "rain_mm": {"observed": _r(cube.v["rain_mm"][i], 1), "source": "CHIRPS (about 5.5 km)"},
        "model": {"name": name, "predicted": _r(pred), "low_90": _r(pred - half), "high_90": _r(pred + half),
                  "what": "the soil water model run on each month's real weather (one step); in training years its error is optimistic"},
        "ndvi": {"quarters": [str(q) for q in cube.quarters], "observed": _r(cube.ndvi[i], 3),
                 "note": "no NDVI image for some quarters (all of 2012; few cells in 2001-2013): gaps stay empty"},
        "el_nino_years": EL_NINO_YEARS,
        "future": future,
        "notes": ["Observed soil water is ERA5-Land (about 9 km), read on the 2 km cell: it describes rain-fed soil and knows nothing about irrigation.",
                  "Layer 2 (7-28 cm) is shown for context; no model uses it.",
                  "The projection is the model's answer with past weather, not an observation and not a forecast."],
    }
