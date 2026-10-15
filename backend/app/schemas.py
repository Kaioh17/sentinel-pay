from enum import StrEnum
from typing import Annotated

import pandas as pd
from pydantic import BaseModel, Field, field_validator


# Column order the model was trained on (creditcardfraud). Single source of truth.
FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]


class ScenarioKind(StrEnum):
    AUTHENTIC = "authentic"
    SUSPICIOUS = "suspicious"
    FRAUDULENT = "fraudulent"


class Scenario(BaseModel):
    id: str
    kind: ScenarioKind
    label: str
    description: str
    default_amount: Annotated[float, Field(gt=0)]


class MockTransaction(BaseModel):
    id: str
    merchant: str
    amount: float
    timestamp: str


class UserCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=40)]


class User(BaseModel):
    id: str
    name: str
    balance: float
    transactions: list[MockTransaction]


class Thresholds(BaseModel):
    step_up: Annotated[float, Field(ge=0, le=1)] = 0.30
    decline: Annotated[float, Field(ge=0, le=1)] = 0.70
    hard_limit_amount: Annotated[float, Field(gt=0)] = 10_000
    velocity_max_tx: Annotated[int, Field(gt=0)] = 5
    velocity_window_seconds: Annotated[int, Field(gt=0)] = 300


class RuleResult(BaseModel):
    service: str  # velocity | blocklist | hard_limits
    tripped: bool
    reason: str | None = None


class ModelFeatures(BaseModel):
    """One scored row. Keys must match FEATURES exactly."""

    values: dict[str, float]

    @field_validator("values")
    @classmethod
    def _check_columns(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(FEATURES):
            raise ValueError("feature columns do not match the trained schema")
        return v

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([self.values])[FEATURES]
