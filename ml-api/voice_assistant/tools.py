"""Herramientas del asistente.

Lista blanca de operaciones de SOLO LECTURA sobre los endpoints existentes de la API
(se llaman dentro del mismo proceso, sin red). El LLM no puede ejecutar nada más:
solo elige un nombre de esta lista y sus argumentos se validan aquí.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import quote

import httpx

from .config import settings

logger = logging.getLogger("voice_assistant.tools")


class ToolError(Exception):
    """Error legible para el LLM (se le devuelve como resultado de la herramienta)."""


class FieldShiftClient:
    """Llama a los endpoints existentes de ml-api sin salir del proceso."""

    def __init__(self, app: Any):
        self._app = app

    async def call(self, method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> Any:
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(transport=transport, base_url="http://field-shift.internal", timeout=60.0) as http:
            resp = await http.request(method, f"{settings.api_prefix}{path}", params=params, json=body)
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text[:500]}
        if resp.status_code >= 400:
            raise ToolError(f"La API respondió {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:400]}")
        return data


# ---------------------------------------------------------------- utilidades
def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _clamp(value: Any, low: float, high: float, default: float) -> float:
    number = _to_float(value)
    if number is None:
        return default
    return max(low, min(high, number))


def _find_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if obj.get(key) not in (None, ""):
            return obj[key]
        for value in obj.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj[:5]:
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def _cell(args: dict, ctx: dict) -> dict:
    """Celda pedida por el LLM; si no dio ninguna, la celda seleccionada en pantalla."""
    explicit = args.get("cell_id") or (args.get("lat") is not None and args.get("lon") is not None)
    src = args if explicit else ctx
    out: dict[str, Any] = {}
    lat, lon = _to_float(src.get("lat")), _to_float(src.get("lon"))
    if lat is not None and lon is not None:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ToolError("Coordenadas fuera de rango.")
        out.update(lat=lat, lon=lon)
    if src.get("cell_id"):
        out["cell_id"] = str(src["cell_id"])
    if not out:
        raise ToolError("No hay una celda seleccionada. Pide al usuario que toque una celda en el mapa.")
    return out


def _select_action(cell: dict, data: Any = None) -> dict:
    action = {"type": "select_cell", **cell}
    if "cell_id" not in action and data is not None:
        found = _find_key(data, "cell_id")
        if found:
            action["cell_id"] = str(found)
    return action


async def _resolve_cell_id(client: FieldShiftClient, args: dict, ctx: dict) -> tuple[str, dict]:
    cell = _cell(args, ctx)
    if cell.get("cell_id"):
        return cell["cell_id"], cell
    data = await client.call("GET", "/projections/cell", params=cell)
    found = _find_key(data, "cell_id")
    if not found:
        raise ToolError("No pude identificar la celda en esas coordenadas.")
    return str(found), cell


def compact(obj: Any, max_list: int = 24, digits: int = 4) -> Any:
    """Reduce listas largas y decimales para no desbordar el contexto del LLM."""
    if isinstance(obj, float):
        return round(obj, digits)
    if isinstance(obj, dict):
        return {k: compact(v, max_list, digits) for k, v in obj.items()}
    if isinstance(obj, list):
        if len(obj) > max_list:
            head, tail = obj[:6], obj[-(max_list - 6):]
            omitted = f"... {len(obj) - max_list} elementos omitidos ..."
            return [compact(x, max_list, digits) for x in head] + [omitted] + [compact(x, max_list, digits) for x in tail]
        return [compact(x, max_list, digits) for x in obj]
    return obj


def serialize(data: Any) -> str:
    text = ""
    for limit in (24, 12, 6):
        text = json.dumps(compact(data, limit), ensure_ascii=False)
        if len(text) <= settings.tool_result_max_chars:
            return text
    return text[: settings.tool_result_max_chars] + " ...[recortado]"


# ---------------------------------------------------------------- herramientas
Handler = Callable[[FieldShiftClient, dict, dict], Awaitable[tuple[Any, list[dict]]]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Handler

    def spec(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


_CELL_PROPS = {
    "lat": {"type": "number", "description": "Latitud de la celda. Omitir para usar la celda seleccionada en pantalla."},
    "lon": {"type": "number", "description": "Longitud de la celda. Omitir para usar la celda seleccionada en pantalla."},
    "cell_id": {"type": "string", "description": "Identificador de celda (opcional)."},
}


async def _projection_cell(client, args, ctx):
    cell = _cell(args, ctx)
    data = await client.call("GET", "/projections/cell", params=cell)
    return data, [_select_action(cell, data)]


async def _cell_history(client, args, ctx):
    cell_id, cell = await _resolve_cell_id(client, args, ctx)
    params = {}
    if args.get("variable") in ("soil_water", "ndvi"):
        params["variable"] = args["variable"]
    data = await client.call("GET", f"/predictions/{quote(cell_id, safe=',-')}/history", params=params)
    return data, [_select_action({**cell, "cell_id": cell_id})]


async def _cell_confidence(client, args, ctx):
    cell_id, cell = await _resolve_cell_id(client, args, ctx)
    data = await client.call("GET", f"/predictions/{quote(cell_id, safe=',-')}/confidence")
    return data, [_select_action({**cell, "cell_id": cell_id})]


async def _timeline(client, args, ctx):
    cell = _cell(args, ctx)
    data = await client.call("GET", "/timeline", params=cell)
    return data, [_select_action(cell, data)]


async def _simulation(client, args, ctx):
    cell = _cell(args, ctx)
    location = {k: cell[k] for k in ("lat", "lon") if k in cell} or {"cell_id": cell["cell_id"]}
    horizon = int(_clamp(args.get("horizon"), 1, 12, 6))
    start = str(args.get("start") or "2025-12")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", start):
        raise ToolError("El mes de inicio debe tener formato AAAA-MM.")
    kind = str(args.get("kind") or "custom")

    scenario: dict[str, Any] = {}
    dry = args.get("dry_months") or []
    if isinstance(dry, list) and dry:
        scenario["dry_months"] = sorted({int(m) for m in dry if _to_float(m) is not None and 1 <= int(m) <= horizon})
    if kind == "drought" and not scenario.get("dry_months"):
        raise ToolError("Para una sequía indica qué meses de adelanto (1 = primer mes) no llueve.")
    if args.get("t2m_delta") is not None:
        scenario["t2m_delta"] = _clamp(args["t2m_delta"], -2, 3, 0)
    if args.get("rain_factor") is not None:
        scenario["rain_factor"] = _clamp(args["rain_factor"], 0, 3, 1)
    if args.get("rh_delta") is not None:
        scenario["rh_delta"] = _clamp(args["rh_delta"], -20, 20, 0)
    if kind == "el_nino":
        scenario["analog"] = "el_nino"

    body = {"location": location, "start": start, "horizon": horizon, "scenario": scenario}
    data = await client.call("POST", "/simulations/climate", body=body)
    return data, [{"type": "run_simulation", **body}]


async def _compare_cells(client, args, ctx):
    raw = args.get("cells") if isinstance(args.get("cells"), list) else []
    cells = []
    for item in raw[:3]:
        if isinstance(item, dict):
            cells.append(_cell(item, {}))
    if len(cells) < 2 and ctx.get("cell_id") or (len(cells) < 2 and ctx.get("lat") is not None):
        cells.insert(0, _cell({}, ctx))
    if len(cells) < 2:
        raise ToolError("Necesito al menos dos celdas (coordenadas) para comparar.")
    results = await asyncio.gather(*[client.call("GET", "/projections/cell", params=c) for c in cells])
    data = {"cells": [{"cell": c, "projection": r} for c, r in zip(cells, results)]}
    return data, [{"type": "compare_cells", "cells": cells}]


_ANALYSIS = {"districts", "water-retention", "vegetation", "drought-risk", "anomalies", "hotspots"}


async def _district_analysis(client, args, ctx):
    kind = args.get("kind")
    if kind not in _ANALYSIS:
        raise ToolError(f"Tipo de análisis no válido. Opciones: {sorted(_ANALYSIS)}")
    params = {k: str(args[k]) for k in ("scenario", "province") if args.get(k)}
    data = await client.call("GET", f"/analysis/{kind}", params=params)
    return data, [{"type": "show_analysis", "kind": kind, **params}]


async def _alerts(client, args, ctx):
    kind = args.get("kind")
    if kind not in ("drought", "vegetation"):
        raise ToolError("Tipo de alerta no válido: drought o vegetation.")
    data = await client.call("GET", f"/alerts/{kind}")
    return data, [{"type": "show_alerts", "kind": kind}]


_MODEL_PATHS = {"info": "/model/info", "metrics": "/models/metrics", "validation": "/models/validation", "health": "/models/health"}


async def _model_info(client, args, ctx):
    kind = args.get("kind")
    if kind not in _MODEL_PATHS:
        raise ToolError(f"Tipo no válido. Opciones: {sorted(_MODEL_PATHS)}")
    return await client.call("GET", _MODEL_PATHS[kind]), []



# ---------------------------------------------------------------- navegación por la web
# Lugares de Lambayeque (OpenStreetMap, los mismos archivos que usa la web) y los temas de cada recorrido.
_PLACES: dict | None = None


def _fold(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(text).lower()) if unicodedata.category(c) != "Mn").strip()


def _places() -> dict:
    global _PLACES
    if _PLACES is None:
        admin = json.loads((settings.places_dir / "lambayeque_admin.json").read_text(encoding="utf-8"))
        towns = json.loads((settings.places_dir / "lambayeque_places.json").read_text(encoding="utf-8"))
        provinces = {_fold(p["name"]): p["name"] for p in admin["provinces"]}
        districts = {_fold(d["name"]): {"name": d["name"], "province": p["name"], "lat": d["center"][1], "lon": d["center"][0]}
                     for p in admin["provinces"] for d in p["districts"]}
        _PLACES = {"provinces": provinces, "districts": districts,
                   "towns": {_fold(t[0]): {"name": t[0], "lat": t[1], "lon": t[2]} for t in towns}}
    return _PLACES


def _best(query: str, names: dict):
    import difflib
    if query in names:
        return names[query]
    close = difflib.get_close_matches(query, list(names), n=1, cutoff=0.82)
    return names[close[0]] if close else None


async def _go_to_place(client, args, ctx):
    raw = str(args.get("name") or "").strip()
    if not raw:
        raise ToolError("Falta el nombre del lugar.")
    q, P = _fold(raw), _places()
    for prefix in ("provincia de ", "province of ", "distrito de ", "district of ", "el ", "la "):
        if q.startswith(prefix):
            q = q[len(prefix):]
    kind = str(args.get("kind") or "").lower()
    if kind != "town" and kind != "district" and (prov := _best(q, P["provinces"])):
        if kind == "province" or not _best(q, P["districts"]) or q in P["provinces"]:
            return ({"found": "province", "name": prov, "note": "La web abre el mapa de la provincia con sus distritos."},
                    [{"type": "go_to_place", "kind": "province", "name": prov}])
    if kind != "town" and (d := _best(q, P["districts"])):
        return ({"found": "district", **d}, [{"type": "go_to_place", "kind": "district", "name": d["name"], "province": d["province"]}])
    if (t := _best(q, P["towns"])):
        return ({"found": "town", **t}, [{"type": "go_to_place", "kind": "town", "name": t["name"], "lat": t["lat"], "lon": t["lon"]}])
    raise ToolError(f"No encontré '{raw}' en Lambayeque. Solo conozco sus 3 provincias, 38 distritos y 650 pueblos.")


TOPICS = {
    # recorrido "Hoy": lo que ven los satélites
    "signals": ("today", "Lo que ven los satélites: calor, lluvia, humedad del suelo, verdor y agua subterránea del lugar."),
    "ground": ("today", "Tu suelo y el clima reciente (últimos 30 días)."),
    "years": ("today", "Tu lugar año por año: franjas de calor desde 1981, el año más lluvioso y el más seco."),
    "prio": ("today", "Qué es lo más importante para ti (ahorrar agua, ganar más, cuidar el suelo...)."),
    "rots": ("today", "Cómo podría verse tu año: rotaciones de cultivos de ejemplo."),
    "detail": ("today", "Comparar una rotación con la actual."),
    "report": ("today", "Tu reporte para imprimir."),
    # recorrido "Lo que viene": los modelos
    "outlook": ("ahead", "Los próximos meses: agua del suelo profundo proyectada para 2026."),
    "trends": ("ahead", "Hacia 2030: tendencias 1998-2025 de temperatura, lluvia, agua del suelo y verdor."),
    "whatif": ("ahead", "Qué pasaría si: El Niño, meses sin lluvia, la mitad o el doble de lluvia."),
    "green": ("ahead", "El verdor (NDVI) que viene por trimestre."),
    "spots": ("ahead", "Dónde aguanta el agua: ranking de distritos y pueblos en la época seca."),
    "trust": ("ahead", "Qué tan seguro está Sprout: acierto de los modelos y sus límites."),
}


def _facts(topic: str) -> dict:
    """The key numbers of a screen, straight from what the API computed at startup (never typed by hand)."""
    try:
        from app.services import state
        s = state.get()
    except Exception:  # noqa: BLE001
        return {}
    meta = s.bundle["meta"]
    if topic == "trust":
        up = meta.get("model_upgrade") or {}
        return {"useful_months_soil_water": meta["useful_lead"]["soil_water_months"], "useful_quarters_ndvi": meta["useful_lead"]["ndvi_quarters"],
                "share_of_real_values_inside_the_90pct_range_2023_2025": meta["coverage_2023_2025"],
                "soil_water_error_m3m3_v1_to_v3": up.get("rmse_validation_2018_2022"), "march_2023_error_v1_to_v3": up.get("rmse_march_2023"),
                "scenario_checks_passed": up.get("scenario_checks_passed")}
    if topic == "trends":
        out = {}
        for name, tr in s.bundle.get("trends", {}).items():
            if isinstance(tr, dict) and "clear" in tr:
                flags = [(c, v) for c, v in zip(tr["clear"], tr["per_decade"]) if c is not None]
                out[name] = {"share_clear_up": round(sum(1 for c, v in flags if c and v > 0) / max(1, len(flags)), 2),
                             "share_clear_down": round(sum(1 for c, v in flags if c and v < 0) / max(1, len(flags)), 2)}
        return {"lambayeque_1998_2025": out, "note": "a straight trend did not predict 2018-2025 better than no change: 2030 is a direction"}
    if topic == "outlook":
        return {"starts": meta["start"], "useful_months": meta["useful_lead"]["soil_water_months"]}
    if topic == "spots":
        rows = sorted((r for r in s.bundle["district_summary"] if r["scenario"] == "base" and r["cells"] >= 3), key=lambda r: -r["dry_season_soil_water"])
        return {"most_water_in_dry_season": [r["district"] for r in rows[:3]], "least": [r["district"] for r in rows[-2:]]}
    return {}


async def _open_topic(client, args, ctx):
    topic = str(args.get("topic") or "")
    if topic not in TOPICS:
        raise ToolError(f"Tema no válido. Opciones: {sorted(TOPICS)}")
    track, what = TOPICS[topic]
    return {"opened": topic, "shows": what, **_facts(topic)}, [{"type": "open_topic", "topic": topic, "track": track}]

_CELL = {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}},
         "description": "Omit lat/lon to use the square on screen."}

TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("go_to_place", "Move the map to a province, district or town of Lambayeque.",
         {"type": "object", "properties": {"name": {"type": "string"}, "kind": {"type": "string", "enum": ["province", "district", "town"]}},
          "required": ["name"]}, _go_to_place),
    Tool("open_topic", "Open a screen or insight of the web; returns its key facts.",
         {"type": "object", "properties": {"topic": {"type": "string", "enum": list(TOPICS)}}, "required": ["topic"]}, _open_topic),
    Tool("get_cell_projection", "Deep soil water and NDVI of a 2 km square for the coming months, with ranges.", _CELL, _projection_cell),
    Tool("get_cell_timeline", "A square since 1998: trends of soil water, temperature, rain and NDVI; El Niño years.", _CELL, _timeline),
    Tool("run_simulation", "What if for a square vs a normal year. kind: drought (dry_months = months ahead, 1 = first), el_nino, temperature (t2m_delta °C), rainfall (rain_factor 0-3).",
         {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"},
              "kind": {"type": "string", "enum": ["drought", "el_nino", "temperature", "rainfall", "custom"]},
              "dry_months": {"type": "array", "items": {"type": "integer"}}, "t2m_delta": {"type": "number"}, "rain_factor": {"type": "number"}}},
         _simulation),
    Tool("get_district_analysis", "Districts ranked: water-retention, vegetation, drought-risk.",
         {"type": "object", "properties": {"kind": {"type": "string", "enum": ["water-retention", "vegetation", "drought-risk"]},
                                            "province": {"type": "string"}}, "required": ["kind"]}, _district_analysis),
]}


async def execute_tool(name: str, args: dict, client: FieldShiftClient, ctx: dict) -> tuple[str, list[dict], bool]:
    tool = TOOLS.get(name)
    if tool is None:
        return json.dumps({"error": f"Herramienta desconocida: {name}"}), [], False
    try:
        data, actions = await tool.handler(client, args, ctx)
    except ToolError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False), [], False
    except Exception:  # noqa: BLE001  (detalle solo en el log, como en el resto de la API)
        logger.exception("Falló la herramienta %s", name)
        return json.dumps({"error": "Falló la consulta interna a Field Shift."}), [], False
    return serialize(data), actions, True