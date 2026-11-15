# Field Shift ML · Projections and scenario simulator (model level)

Status (Nov 15, 2026): **hindcasts run; outputs for 2026 exported.** The standard models in `ml/artifacts/final_model/`
are used read-only and are not changed. Code: `ml/fs_ml/project.py`; notebook: `ml/notebooks/06_projections.ipynb`;
outputs: `ml/artifacts/projections/`; web file: `web/public/data/projections.json` (`ml/scripts/export_web_projections.py`).
The rules in §3 were committed before the hindcasts (commit `abb3b51`).

## 1. Why a new layer is needed

The tested models describe a month from **that month's** weather (their model card says "not for forecasts of real
future dates"). The team wants the cat to also answer "what comes next?" and "what if two months without rain?". Both
need the weather of months that have not happened. This layer supplies it in two honest ways:

| Mode | Question | Weather of the coming months | Validated? |
|---|---|---|---|
| **Projection** | "How will my soil water and greenness likely go in the next months?" | Each past year's weather for the same calendar months (one member per year), starting from today's observed state of the cell | **Yes**, by hindcasts (§3): past starts projected and compared with what really happened |
| **Scenario (what-if)** | "What if there are two months without rain?", "What if it is an El Niño year?" | The projection weather changed on purpose (no rain, half or double rain, only El Niño years) | **No** (they are hypotheses). Only sanity checks (§3) |

Method: analog ensemble, known in hydrology as Ensemble Streamflow Prediction (Day, 1985). The soil water model runs
month by month, each predicted value feeding the next month; the NDVI model runs on the simulated quarters.

## 2. What it cannot do

- **No crop yield, crop quality or export volume.** We have no yield data (the MIDAGRI tables received are truncated and
  have no yields or coordinates). Predicting yields would mean inventing a target. The projections give the conditions
  a crop depends on (root-zone soil water, greenness), not the harvest.
- **No weather forecast.** The coming months' rain is not predicted; the ensemble shows the range of what past years
  brought. Real seasonal forecasts (SENAMHI, ENFEN, NOAA) can be fed in later as a scenario.
- Not for irrigated fields (ERA5-Land has no irrigation) and not a measurement of one field: one 2 km cell.

## 3. Rules written before the hindcasts (do not edit after seeing results)

**Models.** The standard v1 models, unchanged. Same tables and code as every phase (`fs_ml`).

**Hindcasts on Validation (they decide what the app may show).**
- Soil water: one start at the end of every month from Dec 2017 to Nov 2022; leads 1–12 months; only targets inside
  2018–2022. NDVI: one start at the end of every quarter from Dec 2017 to Sep 2022; leads 1–4 quarters; targets inside 2018–2022.
- Analog years: 1998–2017 (20 members), never a year being scored.
- Score per lead: RMSE of the member median, and RMSE skill against the two simple rules: **climatology** (mean of that
  cell and month or quarter, 1998–2017) and **persistence** (the value at the start held constant). 95 % CI by the same
  0.2° block bootstrap as Phases 2–3.
- **Useful lead** = the longest lead L such that at every lead up to L the lower 95 % CI of the skill against the better
  of the two rules is above 0. Beyond it the app must say "a typical year" (climatology), not a projection.
- **Range.** The 5–95 % band of the members only holds the weather uncertainty. A correction per lead (conformalized
  band, Romano et al., 2019) is calibrated on these Validation hindcasts for 90 %.

**Second look on 2023–2025 (report only, already seen by Phase 3).** Starts Dec 2022 – Nov 2025 (soil water) and
Dec 2022 – Sep 2025 (NDVI), the same analog years and corrections. Reported: skill per lead and the coverage of the 90 %
range (target 87–93 %, as rule F).

**Scenario sanity checks (report).** From every Validation start: (a) two months without rain must not raise soil water
in more than 1 % of the cells; (b) double rain must not lower it in more than 1 % of the cells. A failure is reported
as a limit of the scenario, not fixed by hand.

**Outputs for the app (no web yet).** Start Dec 2025 (the last complete month), soil water for Jan–Dec 2026 and NDVI for
Q1–Q4 2026, per 2 km cell and per province, analog years 1998–2025. Scenarios:

