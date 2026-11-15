"""Niño 1+2 sea surface temperature anomaly (coastal El Niño signal), used only by the v2 models.

Source file: NOAA PSL monthly time series `nino12.long.anom.csv` (https://psl.noaa.gov/data/timeseries/month/), one
value per month, the same for every grid cell. Added after Phases 1-3; the v1 code paths do not import this module.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import data as D

NINO_FILE = "Clima y metereología/nino12.long.anom.csv"
MONTHLY_FEATURES = ["nino12_anom", "nino12_anom_lag1", "nino12_anom_3m"]
QUARTERLY_FEATURES = ["q_nino12_anom", "q_nino12_anom_lag1"]


def load_nino12(path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Monthly anomaly in °C. The header says the missing value is -99.99, but the last months of the file use -9999:
    both (and anything below -90) are treated as missing."""
    path = Path(path) if path else D.raw_dir() / NINO_FILE
    header = path.open(encoding="utf-8").readline().strip()
    df = pd.read_csv(path, skiprows=1, header=None, names=["date", "nino12_anom"], skipinitialspace=True)
    df["date"] = pd.to_datetime(df["date"].str.strip())
    raw_missing = int((df.nino12_anom < -90).sum())
    df.loc[df.nino12_anom < -90, "nino12_anom"] = np.nan
    df = df.dropna().sort_values("date").reset_index(drop=True)
    gaps = int((df.date.diff().dt.days.dropna() > 31).sum())
    info = {"file": path.name, "sha256": D.sha256(path), "header": header, "first": str(df.date.min().date()),
            "last": str(df.date.max().date()), "months": len(df), "missing_coded_values": raw_missing, "gaps": gaps}
    return df, info


def monthly_index(nino: pd.DataFrame) -> pd.DataFrame:
    """Same-month value, previous month and the 3-month mean ending this month (like ENFEN's ICEN running mean)."""
    s = nino.set_index("date").nino12_anom.asfreq("MS")
    return pd.DataFrame({"nino12_anom": s, "nino12_anom_lag1": s.shift(1),
                         "nino12_anom_3m": s.rolling(3).mean()}).reset_index()


def quarterly_index(nino: pd.DataFrame) -> pd.DataFrame:
    s = nino.set_index("date").nino12_anom.asfreq("MS")
    q = s.groupby([s.index.year, s.index.quarter]).agg(["mean", "size"])
    q = q[q["size"] == 3]["mean"].rename("q_nino12_anom")
    q.index.names = ["year", "quarter"]
    q = q.reset_index()
    q["q_nino12_anom_lag1"] = q.q_nino12_anom.shift(1)
    return q


def add_to_monthly(panel: pd.DataFrame, nino: pd.DataFrame) -> pd.DataFrame:
    return panel.merge(monthly_index(nino), on="date", how="left", validate="many_to_one")


def add_to_quarterly(panel: pd.DataFrame, nino: pd.DataFrame) -> pd.DataFrame:
    return panel.merge(quarterly_index(nino), on=["year", "quarter"], how="left", validate="many_to_one")
