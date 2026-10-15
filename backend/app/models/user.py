from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    SUSPENDED = "SUSPENDED"
    RESTRICTED = "RESTRICTED"
    CLOSED = "CLOSED"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserBase(SQLModel):                      # shared fields, pydantic only
    account_number: str = Field(unique=True, index=True)  # external customer ID
    full_name: str                             # legal name for KYC
    email: str = Field(unique=True, index=True)
    phone_number: str | None = Field(default=None, index=True)
    country_code: str = Field(min_length=2, max_length=2, index=True)  # ISO 3166-1 alpha-2
    is_pep: bool = False


class User(UserBase, table=True):              # DB table (also a pydantic model)
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(
        default_factory=_now,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": _now},
    )


class UserCreate(UserBase): ...                # request body: no id
class UserUpdate(SQLModel):                    # all optional, for partial update
    full_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    is_pep: bool | None = None
class UserRead(UserBase):                      # response: includes id
    id: int
    account_status: AccountStatus = AccountStatus.ACTIVE  # from account_risk_status, not a users column
    risk_tier: RiskTier = RiskTier.LOW
    created_at: datetime
    updated_at: datetime
