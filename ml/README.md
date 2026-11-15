# Field Shift ML (XGBoost)

| Phase | Years | Status | Report |
|---|---|---|---|
| 1 Training | 1998–2017 | done | [`docs/ML_PHASE1_TRAINING.md`](../docs/ML_PHASE1_TRAINING.md) (data irregularities, acceptance criteria) |
| 2 Validation | 2018–2022 | done, both models accepted | [`docs/ML_PHASE2_VALIDATION.md`](../docs/ML_PHASE2_VALIDATION.md) |
| 3 Testing | 2023–2026 | waiting for NASA POWER 2023–2026 | — |

| Path | What |
|---|---|
| `notebooks/01_phase1_training.ipynb` · `02_phase2_validation.ipynb` | One notebook per phase, saved with its outputs |
| `fs_ml/` | Shared code (loaders, features, metrics). Validation and Testing must reuse it unchanged |
| `artifacts/phase1_training/` | Models (`model.ubj`), feature order and ranges, metadata, baselines |
| `artifacts/phase2_validation/` | Metrics with 95 % CIs (overall, by year, province, season), interval checks, criteria, report |
| `data/processed/` | Training tables (Parquet), rebuilt by the notebook, not in git |

## Run it locally

```bash
python3 -m venv ml/.venv && ml/.venv/bin/pip install -r ml/requirements.txt
export FIELDSHIFT_RAW_DIR="/path/to/Datos para proyecto Nasa"   # the team's Drive folder
export FIELDSHIFT_MIDAGRI_DIR="/path/to/the/MIDAGRI/xlsx"        # optional, only for the inventory
cd ml/notebooks && ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace 01_phase1_training.ipynb
../.venv/bin/jupyter nbconvert --to notebook --execute --inplace 02_phase2_validation.ipynb
```

About 1 minute each on 16 cores. Each phase reads only its own years (Validation also reads 2017 as lag history); the
NASA POWER 2018–2022 files go in the same `Clima y metereología` folder.
