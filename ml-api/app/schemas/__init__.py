"""Pydantic contracts of the ML API (roadmap §8). Requests reject unknown fields; responses keep every field."""
from .ask import AskRequest, AskResponse, ChatTurn
from .common import Location, ModelName, ModelWarning, Open, Reliability, Strict
from .prediction import BatchRequest, CellPredictionRequest, CompleteRequest, Interval, PredictionRequest, PredictionResponse
from .simulation import (DroughtRequest, ElNinoRequest, PeriodComparison, RainfallRequest, RecoveryRequest, Scenario,
                         ScenarioConfiguration, Series, SimulationRequest, SimulationResponse, TemperatureRequest)

ConfidenceInterval = Interval
