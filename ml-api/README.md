# Field Shift ML API

A small FastAPI service that runs the **tested XGBoost models** of Field Shift. The web app's "What's ahead" screens
(projections, what-if scenarios and the simulator) get all their numbers from here. Nothing is trained or changed:
the models are read from `ml/artifacts/final_model/`, with the project's own feature code (`ml/fs_ml`).

**Read this first:** the models describe root-zone soil water (28–100 cm) and plant greenness (NDVI) of a 2 km cell
from weather inputs. They are prototypes with measured errors (`docs/ML_PHASE3_TESTING.md`, `docs/ML_PROJECTIONS.md`),
not crop-yield models and not certainties.

> **Expansion plan (Spanish):** [`roadmap/README.md`](roadmap/README.md) — what exists, what is proposed (predictions,
> simulations, territorial analysis, alerts, explanations, monitoring) and in which order.

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
  web/src/lib/projections.js          app/schemas/     Pydantic contracts (requests reject unknown fields)
  web/src/components/SimTuner.vue     app/services/    state (load once), prediction, projections, scenario_engine,
                                                       analysis, alerts, explanations, monitoring · app/routers/ HTTP routes
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
- `data/cube.npz` (11 MB, all 3,149 cells) is built from the team's raw data with `ml/scripts/export_api_cube.py`, so the API does not
  need the raw CSVs.

```
ml-api/
├── app/            main.py · config.py · ask.py · schemas/ · services/ · routers/
├── data/cube.npz   inputs per cell and month, all 3,149 grid cells (rebuild: ml/scripts/export_api_cube.py)
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
| GET | `/health` · `/models/health` | API status, model loaded and available, model hashes, load error if any |
| GET | `/model/info` · `/models/metrics` · `/models/validation` | Everything known about the models; historical metrics per period; acceptance criteria, projection skill and Phase 2 checks |
| POST | `/predictions` | One prediction from a full feature set (either model), with `prediction_id` and `reliability` |
| POST | `/predictions/soil-water` · `/predictions/ndvi` | The same, or for a cell and month/quarter of the data cube (features built as in training) |
| POST | `/predictions/complete` · `/predictions/batch` | 3 months of soil water + the quarter's NDVI, chained · up to 1,000 rows |
| GET | `/predictions/{cell_id}/history` · `/confidence` | Observed vs predicted 1998–2025 with the period of each row · historical error of the place (check S10 passed) |
| GET | `/projections` · `/projections/cell` | The whole grid for the web (integers × 1000) · one cell in real units |
| GET | `/timeline` | One cell through time for the field's log and the "Towards 2030" topic: 1998–2025 trends (Theil–Sen) of soil water, temperature, rain and NDVI with their extension to 2030 and check T (`docs/ML_TRENDS.md`); observed soil water in 3 ERA5-Land layers, CHIRPS rain and NDVI since 1998, the model's one-step months with their interval, El Niño years and the projection; observed, modelled and projected kept apart |
| POST | `/simulations/climate` · `/custom` · `/drought` · `/el-nino` · `/temperature` · `/rainfall` · `/recovery` | **One scenario engine**, run by the **v3** soil water model (ERA5-Land rain, monotone constraints; `docs/ML_V3_ERA5_RAIN.md`) with its own range corrections and checks; NDVI quarterly; `reliability_level` and `warnings` in every answer |
| GET | `/simulations/{simulation_id}/results` | A recent simulation by id (in memory) |
| GET | `/analysis/districts` · `/water-retention` · `/vegetation` · `/drought-risk` · `/anomalies` · `/hotspots` | Territorial analysis by district (median of 2 km cells, OSM boundaries) |
| GET | `/alerts/drought` · `/alerts/vegetation` | Cells below the band expected one step earlier (check S6 passed) |
| GET | `/explanations/{prediction_id}` · POST `/explanations` | TreeSHAP contributions (base + contributions = prediction) |
| POST | `/ask` | Sprout's open questions with the persona, the numbers on screen and, if sent, a simulation or prediction id |

Status of every feature and the results of its validation: [`roadmap/README.md`](roadmap/README.md) (Spanish) and
`docs/ML_API_VALIDATION.md`. Features whose check failed answer with `reliability_level: "experimental"`.

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

## Sprout's AI (`POST /ask`)

The web sends `{ question, lang, context }` (`web/src/lib/ask.js`, `VITE_ASK_URL`); `context` is what the user sees: place,
lat/lon, month, readings, topic, scenario. The API adds the tested model's 6-month soil water projection for that cell and
sends everything to a chat model with **`docs/SPROUT_PERSONA.md` as the system prompt** (personality, what Sprout may and
may not say, "use only the numbers in context"). Edit that file to change Sprout; no code change. The key, if any, stays
in the API's environment, never in the browser. If no model answers, `/ask` returns 503 and Sprout falls back to its few
local answers and says so.

One code path for any OpenAI-compatible endpoint (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`):

