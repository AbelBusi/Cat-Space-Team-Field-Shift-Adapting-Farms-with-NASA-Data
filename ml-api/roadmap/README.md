# Field Shift ML API — Especificación técnica y hoja de ruta de expansión

> Documento de diseño del backend (`ml-api/`). Describe **lo que existe hoy**, **lo que se propone** y **en qué orden**
> construirlo usando los dos modelos XGBoost ya entrenados y probados, sin reentrenar nada salvo donde se justifique.
> Las cifras de rendimiento vienen de los reportes del repositorio (`docs/ML_*.md`); los JSON marcados como
> *ilustrativos* no son resultados del modelo.

**Leyenda de estado** usada en todo el documento:

| Etiqueta | Significado |
|---|---|
| ✅ **Implementado** | Existe en `ml-api/` hoy, con pruebas (`ml-api/tests/test_api.py`) |
| 🟡 **Parcial** | La lógica existe en `fs_ml` o en los notebooks, pero no está expuesta en la API, o lo está en otra forma |
| 🔵 **Propuesto (Fase 1)** | Se puede construir con los modelos y datos actuales, reutilizando código existente |
| 🟣 **Propuesto (Fase 2)** | Requiere una validación nueva (hindcast, prueba de rangos o validación geográfica) antes de mostrarse como confiable |
| 🔴 **Propuesto (Fase 3)** | Requiere datos o modelos nuevos |


## Estado de implementación (actualizado el 15 de noviembre de 2026)

Fases 1 y 2 implementadas en `ml-api/app/` (servicios en `app/services/`, rutas en `app/routers/`, contratos en
`app/schemas/`). 13 pruebas de integración con los modelos y datos reales (`ml-api/tests/test_api.py`). Las pruebas
de la Fase 2 se corrieron con reglas escritas antes (`docs/ML_API_VALIDATION.md`, notebook 07).

| Grupo | Endpoints | Nivel que devuelven |
|---|---|---|
| Predicciones | `POST /predictions`, `/predictions/soil-water`, `/ndvi`, `/complete`, `/batch`; `GET /predictions/{cell_id}/history` | `ok` / `warning` / `out_of_domain` según las entradas |
| Confianza por lugar | `GET /predictions/{cell_id}/confidence` | `warning` (S10 **pasó**: ρ = 0.65) |
| Simulaciones | `POST /simulations/climate`, `/custom`, `/drought`, `/el-nino`, `/temperature`, `/rainfall`, `/recovery`; `GET /simulations/{id}/results` | un solo motor; `experimental` si cambian temperatura (S1 falló), sequía (S2 falló), lluvia (S3 falló), recuperación (S4 falló) o evaporación/viento/radiación (sin validación); NDVI incluido cuando el inicio es fin de trimestre |
| Análisis territorial | `GET /analysis/districts`, `/water-retention`, `/vegetation`, `/drought-risk`, `/anomalies`, `/hotspots` | rankings `warning`; riesgo de sequía `experimental` (S5 falló: sobreconfiado); anomalías de NDVI y focos `experimental` (S7 no comprobable) |
| Alertas | `GET /alerts/drought`, `/alerts/vegetation` | `warning` (S6 **pasó**: 4.7 % y 3.7 % marcadas, 5 % esperado) |
| Explicabilidad | `GET /explanations/{prediction_id}`, `POST /explanations` | TreeSHAP exacto; la suma da la predicción |
| Monitoreo | `GET /health`, `/models/health`, `/model/info`, `/models/metrics`, `/models/validation` | — |
| Celdas fuera de Lambayeque | todos los endpoints por celda | servidas con aviso (S8 **pasó**) |
| Sprout | `POST /ask` | ahora recibe también el resultado completo de una simulación (`simulation_id`) o la explicación de una predicción (`prediction_id`) |

**Fase 3 — iniciada (15 nov 2026):** llegó la lluvia de ERA5-Land y se entrenó el **modelo v3** de agua del suelo con
restricciones monótonas (`docs/ML_V3_ERA5_RAIN.md`, reglas escritas antes). Pasó R1 y R2 (claramente mejor que v1:
*skill* +0.21 [0.17, 0.25]; RMSE de validación 0.0099) y con él **pasan S1 temperatura, S2 sequías y S3 lluvia**; S4
recuperación sigue fallando. **Desde ahora las simulaciones corren con v3** (sus propias correcciones de rango y
pruebas); las predicciones de un paso y las proyecciones de la web siguen con v1 hasta que el equipo decida.

**Resto de la Fase 3 — pendiente:** necesita datos que no tenemos (precipitación ERA5-Land, superficies regadas, rendimientos,
calendarios, precios, 2026 completo). Lo que las pruebas de la Fase 2 enseñan es concreto: el modelo actual responde poco
y a veces al revés cuando se cambia una sola entrada, porque depende del agua del suelo del mes anterior; los
simuladores necesitan un modelo v3 que reaccione a la lluvia y la temperatura (sección 6.4).

---

