from datetime import datetime, timezone
from enum import Enum, StrEnum

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.user import AccountStatus, RiskTier


class Decision(StrEnum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"


class RiskDecision(SQLModel):
    """Everything a caller needs back from a Layer 1 assessment."""
    rule_triggered: str | None = None          # Layer 1 rule that fired, if any
    decision: Decision


class RestrictionType(str, Enum):
    BLOCKED = "BLOCKED"
    REQUIRES_STEP_UP = "REQUIRES_STEP_UP"
    ALLOWED = "ALLOWED"


class EntityType(str, Enum):
    IP_ADDRESS = "IP_ADDRESS"
    DEVICE_FINGERPRINT = "DEVICE_FINGERPRINT"
    EMAIL_DOMAIN = "EMAIL_DOMAIN"
    CARD_HASH = "CARD_HASH"


class BlocklistSeverity(str, Enum):
    BLOCK_IMMEDIATELY = "BLOCK_IMMEDIATELY"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tz_col() -> dict:
    return {"sa_type": DateTime(timezone=True)}


class AccountRiskStatus(SQLModel, table=True):
    """User-level restrictions: freezes, lockouts, compliance holds."""
    __tablename__ = "account_risk_status"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    status: AccountStatus = AccountStatus.ACTIVE
    risk_tier: RiskTier = RiskTier.LOW
    flag_reason: str | None = None
    updated_by: str
    created_at: datetime = Field(default_factory=_now, **_tz_col())
    updated_at: datetime = Field(
        default_factory=_now, sa_type=DateTime(timezone=True), sa_column_kwargs={"onupdate": _now}
    )


class CountryRestriction(SQLModel, table=True):
    """Sanctions / fraud-rate / corridor policy per ISO country."""
    __tablename__ = "country_restrictions"
    id: int | None = Field(default=None, primary_key=True)
    country_code: str = Field(min_length=2, max_length=2, unique=True, index=True)
    restriction_type: RestrictionType
    reason: str
    updated_by: str
    updated_at: datetime = Field(
        default_factory=_now, sa_type=DateTime(timezone=True), sa_column_kwargs={"onupdate": _now}
    )


class EntityBlocklist(SQLModel, table=True):
    """Reused fraud data points: IPs, device fingerprints, card hashes, email domains."""
    __tablename__ = "entity_blocklist"
    __table_args__ = (UniqueConstraint("entity_type", "entity_value"),)
    id: int | None = Field(default=None, primary_key=True)
    entity_type: EntityType
    entity_value: str = Field(index=True)
    severity: BlocklistSeverity
    expires_at: datetime | None = Field(default=None, **_tz_col())  # null = permanent
    created_by: str
    created_at: datetime = Field(default_factory=_now, **_tz_col())
