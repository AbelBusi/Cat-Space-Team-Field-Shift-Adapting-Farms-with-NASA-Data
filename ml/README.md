# Field Shift ML (XGBoost)

| Phase | Years | Status | Report |
|---|---|---|---|
| 1 Training | 1998–2017 | done | [`docs/ML_PHASE1_TRAINING.md`](../docs/ML_PHASE1_TRAINING.md) (data irregularities, acceptance criteria) |
| 2 Validation | 2018–2022 | done, both models accepted | [`docs/ML_PHASE2_VALIDATION.md`](../docs/ML_PHASE2_VALIDATION.md) |
| 3 Testing | 2023–2025 (2026 incomplete, excluded) | done: accuracy passes, intervals overconfident | [`docs/ML_PHASE3_TESTING.md`](../docs/ML_PHASE3_TESTING.md) |
| v2 experiment | 2023–2025 (second look) | error ranges reach 90 % with CQR + monthly recalibration; not adopted yet | [`docs/ML_V2_INTERVALS_EXPERIMENT.md`](../docs/ML_V2_INTERVALS_EXPERIMENT.md) |
| v2 models + Niño 1+2 | train 1998–2017, validate 2018–2022 | soil water: no difference on Validation, waits for 2026; NDVI: rejected | [`docs/ML_V2_NINO_MODELS.md`](../docs/ML_V2_NINO_MODELS.md) |

**Standard models to use:** `artifacts/final_model/` through `fs_ml.predict` (`load`, `predict`).

| Path | What |
|---|---|
| `notebooks/01_phase1_training.ipynb` · `02_phase2_validation.ipynb` · `03_phase3_testing.ipynb` (experiments: `04_…`, `05_…`) | One notebook per phase, saved with its outputs |
| `fs_ml/` | Shared code (loaders, features, metrics). Validation and Testing must reuse it unchanged |
| `artifacts/phase1_training/` | Models (`model.ubj`), feature order and ranges, metadata, baselines |
| `artifacts/phase2_validation/` · `artifacts/phase3_testing/` | Metrics with 95 % CIs (overall, by year, province, season), interval checks, criteria, reports |
| `artifacts/final_model/` | The tested models with preprocessing, intervals (and their tested coverage) and model card |
| `data/processed/` | Training tables (Parquet), rebuilt by the notebook, not in git |

## Run it locally

```bash
python3 -m venv ml/.venv && ml/.venv/bin/pip install -r ml/requirements.txt
export FIELDSHIFT_RAW_DIR="/path/to/Datos para proyecto Nasa"   # the team's Drive folder
export FIELDSHIFT_MIDAGRI_DIR="/path/to/the/MIDAGRI/xlsx"        # optional, only for the inventory
cd ml/notebooks && ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace 01_phase1_training.ipynb
../.venv/bin/jupyter nbconvert --to notebook --execute --inplace 02_phase2_validation.ipynb
../.venv/bin/jupyter nbconvert --to notebook --execute --inplace 03_phase3_testing.ipynb
```

About 1 minute each on 16 cores. Each phase reads only its own years (Validation also reads 2017 as lag history); the
NASA POWER 2018–2022 and 2023–2025 files go in the same `Clima y metereología` folder.