## Índice

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Estado actual de los modelos](#2-estado-actual-de-los-modelos)
3. [Arquitectura existente](#3-arquitectura-existente)
4. [Arquitectura propuesta](#4-arquitectura-propuesta)
5. [Catálogo de endpoints](#5-catálogo-de-endpoints)
6. [Simulaciones](#6-simulaciones)
7. [Motor de escenarios](#7-motor-de-escenarios)
8. [Contratos JSON (Pydantic)](#8-contratos-json-pydantic)
9. [Validaciones, métricas y confiabilidad](#9-validaciones-métricas-y-confiabilidad)
10. [Integración con el frontend](#10-integración-con-el-frontend)
11. [Integración con Sprout](#11-integración-con-sprout)
12. [Estructura del proyecto](#12-estructura-del-proyecto)
13. [Priorización por fases](#13-priorización-por-fases)
14. [Limitaciones científicas](#14-limitaciones-científicas)
15. [Hoja de ruta de implementación](#15-hoja-de-ruta-de-implementación)

---

## 1. Descripción del proyecto

Field Shift traduce datos de la NASA y de Copernicus a lenguaje simple para agricultores de Lambayeque (Perú). El
backend de ML (`ml-api/`, FastAPI) sirve dos modelos XGBoost que estiman, para cada celda de 2 km:

- cuánta **agua guarda el suelo profundo** (28–100 cm) cada mes, y
- qué tan **verde** está la vegetación (NDVI) cada trimestre.

Sobre ellos ya funcionan proyecciones a futuro, escenarios "qué pasaría si" y un asistente (Sprout). Este documento
define cómo ampliar la API para convertirla en una plataforma de **predicción, simulación y análisis territorial**
sin perder el principio que guió todo el proyecto: **cada número viene con su error medido y sus límites**.

---

## 2. Estado actual de los modelos

### 2.1 Modelos

| | Modelo de agua del suelo (`sm_root_monthly`) | Modelo de verdor (`ndvi_quarterly`) |
|---|---|---|
| Variable objetivo | ERA5-Land, capa 3 (28–100 cm), media mensual, m³/m³ | NDVI del trimestre (compuesto satelital del equipo en GEE) |
| Frecuencia | Mensual | Trimestral |
| Características | 19: lluvia del mes, 2 rezagos y suma de 6 meses (CHIRPS); temperatura y evaporación potencial (+ rezago) (ERA5-Land); agua del suelo profundo y superficial del mes anterior; humedad relativa, viento y radiación (NASA POWER); mes (seno y coseno); 5 clases de suelo (FAO GAEZ) | 16: lluvia del trimestre y del anterior; temperatura, evaporación, agua del suelo, humedad, viento y radiación del trimestre; trimestre; NDVI 1 y 4 trimestres antes; 5 clases de suelo |
| Árboles | 1,122 | 89 |
| Entrenamiento | 1998–2017 (validación 2018–2022, prueba única 2023–2025) | igual |
| Prueba 2023–2025 | RMSE 0.0198 m³/m³ [0.0185, 0.0211], R² 0.962, MAE 0.0113, sesgo −0.003; *skill* frente a persistencia 0.46 [0.44, 0.49] | RMSE 0.126 [0.121, 0.131], R² 0.53, *skill* frente a climatología 0.21 [0.14, 0.29] |
| Intervalo del 90 % | Conformal por temporada; cobertura real en 2023–2025: **82 %** | **84 %** |
| Artefactos | `ml/artifacts/final_model/<modelo>/`: `model.ubj`, `preprocessing.json` (orden de características y rangos p01/p99/min/max), `intervals.json` (anchos y cobertura probada), `model_card.json` | igual |

*Skill* = 1 − RMSE_modelo / RMSE_regla_simple. Corchetes = IC 95 % por bootstrap de bloques espaciales.

### 2.2 Capas construidas sobre los modelos

| Capa | Estado | Resultado medido |
|---|---|---|
| Proyecciones por conjunto de años análogos (clima de cada año 1998–2025, mes a mes, recursivo) | ✅ `GET /projections`, `fs_ml/project.py` | Útil (supera a "un año típico" con IC > 0) hasta **6 meses** (agua del suelo) y **4 trimestres** (NDVI) en 2018–2022. En la segunda mirada a 2023–2025 (con El Niño costero) solo 2 meses. Cobertura del rango 90 % en 2023–2025: 80 % / 84 % |
| Escenarios: año normal, años de El Niño, dos meses sin lluvia | ✅ calculados al iniciar la API | Sequía: seca el suelo en promedio (−0.04 m³/m³ en inicios de enero), **pero su prueba de cordura falló** (25 % de celdas subieron un poco). **Solo lluvia (×0.5, ×2): también falló** (respuesta menor que el error del modelo, a veces en sentido contrario) |
| Simulador por celda (meses secos, ±°C, ±HR, lluvia ×, años El Niño) | ✅ `POST /simulations/climate` (solo agua del suelo) | Marca diferencias menores al RMSE como ruido; advierte cambios solo de lluvia |
| Rangos adaptativos (CQR + recalibración mensual) | 🟡 experimento en `ml/artifacts/v2_intervals_experiment/` | Cobertura 90 % / 89 % en 2023–2025 (segunda mirada); no está en la API |
| Modelos v2 con índice Niño 1+2 | 🟡 `ml/artifacts/v2_nino_models/`, `fs_ml/enso.py` | Agua del suelo: sin diferencia en validación (se decide con 2026). NDVI: rechazado |
| Contribuciones por característica (TreeSHAP) | 🟡 usadas en la fase 1 (`pred_contribs`) | No expuestas en la API |
| Asistente Sprout con IA | ✅ `POST /ask` | Usa los números en pantalla y las 3 proyecciones de la celda; prohibido estimar cifras |

---

## 3. Arquitectura existente

### 3.1 Componentes (verificado en el repositorio)

```
ml-api/
├── app/
│   ├── main.py       rutas /api/v1, CORS, GZip, manejadores de error (422, 503, 500)
│   ├── config.py     variables de entorno + carga de ml-api/.env (ignorado por git)
│   ├── schemas.py    Pydantic: PredictionRequest/Response, Location, Scenario, SimulationRequest/Response,
│   │                 Series, PeriodComparison, AskRequest/Response (extra="forbid")
│   ├── service.py    carga de modelos (una vez), predicción, simulación, proyecciones de toda la grilla
│   └── ask.py        Sprout: cualquier endpoint compatible con OpenAI (Groq en el evento, Ollama por defecto)
├── data/cube.npz     entradas mensuales 1998-01 → 2025-12 de 1,973 celdas de Lambayeque (6 MB),
│                     con provincia y distrito (límites de OpenStreetMap), NDVI trimestral y clases de suelo
├── tests/test_api.py 6 pruebas de integración con los modelos y datos reales
├── Dockerfile        python:3.14-slim, contexto = raíz del repo (aún no probado: Docker no corría en la PC de desarrollo)
└── requirements.txt  fastapi 0.163, uvicorn 0.54, pydantic 2.14, xgboost 3.4.1, numpy 2.5.4, pandas 3.1.1, scipy 1.18.1
```

La API **no duplica** el código de ML: importa el paquete del proyecto `ml/fs_ml`
(`predict.load`, `project.analog_weather`, `project_sm`, `project_ndvi`, `scenario_*`, `out_of_training_range`).
Así, las características se construyen igual que en el entrenamiento.

### 3.2 Flujo de carga

1. Verifica que existan los modelos, `fs_ml`, `cube.npz` y la tarjeta de proyecciones.
2. `fs_ml.predict.load()` carga cada `model.ubj` y **comprueba que el orden de características del modelo coincide con
   `preprocessing.json`**; luego el SHA-256 del archivo se compara con el de `model_card.json`.
3. Construye el `Cube` en memoria y calcula una sola vez las proyecciones de toda la grilla (≈2.4 s).
4. Si algo falla, guarda la causa: `/health` la reporta y los endpoints de inferencia responden 503.

### 3.3 Endpoints actuales

| Método | Ruta | Estado |
|---|---|---|
| GET | `/api/v1/health` | ✅ |
| GET | `/api/v1/model/info` | ✅ |
| POST | `/api/v1/predictions` (modelo + 19/16 características exactas) | ✅ |
| GET | `/api/v1/projections` (grilla completa, enteros × 1000) | ✅ |
| GET | `/api/v1/projections/cell` | ✅ |
| POST | `/api/v1/simulations/climate` | ✅ (solo agua del suelo) |
| POST | `/api/v1/ask` | ✅ |

### 3.4 Integración web actual

`web/src/lib/mlApi.js` (única URL, `VITE_ML_API_URL`), `web/src/lib/projections.js` (consume `/projections`),
`web/src/components/SimTuner.vue` (consume `/simulations/climate`), `web/src/lib/ask.js` (consume `/ask`).

---

## 4. Arquitectura propuesta

Principios:

- **Un solo motor** de escenarios (sección 7) para todas las simulaciones; cada endpoint específico solo traduce su
  configuración a una `ScenarioConfiguration`.
- **`fs_ml` sigue siendo la capa de ML.** No se crea `app/ml/` con copias: lo nuevo que sea ML (por ejemplo, ajustes
  de evaporación o viento) se agrega a `ml/fs_ml/project.py`, que usan también los notebooks.
- **Resultados deterministas e identificables.** `simulation_id` y `prediction_id` = hash SHA-256 de la solicitud
  canónica + hash de los modelos. `GET .../{id}` recalcula (o lee de una caché LRU en memoria): no hace falta base de
  datos ni guardar datos de usuarios.
- **Confiabilidad explícita** en cada respuesta (sección 9.3): `ok`, `warning`, `out_of_domain` o `experimental`.
- **Compatibilidad:** las rutas actuales se mantienen; las nuevas se agregan.

```
            ┌──────────── routers (FastAPI) ─────────────┐
 web ──►    predictions · simulations · analysis · alerts · explanations · models · ask
            └───────────────┬─────────────────────────────┘
                            ▼
              servicios: prediction · scenario_engine · analysis · alerts · explanations · monitoring
                            ▼
              fs_ml (features, predict, project, enso)  +  estado cargado (modelos, cube, tarjetas)
```

---

## 5. Catálogo de endpoints

Convenciones comunes:

- Prefijo `/api/v1`. Errores: **400** solicitud imposible (celda fuera de la grilla, mes de inicio sin datos),
  **422** datos inválidos (Pydantic: nulos no permitidos, tipos, `NaN`/`inf`, rangos físicos, campos desconocidos),
  **503** modelo o IA no disponible, **500** error de inferencia (detalle solo en el log).
- `location` = `{ "cell_id": "x,y" }` o `{ "lat": …, "lon": … }` dentro de la grilla de Lambayeque (2 km).
- Las cifras de los ejemplos de salida son **ilustrativas** salvo que se indique lo contrario.

### A. Predicciones

#### A1. `POST /predictions/soil-water` — 🔵 Fase 1
- **Descripción:** predicción mensual del agua del suelo profundo para un vector de características completo, o para
  una celda y un mes del cubo (las características se arman con los datos observados).
- **Entrada:** `{ "features": {…19…} }` **o** `{ "location": {…}, "month": "2024-03" }`.
- **Usa:** `service.predict_one("sm_root_monthly", …)` (✅ ya existe vía `POST /predictions`); variante por celda: filas
  del `Cube` con la misma construcción que `fs_ml.project._sm_features` con clima real.
- **Validaciones:** las de `validate_features` (nombres exactos, nulos solo donde hubo faltantes en entrenamiento,
  rangos físicos); mes entre 1998-05 y 2025-12.
- **Salida:**
  ```json
  { "prediction_id": "sha256:…", "model": "sm_root_monthly", "target": { "column": "sm_root_m3m3", "unit": "m3/m3" },
    "prediction": 0.214, "interval_90": { "low": 0.184, "high": 0.244, "method": "split conformal (wet Jan-Apr)", "tested_coverage": 0.82 },
    "observed": 0.209, "reliability": "ok", "warnings": [] }
  ```
  *(ilustrativo; `observed` solo si el mes existe en el cubo)*
- **Límites:** describe el mes con su propio clima; no es pronóstico.

#### A2. `POST /predictions/ndvi` — 🔵 Fase 1
Igual que A1 con `ndvi_quarterly` y `{ "quarter": "2024Q2" }`. Validación extra: NDVI rezagado puede ser nulo (hubo
trimestres sin imagen); el resto no.

#### A3. `POST /predictions/complete` — 🔵 Fase 1
- **Descripción:** para una celda y un trimestre, devuelve los 3 meses de agua del suelo y el NDVI del trimestre,
  encadenando la media trimestral de agua del suelo como entrada del NDVI (igual que `fs_ml.project.project_ndvi`).
- **Salida:** `{ "soil_water": [{month, prediction, interval_90}, …×3], "ndvi": {…}, "reliability": "…" }`.

#### A4. `POST /predictions/batch` — 🔵 Fase 1
- **Entrada:** `{ "model": "...", "items": [ { "features": {…} } … ] }`, máximo 1,000 filas.
- **Usa:** una sola llamada vectorizada a `model.predict(DataFrame)`.
- **Validación:** la de A1 por fila; respuesta con errores por índice (`207`-like dentro de 200: `{ "results": [...], "errors": [{ "index": 3, "detail": "…" }] }`).

#### A5. `GET /predictions/{cell_id}/history` — 🔵 Fase 1
- **Descripción:** serie 1998–2025 de la celda: valor observado (ERA5-Land / NDVI) y predicción del modelo a un paso
  (con clima real), marcando el periodo de cada fila (`training`, `validation`, `testing`).
- **Parámetros:** `variable=soil_water|ndvi`, `from`, `to`.
- **Límite:** en años de entrenamiento el error es optimista (el modelo los vio); el campo `split` lo deja claro.

#### A6. `GET /predictions/{cell_id}/confidence` — 🟣 Fase 2
- **Descripción:** desempeño **histórico** del modelo en esa celda: RMSE y sesgo en validación 2018–2022 y prueba
  2023–2025, y cobertura de su intervalo en esos años. No es la probabilidad de acierto de una predicción individual.
- **Por qué Fase 2:** 60 meses correlacionados por celda dan intervalos amplios; hay que definir el mínimo de datos y
  agrupar por píxel ERA5-Land (~20 celdas comparten el mismo valor).

### B. Simulaciones

Todas usan el **mismo motor** (sección 7). La respuesta común es `SimulationResponse` (sección 8).

| Método | Ruta | Estado | Traducción a `ScenarioConfiguration` |
|---|---|---|---|
| POST | `/simulations/climate` | ✅ existe (agua del suelo); 🔵 añadir NDVI | configuración completa actual |
| POST | `/simulations/drought` | 🔵 Fase 1 | `dry_months=[k…k+n−1]`, opcional `rain_factor` en otros meses, `t2m_delta` |
| POST | `/simulations/el-nino` | 🔵 Fase 1 | `analog="el_nino"` (+ cambios opcionales) |
| POST | `/simulations/temperature` | 🔵 Fase 1 (etiqueta *experimental*) | `t2m_delta ∈ {−2,−1,+1,+2,+3}` |
| POST | `/simulations/rainfall` | 🟣 Fase 2 (*experimental* hasta pasar pruebas) | `rain_factor`, `dry_months` |
| POST | `/simulations/custom` | 🟣 Fase 2 | todas las variables (sección 6.5) |
| POST | `/simulations/recovery` | 🟣 Fase 2 | sequía previa + clima posterior (sección 6.6) |
| GET | `/simulations/{simulation_id}/results` | 🔵 Fase 1 | recalcula o lee de caché por hash |

Validaciones comunes: `horizon` 1–12; meses de cambio dentro del horizonte; deltas dentro de rangos (sección 9.2);
`start` con 5 meses previos de lluvia observada; celda con agua del suelo observada en `start`.
Errores: 400 (celda o inicio), 422 (configuración), 503.

### C. Análisis territorial

Base de datos geográfica **real** del cubo: cada celda tiene provincia y distrito asignados con los límites de
OpenStreetMap que usa la web (`web/src/data/lambayeque_admin.json`, © OpenStreetMap, ODbL), 38 distritos con celdas.
Agregación por distrito = **mediana de las celdas** (no media) y número de celdas, para que un distrito pequeño se lea
con su tamaño. Requisito: no reportar distritos con menos de 3 celdas sin advertencia; no inventar valores para
distritos sin celdas.

| Método | Ruta | Estado | Descripción |
|---|---|---|---|
| GET | `/analysis/districts` | 🔵 Fase 1 | lista de distritos con celdas, provincia, n.º de celdas, valores observados recientes y proyectados |
| GET | `/analysis/water-retention` | 🟡→🔵 | ranking de agua del suelo en meses secos (jul–nov) por escenario; ya calculado en `/projections` (`district_summary`) |
| GET | `/analysis/vegetation` | 🟡→🔵 | ranking de NDVI del segundo semestre por escenario; igual que arriba |
| GET | `/analysis/drought-risk` | 🟣 Fase 2 | fracción de miembros del conjunto bajo el percentil 20 de la celda (no es probabilidad oficial; requiere evaluar su calibración con hindcasts) |
| GET | `/analysis/anomalies` | 🟣 Fase 2 | residuo observado − predicho por celda y periodo (2018–2025), estandarizado por el error del modelo |
| GET | `/analysis/hotspots` | 🟣 Fase 2 | agrupaciones de celdas vecinas con anomalías persistentes (p. ej., ≥ 3 trimestres) |

Ejemplo `GET /analysis/water-retention?scenario=base&province=Lambayeque` *(ilustrativo)*:
```json
{ "scenario": "base", "period": "2026-07..2026-11", "unit": "m3/m3", "aggregation": "median of 2 km cells",
  "districts": [ { "district": "San José", "province": "Lambayeque", "cells": 12, "value": 0.311, "rank": 1 } ],
  "warnings": ["Projection beyond the 6-month useful lead: closer to a typical year"] }
```

### D. Alertas

| Método | Ruta | Estado | Descripción |
|---|---|---|---|
| GET | `/alerts/drought` | 🟣 Fase 2 | celdas cuyo valor observado del último mes cae **bajo el rango del 90 %** proyectado para ese mes |
| GET | `/alerts/vegetation` | 🟣 Fase 2 | celdas cuyo NDVI observado cae bajo el rango esperado |

Requisito operativo: hoy el cubo termina en 2025-12 y se actualiza a mano (exportaciones GEE + NASA POWER). Sin una
ingesta mensual no hay alertas "en vivo"; la primera versión puede evaluar meses pasados. Las alertas usan la
cobertura real (80 %) para decir cuántas falsas alarmas esperar.

### E. Explicabilidad

#### `GET /explanations/{prediction_id}` — 🔵 Fase 1
- **Usa:** `booster.predict(DMatrix, pred_contribs=True)` (TreeSHAP exacto de XGBoost) sobre la fila exacta.
- **Salida** *(ilustrativa)*:
  ```json
  { "prediction_id": "sha256:…", "model": "sm_root_monthly", "base_value": 0.162, "prediction": 0.214,
    "contributions": [ { "feature": "sm_root_m3m3_lag1", "value": 0.198, "contribution": 0.041 },
                       { "feature": "sm_surface_m3m3_lag1", "value": 0.230, "contribution": 0.012 } ],
    "note": "Contributions describe how the model reached its number, not causes in the field." }
  ```
- **Límites:** las contribuciones suman la predicción (propiedad de TreeSHAP), pero describen el modelo. En
  proyecciones recursivas se explica cada mes por separado.

### F. Monitoreo de modelos

| Método | Ruta | Estado | Contenido |
|---|---|---|---|
| GET | `/models/health` | ✅ (como `/health`) → alias | carga, SHA-256, error de carga |
| GET | `/models/metrics` | 🟡→🔵 | métricas por fase con IC desde `model_card.json` (✅ ya en `/model/info`) |
| GET | `/models/validation` | 🔵 Fase 1 | criterios A–G de validación y prueba (`ml/artifacts/phase2_validation/*/criteria.csv`, `phase3_testing`), cobertura de intervalos, *skill* por horizonte de las proyecciones |

Regla: estas métricas son **históricas por periodo**; nunca se adjuntan a una predicción individual como si fueran su
precisión.

---

## 6. Simulaciones

### 6.1 Sequía progresiva — 🔵 Fase 1 (meses sin lluvia) · 🟣 (reducción parcial)
- **Configuración:** duración 1–6 meses (`dry_months` consecutivos desde un mes elegido), reducción de lluvia en los
  meses vecinos (`rain_factor`), `t2m_delta`, comparación con años históricos (`analog`).
- **Cómo:** `scenario_drought` (✅): lluvia 0 y suelo superficial al mínimo observado 1998–2017 para ese mes y celda,
  Corrección: este caso **no pasó** su prueba de cordura pre-registrada (en el 25 % de las celdas el agua del suelo subió
  un poco), aunque su efecto promedio sí es secar el suelo (−0.04 m³/m³ en inicios de enero). Por eso se muestra con
  advertencia y se re-evalúa en la Fase 2 (sección 13).
- **Resultados:** serie mensual base vs. sequía con mediana y rango 90 %, diferencias absolutas y relativas,
  `within_model_error`, valores fuera de rango.
- **Pendiente (Fase 2):** sequías de 4–6 meses no se probaron; hindcast sugerido: reproducir los meses secos observados
  más largos de 1998–2022 y comparar con ERA5-Land.

### 6.2 El Niño — 🔵 Fase 1
- **Comparación:** año normal (28 años análogos) vs. años de El Niño costero por la regla del índice Niño 1+2
  (> +1.0 °C en ene–abr: 1998, 2016, 2017, 2023, 2024) vs. El Niño + cambios.
- **Resultados:** agua del suelo mensual, NDVI trimestral (`project_ndvi`), diferencias, celdas con respuesta inusual
  (respuesta fuera del percentil 5–95 de las celdas del mismo distrito).
- **Índice Niño 1+2:** está en `fs_ml/enso.py`; el modelo v2 con el índice como característica **no está aprobado**
  (sin diferencia en validación; decisión con 2026). Si se aprueba, este endpoint podrá usar el valor del índice.
- **Advertencias obligatorias:** solo 5 años análogos → rango menos confiable; no es un pronóstico oficial
  (ENFEN/SENAMHI/NOAA).

### 6.3 Temperatura — 🔵 Fase 1, etiqueta `experimental`
- **Configuración:** −2, −1, +1, +2, +3 °C (todos los meses o algunos).
- **Cómo:** `scenario_adjust(t2m_delta=…)` (✅). La evaporación potencial **no se recalcula** (no derivamos
  variables, decisión del equipo) → es una **prueba de sensibilidad directa**, no un escenario climático completo.
- **Antes de quitar la etiqueta:** prueba de cordura pre-registrada (p. ej., más calor no debe subir el agua del suelo
  en más del 1 % de las celdas), igual que las de lluvia; y aviso de extrapolación cuando la temperatura supera el
  máximo de 1998–2017.

### 6.4 Precipitación — 🟣 Fase 2, `experimental`
- **Configuración:** reducción o aumento (×0–×3), meses sin lluvia, comparación histórica.
- **Estado de evidencia:** las pruebas pre-registradas **fallaron** (lluvia ×2 bajó el agua del suelo en 38 % de las
  celdas en promedio; efecto medio ≤ +0.003 m³/m³, menor que el RMSE 0.0125). La API ya marca `rain_only_change`.
- **Camino para validarlo:** agregar la precipitación propia de ERA5-Land y restricciones monótonas en las
  características de lluvia (`monotone_constraints` de XGBoost) en un modelo v3, con validación completa (Fase 3).

### 6.5 Personalizado — 🟣 Fase 2
- **Variables:** lluvia (×), temperatura (Δ °C), humedad relativa (Δ puntos), evaporación potencial (×), viento (Δ m/s),
  radiación (Δ MJ/m²/día), duración y meses.
- **Implementación:** extender `fs_ml.project.scenario_adjust` con `pet_factor`, `ws_delta`, `allsky_delta`
  (misma función, no una paralela).
- **Coherencia física (advertencias, no bloqueos):** temperatura ↑ con evaporación ↓; lluvia ↑ con radiación ↑ y humedad ↓;
  lluvia = 0 con humedad > 90 %. **Bloqueos (422):** valores físicamente imposibles (lluvia < 0, HR fuera de 0–100,
  viento < 0). **Dominio:** cualquier entrada fuera de min–max de entrenamiento → `out_of_domain`.

### 6.6 Recuperación del suelo — 🟣 Fase 2
- **Configuración:** duración de la sequía previa (1–6 meses), clima posterior (análogos normales, El Niño, o ajustes),
  horizonte hasta 12 meses.
- **Cómo:** el mismo motor: `dry_months=[1..n]` y luego clima análogo; la recursión mensual hace el resto. NDVI
  trimestral sobre los trimestres completos.
- **Salida:** meses hasta volver dentro del rango del año normal (si ocurre en el horizonte), curva de recuperación,
  NDVI posterior.
- **Advertencia:** recuperación de **humedad** ≠ recuperación de fertilidad, nutrientes o productividad.
- **Validación pendiente:** la dinámica de recuperación nunca se evaluó; hindcast sobre secuencias secas observadas.

### 6.7 Posibles zonas irrigadas — 🟣 Fase 2 (validación) · 🔴 (clasificación)
- **Señal:** residuo de NDVI = observado − predicho, por celda y trimestre (2018–2025), persistente en meses secos.
  El modelo no conoce el riego, así que un verdor muy superior a lo esperado sugiere algo que el clima no explica.
- **Otras explicaciones posibles:** cambio de cultivo, vegetación natural tras lluvias, errores del compuesto NDVI
  (sensor y máscara sin documentar), nubes, cuerpos de agua.
- **Antes de clasificar:** validar contra datos independientes de superficie regada (MapBiomas Perú, proyecto Olmos,
  ANA). Mientras tanto, el endpoint solo devuelve "verdor mayor al esperado", nunca "zona irrigada".

---

## 7. Motor de escenarios

### 7.1 Flujo (un solo motor)

| Paso | Qué hace | Código existente |
|---|---|---|
| 1 | Recibe ubicación y configuración | `SimulationRequest` ✅ |
| 2 | Valida (Pydantic + reglas de dominio) | `schemas.py`, `months_in_horizon` ✅ |
| 3 | Obtiene el estado observado de la celda en `start` (agua del suelo profunda y superficial, 5 meses de lluvia, evaporación) | `project_sm` lee del `Cube` ✅ |
| 4 | Construye el **escenario base**: clima de cada año análogo para los meses siguientes | `analog_weather` ✅ |
| 5 | Modifica **solo** las variables pedidas en los meses pedidos | `select_members`, `scenario_drought`, `scenario_adjust` ✅ (+ extensiones 6.5) |
| 6 | Ejecuta el modelo de agua del suelo mes a mes | `_sm_features` + `project_sm` ✅ |
| 7 | Actualiza las dependientes: el agua del suelo predicha pasa a `sm_root_m3m3_lag1` del mes siguiente; la lluvia modificada actualiza rezagos y suma de 6 meses; la evaporación pasa a `pet_mm_lag1` | ✅ dentro de `_sm_features` |
| 8 | Ejecuta NDVI en trimestres completos (media de agua del suelo predicha, sumas de lluvia y evaporación) | `project_ndvi` ✅ (falta en `/simulations/climate`) |
| 9 | Diferencias escenario − base por miembro y en la mediana | `service.simulate` ✅ |
| 10 | Intervalos: cuantiles 5–95 % de los miembros + corrección conformal por horizonte (calibrada en hindcasts 2018–2022) | ✅ (`correction_by_lead`) |
| 11 | Dominio: fracción de entradas fuera de min–max y de p01–p99 | `out_of_training_range` ✅ (ampliar a todas las características) |
| 12 | Respuesta estructurada + nivel de confiabilidad + resumen generado de los números | ✅ parcial |

### 7.2 Reglas de diseño

- **Variables dependientes:** solo las que el modelo usa como rezago se propagan. El suelo superficial no se predice
  (el modelo no lo tiene como objetivo): se toma del año análogo, o del mínimo histórico en la sequía; esta
  aproximación se declara en la respuesta.
- **Secuencias y recursión:** siempre desde un mes observado (`start`); el error crece con el horizonte, por eso cada
  periodo lleva `within_useful_lead`.
- **Frecuencias:** agua del suelo mensual; NDVI solo en trimestres completos dentro del horizonte; si `start` no es
  fin de trimestre, el NDVI empieza en el siguiente trimestre completo (hoy `project_ndvi` exige fin de trimestre;
  propuesta: permitir inicios intermedios).
- **Base y modificado** usan los mismos años análogos y la misma semilla de datos, para que la diferencia sea solo el
  cambio pedido.
- **Rendimiento:** una celda × 28 miembros × 12 meses ≈ milisegundos; la grilla completa ≈ 1 s por escenario. Los
  escenarios de grilla completa se precalculan al iniciar (como `/projections`).

---

## 8. Contratos JSON (Pydantic)

Modelos reutilizables propuestos (los marcados ✅ ya existen con otro nombre o forma):

```python
class ConfidenceInterval(BaseModel):          # ✅ como Interval
    low: float; high: float; nominal: float = 0.9
    method: str                                # "split conformal by season" | "analog ensemble + conformal by lead"
    tested_coverage: float | None              # cobertura real medida en 2023-2025

class ModelWarning(BaseModel):                 # 🔵
    code: Literal["out_of_range", "out_of_domain", "beyond_useful_lead", "rain_only", "few_analogs",
                  "pet_not_recomputed", "experimental", "within_model_error"]
    message: str
    affected: list[str] = []                   # características o periodos

class ScenarioConfiguration(BaseModel):        # ✅ como Scenario (+ campos 6.5)
    rain_factor: float = 1; t2m_delta: float = 0; rh_delta: float = 0
    pet_factor: float = 1; ws_delta: float = 0; allsky_delta: float = 0     # propuestos
    months: list[int] | None = None; dry_months: list[int] = []
    analog: Literal["all", "el_nino"] | list[int] = "all"

class SimulationRequest(BaseModel):            # ✅
    location: Location; start: str = "2025-12"; horizon: int = 6; scenario: ScenarioConfiguration
    include_ndvi: bool = True                  # propuesto

class PeriodValue(BaseModel):                  # 🔵 (hoy Series usa listas paralelas)
    period: str; median: float | None; interval_90: ConfidenceInterval | None

class ScenarioComparison(BaseModel):           # ✅ como PeriodComparison
    period: str; absolute_difference: float | None; percentage_change: float | None
    direction: Literal["increased", "decreased", "unchanged"] | None
    within_model_error: bool | None; within_useful_lead: bool

class SimulationResponse(BaseModel):           # ✅ (+ campos nuevos)
    simulation_id: str; model_versions: dict[str, str]
    location: dict; start: str
    baseline: dict; scenario: dict             # {"soil_water": [PeriodValue], "ndvi": [PeriodValue]}
    comparison: dict                           # {"soil_water": [ScenarioComparison], "ndvi": [...]}
    modified_inputs: list[str]; warnings: list[ModelWarning]
    reliability: Literal["ok", "warning", "out_of_domain", "experimental"]
    interpretation: dict                       # summary (de los números) + limitations

class TerritorialAnalysisResponse(BaseModel):  # 🔵
    metric: str; scenario: str; period: str; unit: str; aggregation: str
    districts: list[dict]                      # district, province, cells, value, rank
    warnings: list[ModelWarning]
```

Ejemplo de `SimulationResponse` *(ilustrativo; la forma actual real está en `ml-api/README.md`)*:

```json
{
  "simulation_id": "sha256:4f1c…", "model_versions": { "sm_root_monthly": "a4bbaf13…", "ndvi_quarterly": "effe57ea…" },
  "location": { "cell_id": "-4438,-342", "province": "Lambayeque", "district": "Motupe", "cell_size_km": 2 },
  "start": "2025-12",
  "baseline": { "soil_water": [ { "period": "2026-01", "median": 0.128, "interval_90": { "low": 0.11, "high": 0.15, "nominal": 0.9, "method": "analog ensemble + conformal by lead", "tested_coverage": 0.80 } } ],
                "ndvi": [ { "period": "2026Q1", "median": 0.31, "interval_90": null } ] },
  "scenario": { "soil_water": [ … ], "ndvi": [ … ] },
  "comparison": { "soil_water": [ { "period": "2026-03", "absolute_difference": -0.05, "percentage_change": -19.0, "direction": "decreased", "within_model_error": false, "within_useful_lead": true } ] },
  "modified_inputs": [ "no rain and driest surface soil in lead months [2, 3]" ],
  "warnings": [ { "code": "pet_not_recomputed", "message": "Temperature changes do not recompute evaporation.", "affected": ["t2m_c"] } ],
  "reliability": "warning",
  "interpretation": { "summary": "…generado solo de los números…", "limitations": [ "…" ] }
}
```

---

## 9. Validaciones, métricas y confiabilidad

### 9.1 Qué significa cada número

| Concepto | Qué es | Qué **no** es |
|---|---|---|
| RMSE / MAE | error típico en unidades de la variable, medido en un periodo | la precisión de una predicción concreta |
| R² | fracción de la variación explicada en un periodo | un "porcentaje de acierto" |
| *Skill* | mejora frente a una regla simple (persistencia o climatología) | — |
| Intervalo 90 % | rango calibrado para contener el valor real 9 de cada 10 veces | la probabilidad de que *esta* predicción sea correcta |
| Cobertura real | cuántas veces lo contuvo en años no vistos (82 % / 84 % en 2023–2025) | — |
| Horizonte útil | meses en que la proyección supera a "un año típico" con IC > 0 (hindcasts) | — |

**Nunca se muestra un porcentaje de confianza inventado.** Si un intervalo no tiene cobertura medida, se dice.

### 9.2 Dominio de entrenamiento

- `preprocessing.json` guarda por característica min, p01, p50, p99, max y fracción de faltantes (1998–2017).
- Fuera de p01–p99 → `warning`. Fuera de min–max → `out_of_domain` (los árboles no extrapolan: devuelven la respuesta
  del extremo visto). En la prueba 2023–2025, el 18–21 % de las filas ya tenía alguna entrada fuera de p01–p99.

### 9.3 Niveles de confiabilidad de cada respuesta

| Nivel | Condición |
|---|---|
| `ok` | entradas dentro de p01–p99, periodo dentro del horizonte útil, tipo de escenario validado |
| `warning` | alguna entrada fuera de p01–p99, periodo más allá del horizonte útil, pocos análogos (< 10) o diferencia dentro del error del modelo |
| `out_of_domain` | alguna entrada fuera de min–max de entrenamiento |
| `experimental` | tipo de escenario sin validación aprobada (temperatura, lluvia, personalizado, recuperación, residuos de NDVI) |

### 9.4 Mejoras de incertidumbre previstas

- **CQR + recalibración adaptativa (ACI):** ya probada (cobertura 90 % / 89 % en 2023–2025, segunda mirada); servirla
  en `/predictions/*` y `/predictions/{cell}/confidence` tras confirmar con 2026 (Fase 2).
- **Hindcasts nuevos** para cada tipo de simulación antes de quitar `experimental`.
- **Años de El Niño:** todas las bandas fueron demasiado estrechas en 2023; las respuestas en escenarios El Niño deben
  decirlo.

---

## 10. Integración con el frontend

*(Este documento solo cambia el backend; esta sección describe el contrato para la web.)*

| Necesidad | Endpoint | Hoy |
|---|---|---|
| Elegir una celda en el mapa | la web calcula `cell_id` (`projections.js → cellAt`) o envía `lat/lon` | ✅ |
| Información ambiental de la celda | `/predictions/{cell_id}/history` | 🔵 |
| Proyección de la celda | `/projections/cell` | ✅ |
| Panel de simulación (tipo, variables, duración) | `/simulations/{tipo}` con `ScenarioConfiguration` | ✅ `climate` en `SimTuner.vue` |
| Gráfica mensual de agua del suelo / trimestral de NDVI con bandas | `SimulationResponse.baseline/scenario` | ✅ agua del suelo · 🔵 NDVI |
| Mapa de anomalías y comparación distrital | `/analysis/*` | 🟡 `district_summary` |

Reglas para la interfaz: distinguir **observado** (histórico), **ingresado por el usuario** (`modified_inputs`),
**predicho** (mediana + banda) y **comparación** (diferencias); mostrar siempre `reliability` y `warnings`;
"modo agricultor" sin decimales (ver `DESIGN.md`).

---

## 11. Integración con Sprout

✅ Hoy `POST /ask` envía a la IA la personalidad (`docs/SPROUT_PERSONA.md`), lo que el usuario ve y las 3 proyecciones
de la celda, con la regla de no inventar ni estimar números.

🔵 Propuesta: cuando el usuario corre una simulación, la web envía el `simulation_id`; `/ask` agrega a su contexto la
`SimulationResponse` completa (cambios, diferencias, rangos, avisos) y, si existe, la explicación TreeSHAP. Así Sprout
puede explicar **qué se modificó, qué cambió, qué variables pesaron, cuánta incertidumbre hay y qué límites tiene**,
sin diagnósticos agrícolas ni recomendaciones que los datos no respalden (rendimiento, dosis, cultivos).

---

## 12. Estructura del proyecto

Propuesta incremental. **No se mueve nada automáticamente**: cada paso mantiene las rutas y pruebas actuales.

```
ml-api/
├── app/
│   ├── main.py                 crea la app, incluye routers, manejadores de error (existente)
│   ├── config.py               (existente)
│   ├── routers/                🔵 se separan de main.py cuando superen ~150 líneas
│   │   ├── predictions.py · simulations.py · analysis.py · alerts.py · explanations.py · models.py · ask.py
│   ├── schemas/                🔵 dividir schemas.py: common.py · prediction.py · simulation.py · analysis.py
│   ├── services/               🔵 dividir service.py:
│   │   ├── state.py            carga de modelos y cubo (hoy load()/state())
│   │   ├── prediction.py       predict_one, validate_features, history
│   │   ├── scenario_engine.py  el motor único (hoy simulate()) + configuraciones por tipo
│   │   ├── projections.py      build_bundle, projection_at
│   │   ├── analysis.py · alerts.py · explanations.py · monitoring.py
│   └── ask.py                  (existente)
├── data/cube.npz               (existente; regenerar con ml/scripts/export_api_cube.py)
├── roadmap/README.md           este documento
├── tests/                      una prueba por endpoint con datos reales + pruebas de cordura de escenarios
├── requirements.txt · Dockerfile · .env.example · README.md
```

La capa de ML **sigue en `ml/fs_ml/`** (features, predict, project, enso, evaluate): no se crea `app/ml/` para no tener
dos versiones de la misma lógica. Lo que haga falta (ajustes de escenario, NDVI desde inicios intermedios, rangos
adaptativos) se agrega ahí y lo usan tanto la API como los notebooks.

---

## 13. Priorización por fases

### Fase 1 — Reutilización inmediata (sin entrenar)
- `POST /predictions/soil-water`, `/ndvi`, `/complete`, `/batch`; `GET /predictions/{cell_id}/history`.
- `POST /simulations/drought`, `/el-nino`, `/temperature` (`experimental`); NDVI dentro de las simulaciones;
  `simulation_id` + `GET /simulations/{id}/results`.
- `GET /analysis/districts`, `/water-retention`, `/vegetation` (desde lo ya calculado).
- `GET /explanations/{prediction_id}` (TreeSHAP).
- `GET /models/metrics`, `/models/health`, `/models/validation`.
- `ModelWarning` + `reliability` en todas las respuestas.

### Fase 2 — Validación adicional
- Prueba de cordura de temperatura; hindcasts de sequías largas y de recuperación.
- `/simulations/rainfall` y `/custom` (siguen `experimental` hasta pasar pruebas).
- `/analysis/drought-risk`, `/anomalies`, `/hotspots`; `/alerts/*` con ingesta mensual de datos.
- `/predictions/{cell_id}/confidence` y rangos adaptativos (CQR + ACI) confirmados con 2026.
- Validación separada de las 1,176 celdas fuera de Lambayeque antes de exponerlas.
- Contraste de residuos de NDVI con superficies regadas conocidas.

### Fase 3 — Datos y modelos nuevos
- Precipitación ERA5-Land y capa 2; modelo v3 con restricciones monótonas en lluvia (habilita el simulador de lluvia).
- Decisión sobre el modelo v2 con Niño 1+2 tras 2026.
- Superficies irrigadas por año → separar riego de secano y clasificar zonas.
- **Rendimientos por cultivo, calendarios agrícolas, campañas, producción por distrito y precios** → solo con estos
  datos se podría hablar de productividad, rentabilidad o recomendación de cultivos. **Hoy no podemos predecir nada de
  eso**: los modelos no se entrenaron para ello.

---

## 14. Limitaciones científicas

1. **Agua del suelo de ERA5-Land es un modelo, no una medición,** y no conoce el riego; describe suelo de secano.
2. **Resolución:** celdas de 2 km, pero el clima y el suelo de entrada son de ~9 km (ERA5-Land, GAEZ) y NASA POWER de
   55–110 km. No es "tu terreno".
3. **Persistencia:** el agua del suelo del mes anterior pesa 68 % de la ganancia del modelo; las cuatro entradas de
   lluvia, 2.4 %. Por eso los cambios solo de lluvia no son fiables.
4. **Años extremos:** los intervalos fueron demasiado estrechos con El Niño (cobertura 77 % en la temporada de lluvias y 77 % en 2023, frente al 90 % nominal).
5. **Deriva:** 2023–2025 tuvo más entradas fuera de rango y NDVI más verde que 1998–2017 (probable expansión del
   riego, no verificada).
6. **Asociaciones, no causas:** una simulación muestra la respuesta del modelo aprendida de 1998–2017.
7. **No es pronóstico del clima:** las proyecciones usan el clima de años pasados.
8. **Datos del NDVI:** sensor, máscara y método del compuesto sin documentar; 18 trimestres sin imagen en 1998–2017.
9. **Fuera de alcance:** rendimiento, cultivo, rentabilidad, dosis de insumos y calendarios de riego.

---

## 15. Hoja de ruta de implementación

| Paso | Entregable | Depende de | Prueba de aceptación |
|---|---|---|---|
| 1 | Dividir `service.py` en `services/` y `schemas.py` en `schemas/` sin cambiar comportamiento | — | las 6 pruebas actuales pasan sin cambios |
| 2 | `ModelWarning`, `reliability`, `simulation_id`/`prediction_id` por hash | 1 | mismas entradas → mismo id; niveles correctos en casos de prueba |
| 3 | NDVI en el motor de simulación (inicios en fin de trimestre) | 1 | con clima real, el primer trimestre coincide con la predicción directa del modelo (como la prueba de consistencia del notebook 06) |
| 4 | Endpoints de predicción A1–A5 | 2 | predicción por celda = `model.predict` sobre la fila del cubo; history marca `training/validation/testing` |
| 5 | Simulaciones `drought`, `el-nino`, `temperature` sobre el motor | 2, 3 | `drought` seca el suelo en promedio (prueba existente); `el-nino` usa exactamente los años de la regla |
| 6 | `explanations` (TreeSHAP) | 2 | suma de contribuciones + base = predicción (tolerancia 1e-4) |
| 7 | `analysis/districts`, `water-retention`, `vegetation`; `models/*` | 1 | ranking idéntico a `district_summary`; métricas idénticas a las tarjetas |
| 8 | Pre-registrar y correr pruebas de Fase 2 (temperatura, sequías largas, recuperación, residuos NDVI) en un notebook nuevo | 5 | reglas commiteadas antes de correr; resultados en `docs/` |
| 9 | Rangos adaptativos (CQR + ACI) en la API | confirmación 2026 | cobertura medida en 2026 dentro de 87–93 % |
| 10 | Probar el Dockerfile y publicar la API | — | `docker build` y `/health` = ok en el contenedor |

Cada paso se cierra con sus pruebas en `ml-api/tests/`, sin tocar los modelos probados (`ml/artifacts/final_model/`).
