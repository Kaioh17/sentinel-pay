"""Layer 1 checks: pure rules, Postgres failover (sqlite stand-in), idempotency, both-stores-down."""
import asyncio

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models
from app.models import (
    AccountRiskStatus, AccountStatus, BlocklistSeverity, CountryRestriction, Decision, EntityBlocklist,
    EntityType, RestrictionType, RiskTier, TransactionCreate, User,
)
from app.service import risk


def tx(**kw) -> TransactionCreate:
    base = dict(transaction_id="t1", user_id=1, amount="10.00", currency="USD", merchant_id="m",
                ip_address="1.1.1.1", device_fingerprint="dev", country_code="US", card_hash=None)
    return TransactionCreate(**{**base, **kw})


def test_pure_checks_and_precedence():
    assert risk.check_account(None) == (Decision.DECLINE, "UNKNOWN_USER")
    assert risk.check_account(("FROZEN", "LOW", "x.com"))[0] == Decision.DECLINE
    assert risk.check_account(("ACTIVE", "HIGH", "x.com")) == (Decision.REVIEW, "ACCOUNT_RISK_TIER_HIGH")
    assert risk.check_country("KP", "BLOCKED") == (Decision.DECLINE, "COUNTRY_BLOCKED:KP")
    assert risk.check_country("US", None) == risk.OK
    hits = [("DEVICE_FINGERPRINT", "BLOCK_IMMEDIATELY"), ("IP_ADDRESS", "BLOCK_IMMEDIATELY")]
    assert risk.check_entities(hits) == (Decision.DECLINE, "ENTITY_BLOCK:IP_ADDRESS")  # fixed type order
    # account outranks country when both decline
    facts = risk.Facts(("SUSPENDED", "LOW", "x.com"), "BLOCKED")
    assert risk.decide("KP", facts).rule_triggered == "ACCOUNT_SUSPENDED"


class DownRedis:
    async def mget(self, *a): raise RedisConnectionError("down")
    async def set(self, *a, **k): raise RedisConnectionError("down")


@pytest.fixture
def pg(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(User(id=1, account_number="A1", full_name="A", email="a@Bad.com", country_code="US"))
        s.add(AccountRiskStatus(user_id=1, risk_tier=RiskTier.LOW, updated_by="t"))
        s.add(CountryRestriction(country_code="KP", restriction_type=RestrictionType.BLOCKED, reason="x", updated_by="t"))
        s.add(EntityBlocklist(entity_type=EntityType.EMAIL_DOMAIN, entity_value="bad.com",
                              severity=BlocklistSeverity.FLAG_FOR_REVIEW, created_by="t"))
        s.commit()
    monkeypatch.setattr(risk, "engine", engine)
    monkeypatch.setattr(risk.cache, "redis", DownRedis())
    monkeypatch.setattr(risk, "_retry_redis_at", 0.0)
    return engine


def test_failover_to_postgres(pg):
    r = asyncio.run(risk.assess(tx()))
    assert (r.decision, r.rule_triggered) == (Decision.REVIEW, "ENTITY_FLAG:EMAIL_DOMAIN")
    assert asyncio.run(risk.assess(tx(country_code="kp"))).rule_triggered == "COUNTRY_BLOCKED:KP"
    assert asyncio.run(risk.assess(tx(user_id=99))).rule_triggered == "UNKNOWN_USER"


def test_both_stores_down(pg, monkeypatch):
    monkeypatch.setattr(risk, "engine", create_engine("sqlite://"))  # no tables -> OperationalError
    r = asyncio.run(risk.assess(tx()))
    assert (r.decision, r.rule_triggered) == (Decision.REVIEW, "RISK_STORE_UNAVAILABLE")
