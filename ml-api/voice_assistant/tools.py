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


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("get_cell_projection",
         "Proyección de agua del suelo profunda (28-100 cm, 'Soil Memory') y NDVI (verdor) de una celda de 2 km para los próximos meses, con rangos y avisos. Úsala para preguntas sobre humedad del suelo, NDVI o datos de una celda.",
         {"type": "object", "properties": _CELL_PROPS}, _projection_cell),
    Tool("get_cell_history",
         "Serie histórica 1998-2025 de una celda: valor observado vs predicho por el modelo.",
         {"type": "object", "properties": {**_CELL_PROPS, "variable": {"type": "string", "enum": ["soil_water", "ndvi"]}}}, _cell_history),
    Tool("get_cell_confidence",
         "Qué tan bien ha funcionado históricamente el modelo en esa celda (error medido, no probabilidad de acierto).",
         {"type": "object", "properties": _CELL_PROPS}, _cell_confidence),
    Tool("get_cell_timeline",
         "Línea de tiempo de una celda: tendencias 1998-2025 de agua del suelo, temperatura, lluvia y NDVI, años de El Niño y proyección.",
         {"type": "object", "properties": _CELL_PROPS}, _timeline),
    Tool("run_simulation",
         "Simula un escenario 'qué pasaría si' en una celda y lo compara con un año normal. kind: drought (meses sin lluvia), el_nino, temperature, rainfall o custom. dry_months son meses de adelanto (1 = primer mes tras 'start'). t2m_delta en °C (-2 a 3), rain_factor multiplicador (0 a 3), rh_delta en puntos de humedad.",
         {"type": "object", "properties": {**_CELL_PROPS,
              "kind": {"type": "string", "enum": ["drought", "el_nino", "temperature", "rainfall", "custom"]},
              "start": {"type": "string", "description": "Mes de inicio AAAA-MM (por defecto 2025-12)."},
              "horizon": {"type": "integer", "description": "Meses a simular, 1 a 12 (por defecto 6)."},
              "dry_months": {"type": "array", "items": {"type": "integer"}},
              "t2m_delta": {"type": "number"}, "rain_factor": {"type": "number"}, "rh_delta": {"type": "number"}}},
         _simulation),
    Tool("compare_cells",
         "Compara las proyecciones de 2 o 3 celdas.",
         {"type": "object", "properties": {"cells": {"type": "array", "items": {"type": "object", "properties": _CELL_PROPS}}}, "required": ["cells"]},
         _compare_cells),
    Tool("get_district_analysis",
         "Análisis territorial por distrito (mediana de celdas). kind: districts, water-retention, vegetation, drought-risk, anomalies, hotspots.",
         {"type": "object", "properties": {"kind": {"type": "string", "enum": sorted(_ANALYSIS)},
                                            "scenario": {"type": "string"}, "province": {"type": "string"}}, "required": ["kind"]},
         _district_analysis),
    Tool("get_alerts",
         "Celdas con alerta: drought (agua del suelo bajo lo esperado) o vegetation (NDVI bajo lo esperado).",
         {"type": "object", "properties": {"kind": {"type": "string", "enum": ["drought", "vegetation"]}}, "required": ["kind"]},
         _alerts),
    Tool("get_model_info",
         "Métricas, validación y estado de los modelos. kind: info (todo sobre los modelos), metrics (error por periodo), validation (criterios y habilidad de proyección), health.",
         {"type": "object", "properties": {"kind": {"type": "string", "enum": sorted(_MODEL_PATHS)}}, "required": ["kind"]},
         _model_info),
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