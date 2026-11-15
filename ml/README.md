# Field Shift ML (XGBoost)

Phase 1 (Training, 1998–2017) is done. Results, irregularities in the data and the acceptance criteria for the next phases:
[`docs/ML_PHASE1_TRAINING.md`](../docs/ML_PHASE1_TRAINING.md).

| Path | What |
|---|---|
| `notebooks/01_phase1_training.ipynb` | Phase 1 notebook, saved with its outputs |
| `fs_ml/` | Shared code (loaders, features, metrics). Validation and Testing must reuse it unchanged |
| `artifacts/phase1_training/` | Models (`model.ubj`), feature order and ranges, metadata, baselines |
| `data/processed/` | Training tables (Parquet), rebuilt by the notebook, not in git |

## Run it locally

```bash
python3 -m venv ml/.venv && ml/.venv/bin/pip install -r ml/requirements.txt
export FIELDSHIFT_RAW_DIR="/path/to/Datos para proyecto Nasa"   # the team's Drive folder
export FIELDSHIFT_MIDAGRI_DIR="/path/to/the/MIDAGRI/xlsx"        # optional, only for the inventory
cd ml/notebooks && ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace 01_phase1_training.ipynb
```

About 1 minute on 16 cores. Phase 1 only reads 1998–2017 rows; the 2018–2026 rows of the same files stay untouched.
