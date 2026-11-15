# Field Shift ML · What the models can and cannot do

A plain guide for the team: what the two XGBoost (gradient boosting) models do, what we already built on them, what
else they could do with little work, and what they must not be used for. Numbers come from the phase reports
(`ML_PHASE1_TRAINING.md` … `ML_PROJECTIONS.md`); nothing here is new evidence.

## 1. What the models are

| | Soil water model | Greenness model |
|---|---|---|
| Predicts | Root-zone soil water (ERA5-Land layer 3, **28–100 cm**), monthly, m³/m³ | Vegetation greenness (**NDVI**), quarterly |
| From | That month's rain, temperature, evaporation, humidity, wind, sunlight; last month's soil water; soil classes | That quarter's weather and soil water; NDVI 1 and 4 quarters before; soil classes |
| Where | Any 2 km cell of the Lambayeque grid (3,149 cells; 1,950 inside the department) | Same grid (cells with NDVI) |
| How good (test 2023–2025) | RMSE 0.020 m³/m³, R² 0.96; halves the error of "same as last month" | RMSE 0.126, R² 0.53; 21 % better than "the usual NDVI here" |
| Honest range | 90 % interval held the truth 82 % of the time (too narrow in El Niño years); adaptive version reaches 90 % | 84 %; adaptive version 89 % |

In one sentence: **given the weather of a month (or a quarter) and the state of the soil, the models say how much water
the deep soil holds and how green the land is, for a 2 km cell, with a measured error.**

## 2. What we already do with them

| Capability | How | Where |
|---|---|---|
| **Estimate** soil water and NDVI for a cell and month, with an interval and its real coverage | `POST /api/v1/predictions`; `fs_ml.predict` | ml-api, notebooks |
| **Warn** when inputs are outside what the model has seen (trees cannot extrapolate) | training ranges p01–p99 and min–max per feature | every prediction |
| **Project** the next months (analog ensemble: the weather of each past year, month by month) | useful for **6 months** (soil water) and 4 quarters (NDVI) on 2018–2022; 2 months in El Niño years | `GET /api/v1/projections`, "What's ahead" |
| **What-if** scenarios: El Niño years, two months without rain, your own changes (dry months, ±°C, El Niño years) | same engine, weather changed on purpose | "What if…", simulator, `POST /api/v1/simulations/climate` |
| **Rank places**: districts and towns where the deep soil should keep the most water in the dry months | median of the cells' projections | "Where water holds" |
| **Explain** with Sprout: the AI reads the on-screen numbers and the cell's projections and interprets them, without inventing | `POST /api/v1/ask` | Sprout's chat |
| **Check itself** on past years (hindcasts) and say how far ahead it is useful | block bootstrap CIs per lead | "How sure is Sprout", paper |

## 3. What they could do next (little work, no new data)

Each would need its own rules written before it is checked, like every step so far.

1. **Explain one prediction**: XGBoost gives each feature's contribution (TreeSHAP, `pred_contribs=True`; already used in
   Phase 1). An endpoint could say "this month is wetter mostly because last month was wet and it rained 40 mm".
   It describes the model, not causes in the field.
2. **Anomaly map / irrigation signal**: where the observed NDVI is much greener than the model expects from the weather,
   something the weather does not explain is going on — most likely irrigation or new cropland (Olmos). A map of those
   residuals could show where irrigation is expanding. Needs a check against known irrigated areas.
3. **Fill NDVI gaps**: 18 quarters of 1998–2017 have no image; the model can estimate them, marked as estimates.
4. **Early warning per month**: when the newest month of data arrives, compare it with the projection and flag cells
   that are drier than the 90 % range ("this is unusual for here").
5. **Monthly recalibration in the API**: serve the adaptive ranges (CQR + monthly recalibration, 90 % coverage) instead
   of the fixed ones.
6. **Temperature sensitivity**: how the model's soil water changes with ±1–2 °C, labelled as the model's direct response
   (evaporation is not recomputed).
7. **Same tools for any place in the grid**: the 1,176 cells outside Lambayeque (towards Piura, Cajamarca, La Libertad)
   already have predictions, but they were not validated separately; validate them before showing them.

## 4. What needs new data

| To be able to… | We need | Status |
|---|---|---|
| React to rain alone (today a rain-only change moves soil water less than the model error) | ERA5-Land monthly precipitation and soil layer 2; monotone constraints on rain | request documented in `ML_V2_NINO_MODELS.md` §2 |
| Know El Niño from the start, not only through analog years | Niño 1+2 index as a feature | v2 trained; decided on 2026 |
| Say which **crop** fits, or expected **yield** or **profit** | yields by district and campaign, crop calendars, prices | not available (MIDAGRI files are truncated, no yields) |
| Separate irrigated from rain-fed fields | irrigated area per year (MapBiomas, Olmos, Tinajones) | pending |
| Trust the 2026 El Niño | complete 2026 data | pending: the decisive test |
| Work outside the north coast (highlands, other regions) | the same GEE export for those regions and a new validation | not started |

## 5. What they must not be used for

- **Not a yield, crop, profit or price model.** They predict soil water and greenness only.
- **Not a weather forecast.** Projections use past years' weather; they do not know next year's rain.
- **Not your exact field.** One value per 2 km cell; ERA5-Land soil and climate are ~9 km underneath; no irrigation.
- **Not causes.** A what-if shows how the model responds, not what would happen in the field.
- **Not rain-only scenarios** (they failed their checks) and not inputs far outside 1998–2017 without the warning.
- **Not certainties.** Always show the range with its measured coverage, and remember it is too narrow in extreme years.

## 6. Where to start

- Python: `from fs_ml.predict import load, predict` (tables built with `fs_ml.features`); projections with `fs_ml.project`.
- API: `ml-api/README.md` (endpoints, examples, Docker).
- Evidence: `docs/ML_PHASE1_TRAINING.md`, `ML_PHASE2_VALIDATION.md`, `ML_PHASE3_TESTING.md`,
  `ML_V2_INTERVALS_EXPERIMENT.md`, `ML_V2_NINO_MODELS.md`, `ML_PROJECTIONS.md`, and the paper `paper/field_shift_ml.tex`.
