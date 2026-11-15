"""Constants and small helpers shared by every service."""
from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict

log = logging.getLogger("ml-api")

TARGET_MEANING = {
    "sm_root_monthly": "Root-zone soil water, ERA5-Land layer 3 (28-100 cm), monthly mean, volumetric (m3 of water per m3 of soil)",
    "sm_root_monthly_v3": "Root-zone soil water, ERA5-Land layer 3 (28-100 cm), monthly mean, volumetric (m3 of water per m3 of soil); "
                          "v3 model, which also reads ERA5-Land's own rain (an input only, not the real rain)",
    "ndvi_quarterly": "Plant greenness (NDVI) of the quarter, from the team's satellite composite (-1 to 1)",
}
EL_NINO_YEARS = [1998, 2016, 2017, 2023, 2024]   # rule in docs/ML_PROJECTIONS.md: Niño 1+2 > +1.0 °C in Jan-Apr
GRID_STEP = 0.017966305682390427
K = 1000                                          # projections are sent as integers x 1000
# Physical limits: values outside are impossible (422), not just unusual (those only raise a warning)
PHYSICAL = [("era5_rain_mm_sum6", 0, 30000), ("era5_rain", 0, 10000), ("rain", 0, 3000), ("pet", 0, 1500), ("rh2m", 0, 100), ("ws2m", 0, 60), ("allsky", 0, 50), ("t2m", -40, 60),
            ("sm_", 0, 1), ("ndvi", -1, 1), ("month_", -1, 1), ("quarter", 1, 4)]

# Reliability of an answer, from best to worst (roadmap §9.3)
LEVELS = ["ok", "warning", "out_of_domain", "experimental"]


class ModelUnavailable(RuntimeError):
    pass


class NotFound(LookupError):
    """A cell, period or id that does not exist (HTTP 400)."""


class BadRequest(ValueError):
    """A request that cannot be answered as asked (HTTP 400). Other errors stay 500."""


def worst(*levels: str) -> str:
    return max(levels, key=LEVELS.index)


def warn(code: str, message: str, affected=()) -> dict:
    return {"code": code, "message": message, "affected": list(affected)}


def make_id(kind: str, payload: dict, models: dict) -> str:
    """Deterministic id: the same request on the same models always gets the same id (no database needed)."""
    blob = json.dumps({"kind": kind, "payload": payload, "models": models}, sort_keys=True, default=str)
    return f"{kind}_{hashlib.sha256(blob.encode()).hexdigest()[:24]}"


class LRU:
    """Small in-memory cache for recent results (ids → results). Nothing is stored on disk."""
    def __init__(self, size: int = 500):
        self.size, self.items = size, OrderedDict()

    def put(self, key, value):
        self.items[key] = value
        self.items.move_to_end(key)
        while len(self.items) > self.size:
            self.items.popitem(last=False)

    def get(self, key):
        if key in self.items:
            self.items.move_to_end(key)
            return self.items[key]
        return None