| Option | Cost | Notes |
|---|---|---|
| **Ollama** on your machine (default: `http://localhost:11434/v1`, `qwen2.5:3b`) | Free | Install Ollama, `ollama pull qwen2.5:3b` (~2 GB). Good for the local demo; answers in Spanish. Needs ~4 GB RAM; on a public server it needs a machine of that size, which hosting usually charges for |
| Groq (`https://api.groq.com/openai/v1`) | Free tier, rate-limited | Account and key; very fast open models (Llama, Qwen) |
| Google Gemini (`https://generativelanguage.googleapis.com/v1beta/openai`) | Free tier, rate-limited | Account and key; the free tier may use prompts to improve their products |
| OpenRouter (`https://openrouter.ai/api/v1`, models ending in `:free`) | Free models, rate-limited | Account and key |
| Paid APIs (Anthropic Claude, OpenAI…) | Per token | Best quality; Claude is reachable through its own API or OpenAI-compatible gateways |

## Sprout's voice (`/assistant/voice`, `/assistant/chat`)

Talk to Sprout with the microphone button in its panel (or type in the question box): it answers in **Spanish or
English** (the language you spoke in, detected by Whisper), with a **high, soft kitten voice**, and it can **move the
web**: fly to a province, district or town of Lambayeque, or open a screen or insight (the coming months, towards
2030, what if, where water holds, how sure Sprout is…). Code: `voice_assistant/` (backend) and `web/src/voice/` (web).

```
🎙️ browser (MediaRecorder) ──audio──► /assistant/voice ──► Whisper (speech → text, language detected)
                                                      ──► chat model with 6 tools (go_to_place, open_topic, projection,
                                                          timeline, what-if, district ranking), only read-only
                                                      ◄── { text, mood, actions, lang }
web: Sprout types the answer, speaks it (browser voice, pitch 1.75) and runs the actions (map, topic)
```

**A guide, not a chatbot:** Sprout reads the intent of what you say, not only commands, and takes you there in
the same turn. *"Soy de Pomalca y me preocupa el calor"* flies to Pomalca, opens what the satellites see, paints the map
with daytime heat and points at that card with a campfire ring; *"quiero ahorrar agua"* opens the priorities with water
at the top; *"¿y si llega El Niño?"* opens the what-if on the El Niño scenario. Tools for it: `go_to_place`,
`open_topic`, `set_view` (map signal, month, kind of year, scenario, priorities, mode, card to point at) and
`offer_choices` (2–3 next steps shown as buttons; per-screen defaults when the model offers none). The answer stays on
screen while the user is moved: the new screen's own lines wait a moment.

**Sprout's voice:** every line Sprout says (the guide, typed answers, spoken answers) is also spoken with
[Piper](https://github.com/rhasspy/piper) on the API (`POST /assistant/speak`, cached): a soft Spanish voice
(`es_MX-claude-high`) and a soft English one (`en_US-amy-medium`), pitched up by `TTS_PITCH` (1.35) with the pace kept
normal, so it sounds like a kitten. Get the voices once with `bash voice_assistant/download_voices.sh` (~126 MB, ignored
by git). Without them, or with `TTS_ENGINE=browser`, the browser's own voice speaks instead. The speaker button in
Sprout's panel turns the voice off.

**Quick local run** (one key for everything):

0. `pip install -r requirements.txt` and `bash voice_assistant/download_voices.sh` (once).
1. In `ml-api/.env`: `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_API_KEY=<your Groq key>`,
   `VOICE_LLM_MODEL=openai/gpt-oss-20b` (fast, with its own rate limit). Defaults: `STT_ENGINE=groq` (Whisper in the
   cloud with the same key) and `TTS_ENGINE=piper` (Sprout's voice on the API).
2. Start the API and the web as above; open http://localhost:5173 (the microphone needs `localhost` or https).
3. Tap 🎙️ in Sprout's panel, speak, tap again. Try: *"Llévame a Olmos"*, *"Take me to the Towards 2030 insight"*,
   *"¿Qué tan seguro estás?"*, *"¿Cómo estará el agua del suelo en marzo?"*. Check: `GET /api/v1/assistant/status?check=true`.

**Fully local (optional):** `STT_ENGINE=local` uses `faster-whisper` (model `small`, ~460 MB the first time) instead
of Whisper in the cloud.

**Free tier limits:** Groq's free models allow about 8,000 tokens per minute each; one question uses 2–4 thousand. The
assistant keeps prompts short, waits once when Groq asks for a short pause, and switches to `LLM_MODEL` when the voice
model is busy. Numbers come only from the tools; navigation never changes data.

## Known limitations

- Not a yield, crop or profit model; no irrigation in the data; one value per 2 km cell.
- Projections beat "a typical year" only for the first 6 months (soil water) on 2018–2022; in 2023–2025 (El Niño) only for 2.
- The 90 % ranges held the real value 81 % (soil water, v3) and 84 % (NDVI) of the time in 2023–2025: too narrow in extreme years.
- Soil water is the **v3** model everywhere (projections, cell predictions, simulations): temperature, droughts and
  rain passed their checks with it (recovery did not). It reads ERA5-Land's own rain, 3-6 times wetter than the real
  rain on this coast: an input, never shown as rain. v1 stays for feature-based requests with its 19 features and for
  the alerts (validated with v1). See `docs/ML_V3_ERA5_RAIN.md` §4.
- Temperature and humidity changes do not recompute evaporation or surface soil water.
- `summary` and `limitations` are in English; the web translates its own labels.
