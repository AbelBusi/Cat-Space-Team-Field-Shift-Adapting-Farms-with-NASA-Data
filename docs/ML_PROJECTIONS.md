# Field Shift ML · Projections and scenario simulator (model level)

Status (Nov 15, 2026): **rules written, hindcasts not run yet.** Model level only: no web, no backend. The standard
models in `ml/artifacts/final_model/` are used read-only and are not changed. Code: `ml/fs_ml/project.py`.

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
| `el_nino` | only the years whose Niño 1+2 index passed +1.0 °C in a month of Jan–Apr (the rainy season): 1998, 2016, 2017, 2023 (4 members, wide uncertainty) |
| `drought_feb_mar` | base, with no rain in Feb and Mar 2026 and the driest surface soil of those months |
| `rain_half` · `rain_double` | base, with rain × 0.5 or × 2 in every month |

Each row says whether its lead is within the useful lead. **2026 is not used to score anything here**; once its complete
data arrive, the Dec 2025 projection can be checked against it.