| Scenario | Change |
|---|---|
| `base` | all analog years 1998–2025 |
| `el_nino` | only the years whose Niño 1+2 index passed +1.0 °C in a month of Jan–Apr (the rainy season): 1998, 2016, 2017, 2023, 2024 (5 members, wide uncertainty). *Correction before any result was seen: the first version of this line listed 4 years by hand and missed 2024 (Jan +1.14 °C, the tail of the 2023 event); the rule is what counts.* |
| `drought_feb_mar` | base, with no rain in Feb and Mar 2026 and the driest surface soil of those months |
| `rain_half` · `rain_double` | base, with rain × 0.5 or × 2 in every month |

Each row says whether its lead is within the useful lead. **2026 is not used to score anything here**; once its complete
data arrive, the Dec 2025 projection can be checked against it.

## 4. Results

Two fixes were made after the first run failed and before any result was read: the El Niño year list (see the table
above; the rule gives 5 years) and the NDVI climatology baseline, which was NaN for cells with no NDVI in a quarter and
now falls back to the regional mean of that quarter, as in Phases 2–3. A consistency check passed: with the real weather,
lead 1 equals the tested model's own prediction exactly (max difference 0.0).

### 4.1 Skill by lead (Validation hindcasts 2018–2022 decide; 2023–2025 report only)

| Lead | Soil water skill [95 % CI] 2018–2022 | 2023–2025 | | NDVI lead | NDVI skill 2018–2022 | 2023–2025 |
|---|---|---|---|---|---|---|
| 1 month | 0.39 [0.34, 0.43] vs persistence | 0.35 | | 1 quarter | 0.17 [0.09, 0.25] | 0.19 |
| 2 | 0.18 [0.14, 0.23] vs climatology | 0.09 | | 2 | 0.11 [0.03, 0.19] | 0.12 |
| 3 | 0.08 [0.05, 0.13] | 0.01 | | 3 | 0.11 [0.03, 0.18] | 0.13 |
| 6 | 0.04 [0.005, 0.09] | −0.09 | | 4 | 0.10 [0.07, 0.13] vs persistence | 0.12 |
| 12 | 0.01 [−0.03, 0.06] | −0.13 | | | | |

- **Useful lead (rule of §3): soil water 6 months, NDVI 4 quarters.** Most of the gain is in the first 2–3 months; after
  that the projection is close to "a typical year".
- On 2023–2025 (coastal El Niño and drift), soil water stays better than climatology only for 2 months, and is worse
  from month 4. This is the same weakness as in Phase 3: the rule decides on Validation, but the app must say plainly
  that extreme years are less predictable.

### 4.2 The 90 % range

Correction per lead calibrated on the Validation hindcasts. Coverage on 2023–2025: **soil water 80 % [79, 82], NDVI
84 % [83, 86]**, both below the 87–93 % target. The ranges are too narrow in an El Niño period, as in Phase 3.

### 4.3 Scenario sanity checks: failed

| Check | Result |
|---|---|
| (a) two months without rain must not raise soil water in > 1 % of cells | **fails**: 25 % of cells on average (max 42 %) |
| (b) double rain must not lower soil water in > 1 % of cells | **fails**: 38 % on average (max 80 %) |

- "Two months without rain" (no rain and the driest surface soil) does dry the soil clearly on average: −0.04 m³/m³ for
  January starts, −0.02 to −0.01 for March to May starts. The cells that "rise" are small tree-step changes.
- **Rain alone barely moves the model.** Doubling the rain changes soil water by +0.003 m³/m³ at most on average (less
  than the model error, 0.0125), and in the dry months in the wrong direction about as often as in the right one. The
  model leans on last month's soil water (68 % of its gain) and on the surface soil (24 %); the four rain inputs add up to 2.4 %.
- Consequence, applied in the app: only **normal year**, **El Niño years** and **two months without rain** are offered.
  "Half / double the rain" stay in the artifacts but are not shown. Any "rain ×" button of a simulator would show noise
  as if it were an answer; the API (`ml-api/`) returns this warning with every rain-only change.

### 4.4 What this means for the MVP

The projection layer is usable for a prototype: a 1–3 month outlook of root-zone soil water with an honest range, an
El Niño what-if, and a drought what-if. It is not a crop or yield forecast, and its ranges are too narrow in El Niño
years. The decisive check is the complete 2026 data: the Dec 2025 projection can be compared with what happened.
