import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.risk import Decision


class TransactionCreate(SQLModel):             # request body: what the client knows
    transaction_id: str = Field(unique=True, index=True)  # external ref from client/gateway
    user_id: int = Field(index=True)
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    currency: str = Field(max_length=3)
    merchant_id: str = Field(index=True)
    ip_address: str
    device_fingerprint: str
    country_code: str = Field(min_length=2, max_length=2)  # ISO 3166-1 alpha-2, where it came from
    card_hash: str | None = None


class TransactionBase(TransactionCreate):      # plus what the system decides
    risk_score: float | None = None            # Layer 2 ML score, null when Layer 1 decided
    rule_triggered: str | None = None          # Layer 1 rule that fired, if any
    decision: Decision
    is_fraud: bool | None = None               # ground truth, set when chargeback arrives


class Transaction(TransactionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )


class TransactionRead(TransactionBase):
    id: uuid.UUID
    created_at: datetime
