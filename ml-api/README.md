# Field Shift ML API

A small FastAPI service that runs the **tested XGBoost models** of Field Shift. The web app's "What's ahead" screens
(projections, what-if scenarios and the simulator) get all their numbers from here. Nothing is trained or changed:
the models are read from `ml/artifacts/final_model/`, with the project's own feature code (`ml/fs_ml`).

**Read this first:** the models describe root-zone soil water (28–100 cm) and plant greenness (NDVI) of a 2 km cell
from weather inputs. They are prototypes with measured errors (`docs/ML_PHASE3_TESTING.md`, `docs/ML_PROJECTIONS.md`),
not crop-yield models and not certainties.

## What the models predict

| Model | Target | Unit | Features (exact order in `GET /model/info`) |
|---|---|---|---|
| `sm_root_monthly` | ERA5-Land soil water layer 3, 28–100 cm, monthly mean | m³/m³ | 19: rain (month, 2 lags, 6-month sum), temperature, potential evaporation (+lag), last month's root and surface soil water, NASA POWER humidity, wind, sunlight, month (sin/cos), 5 FAO GAEZ soil classes |
| `ndvi_quarterly` | NDVI of the quarter (team's GEE composite) | index (−1…1) | 16: quarter weather sums/means, quarter soil water, quarter, NDVI 1 and 4 quarters before, 5 soil classes |

Artifact format: XGBoost `model.ubj` (binary JSON) + `preprocessing.json` (feature order and training ranges) +
`model_card.json` (metrics, limitations) + `intervals.json` (90 % interval and its tested coverage). No scaling and no
imputation were used in training (XGBoost handles missing values natively), so none is applied here.

## Architecture

```
web (Vue 3, Leaflet) ──HTTP/JSON──► ml-api (FastAPI)
  web/src/lib/mlApi.js                app/main.py      routes, CORS, gzip, error handlers
  web/src/lib/projections.js          app/schemas.py   Pydantic request/response models (extra fields rejected)
  web/src/components/SimTuner.vue     app/service.py   loads models once, predictions, projections, simulation
                                      app/config.py    settings from environment variables
                                          │
                                          ├── ml/fs_ml/            same feature and projection code as the notebooks
                                          ├── ml/artifacts/final_model/      the tested models (read-only)
                                          ├── ml/artifacts/projections/      hindcast results (useful lead, range corrections)
                                          └── ml-api/data/cube.npz           monthly inputs 1998–2025 per Lambayeque cell
```

- Models and data are loaded **once at startup**. The startup checks that every file exists, that each model's
  feature names equal its `preprocessing.json` order, and that each `model.ubj` matches the SHA-256 of its model card.
  A failure is logged with its cause and reported by `/health`; inference endpoints then answer 503.
- At startup the service also runs the projections of every Lambayeque cell (2.4 s): 12 months from December 2025 for a
  normal year, El Niño years and two dry months. A test checks they equal `ml/notebooks/06_projections.ipynb` cell by cell.
- `data/cube.npz` (6 MB) is built from the team's raw data with `ml/scripts/export_api_cube.py`, so the API does not
  need the raw CSVs.

```
ml-api/
├── app/            main.py · config.py · schemas.py · service.py
├── data/cube.npz   inputs per cell and month (rebuild: ml/scripts/export_api_cube.py)
├── tests/test_api.py
├── requirements.txt · .env.example · Dockerfile · Dockerfile.dockerignore
```

## Run it locally

Requirements: Python 3.14 (the version the models were trained with; `ml/requirements.txt` pins the same libraries).

```bash
cd ml-api
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional: the defaults already point to ../ml
uvicorn app.main:app --port 8000
```

Swagger docs: http://localhost:8000/docs. If you already have `ml/.venv`, it has every dependency:
`../ml/.venv/bin/python -m uvicorn app.main:app --port 8000`.

Tests (real models, real data):

```bash
python -m pytest -q
```

## Run it with Docker

Build from the **repository root** (the image copies `ml/fs_ml` and the models):

```bash
docker build -f ml-api/Dockerfile -t field-shift-ml-api .
docker run --rm -p 8000:8000 -e ML_API_CORS_ORIGINS=http://localhost:5173 field-shift-ml-api
```

The container listens on 0.0.0.0:8000. (The Docker build was written but not run on the development machine:
Docker was not running there. Run it once before relying on it.)

## Configuration (`.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `FS_MODEL_DIR` | `../ml/artifacts/final_model` | The tested models |
| `FS_ML_PACKAGE_DIR` | `../ml` | Folder that contains `fs_ml` |
| `FS_PROJECTION_CARD` | `../ml/artifacts/projections/projection_card.json` | Useful lead, range corrections (and `hindcast_skill_by_lead.csv` next to it) |
| `FS_CUBE_PATH` | `data/cube.npz` | Inputs per cell |
| `ML_API_CORS_ORIGINS` | `http://localhost:5173,http://localhost:5174` | Web origins allowed to call the API |
| `ML_API_LOG_LEVEL` | `info` | Logging level |

## Endpoints (`/api/v1`)

| Method | Path | What |
|---|---|---|
| GET | `/health` | API status, model loaded and available, service version, load error if any |
| GET | `/model/info` | For each model: algorithm, version, SHA-256, target with unit and meaning, features in order, hyperparameters, metrics with 95 % CIs, interval and its tested coverage, known limitations. Training date: `null` (not stored in the artifacts, said explicitly) |
| POST | `/predictions` | One prediction from a full feature set |
| GET | `/projections` | The whole grid (used by the web): 12 months of soil water and 4 quarters of NDVI per cell and scenario, integers × 1000 |
| GET | `/projections/cell?lat=&lon=&variable=&scenario=` | One cell's series in real units |
| POST | `/simulations/climate` | **The simulator**: a what-if for one cell compared with a normal year |

### POST /predictions

```json
{ "model": "sm_root_monthly",
  "features": { "rain_mm": 20, "rain_mm_lag1": 10, "rain_mm_lag2": 5, "rain_mm_sum6": 60, "t2m_c": 25, "pet_mm": 120,
                "pet_mm_lag1": 115, "sm_root_m3m3_lag1": 0.25, "sm_surface_m3m3_lag1": 0.22, "power_rh2m_pct": 75,
                "power_ws2m_ms": 3, "power_allsky_mj_m2_day": 20, "month_sin": 0.866, "month_cos": 0.5,
                "soil_nutrient_low_class": 2, "soil_oxygen_low_class": 3, "soil_lime_gypsum_class": 1,
                "soil_salinity_sodicity_class": 1, "soil_rooting_class": 2 } }
```

Every feature is required, unknown features are rejected, `null` is accepted only where training also had missing
values (e.g. `ndvi_lag1`), and physically impossible values (negative rain, humidity over 100 %) give 422. Unusual but
possible values are accepted and listed in `out_of_training_range` with a warning. The answer has `prediction`, the
target's unit and meaning, and `interval_90` (split conformal, one width per season) with its **real** coverage on
2023–2025 (0.82 for soil water), not a confidence percentage.

### POST /simulations/climate

The models need the weather of each month, so a "scenario" is not one feature vector: the service takes the cell's
observed state at `start`, runs 6–12 months with the weather of each past year (the baseline, a normal year), and again
with your changes. Only what you change is changed.

```json
{ "location": { "lat": -6.13, "lon": -79.73 },
  "start": "2025-12", "horizon": 6,
  "scenario": { "dry_months": [2, 3], "t2m_delta": 1, "rain_factor": 1, "rh_delta": 0, "months": null, "analog": "all" } }
```

Answer (abridged, real values for a cell in Motupe):

```json
{ "location": { "cell_id": "-4438,-342", "province": "Lambayeque", "district": "Motupe", "cell_size_km": 2 },
  "model": { "algorithm": "XGBoost", "name": "sm_root_monthly", "status": "available" },
  "periods": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
  "baseline": { "median": [...], "low_90": [...], "high_90": [...], "members": 28 },
  "scenario": { "median": [...], "low_90": [...], "high_90": [...], "members": 28 },
  "comparison": [ { "period": "2026-03", "absolute_difference": -0.0915, "percentage_change": -33.0,
                    "direction": "decreased", "within_model_error": false, "within_useful_lead": true } ],
  "modified_inputs": ["t2m_c +1 °C (all months; potential evaporation unchanged)", "no rain and driest surface soil in lead months [2, 3]"],
  "reliability": { "useful_lead_months": 6, "model_rmse_validation": 0.0125, "range_coverage_2023_2025": 0.80, "rain_only_change": false },
  "interpretation": { "summary": "With these changes the model's median root-zone soil water is higher than in a normal year in 2 of 6 months and lower in 4. The biggest difference is -0.0915 m3/m3 (-33 %) in 2026-03.",
                      "limitations": ["..."] } }
```

`summary` is written only from the computed numbers. `within_model_error` marks differences smaller than the model's
validation RMSE (0.0125 m³/m³): they cannot be told apart from noise. Errors: 400 unknown location or bad start month,
422 invalid input, 503 model not loaded, 500 inference error (details in the server log, not in the response).

## Web integration

- `web/src/lib/mlApi.js` is the only file with the URL, from `VITE_ML_API_URL` (`web/.env.development` for
  `npm run dev`, `web/.env.example` for other setups). It turns connection and HTTP errors into readable messages.
- `web/src/lib/projections.js` loads `GET /projections` once and feeds the five "What's ahead" topics (map colors,
  charts, district ranking). If the API is down, the topics say so instead of showing old numbers.
- `web/src/components/SimTuner.vue` (topic "What if…") holds the simulator buttons: months without rain, temperature
  −1…+2 °C, El Niño years, rain × 0.5…1.5. It sends `POST /simulations/climate` for the tapped cell, shows a loading
  state, aborts a request that a new one replaces, skips identical repeats, and shows the model's answer apart from
  the user's inputs.

## Known limitations

- Not a yield, crop or profit model; no irrigation in the data; one value per 2 km cell.
- Projections beat "a typical year" only for the first 6 months (soil water) on 2018–2022; in 2023–2025 (El Niño) only for 2.
- The 90 % ranges held the real value 80 % (soil water) and 84 % (NDVI) of the time in 2023–2025: too narrow in extreme years.
- **Rain-only changes failed their sanity checks**: the model leans on last month's soil water and barely reacts to rain
  alone, sometimes in the wrong direction. The API flags `rain_only_change` and puts the warning first.
- Temperature and humidity changes do not recompute evaporation or surface soil water.
- `summary` and `limitations` are in English; the web translates its own labels.
