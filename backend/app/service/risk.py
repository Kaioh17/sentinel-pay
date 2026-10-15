"""Layer 1 deterministic risk checks: account, country, entity.

Read order: Redis first, Postgres if Redis is down or cold, REVIEW if both fail.
The three check_* functions are pure, so equal facts always give an equal decision.
"""
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool
from redis.exceptions import RedisError
from sqlalchemy import or_, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app import cache
from app.db import engine
from app.logger import get_logger
from app.models import (
    AccountRiskStatus, AccountStatus, BlocklistSeverity, CountryRestriction, Decision,
    EntityBlocklist, EntityType, RestrictionType, RiskDecision, RiskTier, TransactionCreate, User,
)
from app.settings import settings

logger = get_logger(__name__)

WARM = "risk:warm"
LOCK = "risk:warm:lock"
WARM_TTL = settings.risk_reload_s * 2          # flag lapses if the reload loop dies -> Postgres reads
IDEM_TTL = 86_400
BREAKER_S = 5                                  # skip Redis this long after a failure
_RANK = {Decision.APPROVE: 0, Decision.REVIEW: 1, Decision.DECLINE: 2}
_ENTITY_ORDER = list(EntityType)
_ACCOUNT_DOWN = {AccountStatus.FROZEN, AccountStatus.SUSPENDED, AccountStatus.CLOSED}
_REDIS_DOWN = (RedisError, OSError, TimeoutError)

Verdict = tuple[Decision, str | None]
OK: Verdict = (Decision.APPROVE, None)
Account = tuple[str, str, str]                 # status, risk_tier, email_domain


class _Cold(Exception):
    """Redis is up but not loaded yet."""


@dataclass
class Facts:
    account: Account | None
    country: str | None = None                 # RestrictionType value
    hits: list[tuple[str, str]] = field(default_factory=list)  # (entity_type, severity)


# --- pure checks ----------------------------------------------------------------------------

def check_account(account: Account | None) -> Verdict:
    if account is None:
        return Decision.DECLINE, "UNKNOWN_USER"
    status, tier, _ = account
    if status in _ACCOUNT_DOWN:
        return Decision.DECLINE, f"ACCOUNT_{status}"
    if status == AccountStatus.RESTRICTED:
        return Decision.REVIEW, "ACCOUNT_RESTRICTED"
    if tier == RiskTier.HIGH:
        return Decision.REVIEW, "ACCOUNT_RISK_TIER_HIGH"
    return OK


def check_country(code: str, restriction: str | None) -> Verdict:
    if restriction == RestrictionType.BLOCKED:
        return Decision.DECLINE, f"COUNTRY_BLOCKED:{code}"
    if restriction == RestrictionType.REQUIRES_STEP_UP:
        return Decision.REVIEW, f"COUNTRY_STEP_UP:{code}"
    return OK


def check_entities(hits: list[tuple[str, str]]) -> Verdict:
    verdicts = [
        (Decision.DECLINE, f"ENTITY_BLOCK:{t}") if sev == BlocklistSeverity.BLOCK_IMMEDIATELY
        else (Decision.REVIEW, f"ENTITY_FLAG:{t}")
        for t, sev in sorted(hits, key=lambda h: _ENTITY_ORDER.index(EntityType(h[0])))
    ]
    return _worst(OK, *verdicts)


def _worst(*verdicts: Verdict) -> Verdict:
    return max(verdicts, key=lambda v: _RANK[v[0]])  # ties keep the first, so order is the precedence


def decide(code: str, facts: Facts) -> RiskDecision:
    decision, rule = _worst(check_account(facts.account), check_country(code, facts.country), check_entities(facts.hits))
    return RiskDecision(decision=decision, rule_triggered=rule)


# --- helpers --------------------------------------------------------------------------------

def _norm(value: str) -> str:
    return value.strip().lower()


def _domain(email: str) -> str:
    return _norm(email.rsplit("@", 1)[-1])


def _pack(status, tier, email: str) -> str:
    return f"{(status or AccountStatus.ACTIVE).value}|{(tier or RiskTier.LOW).value}|{_domain(email)}"


def _probes(tx: TransactionCreate) -> list[tuple[EntityType, str]]:
    pairs = [(EntityType.IP_ADDRESS, tx.ip_address), (EntityType.DEVICE_FINGERPRINT, tx.device_fingerprint),
             (EntityType.CARD_HASH, tx.card_hash)]
    return [(t, _norm(v)) for t, v in pairs if v]


def _ent_key(t: EntityType, v: str) -> str:
    return f"ent:{t.value}:{v}"


def _ttl(expires_at: datetime | None) -> int | None:
    return None if expires_at is None else max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds()))


# --- Postgres reads -------------------------------------------------------------------------

def _pg_account(db: Session, user_id: int) -> Account | None:
    row = db.exec(
        select(User.email, AccountRiskStatus.status, AccountRiskStatus.risk_tier)
        .select_from(User)
        .join(AccountRiskStatus, AccountRiskStatus.user_id == User.id, isouter=True)
        .where(User.id == user_id)
    ).first()
    return None if row is None else tuple(_pack(row[1], row[2], row[0]).split("|"))


def _pg_facts(tx: TransactionCreate) -> Facts:
    code = tx.country_code.upper()
    with Session(engine) as db:
        account = _pg_account(db, tx.user_id)
        restriction = db.exec(
            select(CountryRestriction.restriction_type).where(CountryRestriction.country_code == code)
        ).first()
        probes = _probes(tx) + ([(EntityType.EMAIL_DOMAIN, account[2])] if account else [])
        now = datetime.now(timezone.utc)
        hits = db.exec(
            select(EntityBlocklist.entity_type, EntityBlocklist.severity).where(
                tuple_(EntityBlocklist.entity_type, EntityBlocklist.entity_value).in_(probes),
                or_(EntityBlocklist.expires_at.is_(None), EntityBlocklist.expires_at > now),
            )
        ).all()
    return Facts(account, restriction, [(t.value, s.value) for t, s in hits])


# --- Redis reads ----------------------------------------------------------------------------

async def _redis_facts(tx: TransactionCreate) -> tuple[Facts, RiskDecision | None]:
    r, code, probes = cache.redis, tx.country_code.upper(), _probes(tx)
    warm, prior, acct, country, *ents = await r.mget(
        WARM, f"idem:{tx.transaction_id}", f"acct:{tx.user_id}", f"country:{code}",
        *(_ent_key(t, v) for t, v in probes),
    )
    if warm is None:
        raise _Cold
    if prior:
        return Facts(None), RiskDecision.model_validate_json(prior)
    if acct is None:                           # user created after the last reload: read through
        account = await run_in_threadpool(_pg_user, tx.user_id)
        if account:
            await r.set(f"acct:{tx.user_id}", "|".join(account), ex=WARM_TTL)
    else:
        account = tuple(acct.split("|"))
    hits = [(t.value, s) for (t, _), s in zip(probes, ents) if s]
    if account:                                # the domain comes from the account, so it needs a second read
        sev = await r.get(_ent_key(EntityType.EMAIL_DOMAIN, account[2]))
        if sev:
            hits.append((EntityType.EMAIL_DOMAIN.value, sev))
    return Facts(account, country, hits), None


def _pg_user(user_id: int) -> Account | None:
    with Session(engine) as db:
        return _pg_account(db, user_id)


# --- entry point ----------------------------------------------------------------------------

_retry_redis_at = 0.0


async def assess(tx: TransactionCreate) -> RiskDecision:
    global _retry_redis_at
    start, source, facts, prior = time.perf_counter(), "redis", None, None
    if time.monotonic() >= _retry_redis_at:
        try:
            facts, prior = await _redis_facts(tx)
        except (*_REDIS_DOWN, _Cold) as exc:
            _retry_redis_at = time.monotonic() + BREAKER_S
            logger.warning("risk cache unusable (%s), reading Postgres", type(exc).__name__)
    if facts is None:
        source = "postgres"
        try:
            facts = await run_in_threadpool(_pg_facts, tx)
        except SQLAlchemyError:
            logger.exception("risk Postgres read failed")
            source, result = "none", RiskDecision(decision=Decision.REVIEW, rule_triggered="RISK_STORE_UNAVAILABLE")
    if facts is not None:
        result = prior or decide(tx.country_code.upper(), facts)
        source = "idempotent" if prior else source
        if not prior:
            try:
                await cache.redis.set(f"idem:{tx.transaction_id}", result.model_dump_json(), ex=IDEM_TTL)
            except _REDIS_DOWN:
                pass
    logger.info("assess source=%s decision=%s rule=%s ms=%.2f",
                source, result.decision.value, result.rule_triggered, (time.perf_counter() - start) * 1000)
    return result


# --- cache reload ---------------------------------------------------------------------------

def _load_all() -> dict[str, tuple[str, int | None]]:
    """Every risk row as redis key -> (value, ttl). Only the columns the checks read."""
    now = datetime.now(timezone.utc)
    out: dict[str, tuple[str, int | None]] = {}
    # ponytail: every user is cached; switch to read-through only if users outgrow Redis memory
    with Session(engine) as db:
        for uid, email, status, tier in db.exec(
            select(User.id, User.email, AccountRiskStatus.status, AccountRiskStatus.risk_tier)
            .select_from(User).join(AccountRiskStatus, AccountRiskStatus.user_id == User.id, isouter=True)
        ):
            out[f"acct:{uid}"] = (_pack(status, tier, email), None)
        for code, rtype in db.exec(
            select(CountryRestriction.country_code, CountryRestriction.restriction_type)
            .where(CountryRestriction.restriction_type != RestrictionType.ALLOWED)
        ):
            out[f"country:{code.upper()}"] = (rtype.value, None)
        for etype, value, sev, exp in db.exec(
            select(EntityBlocklist.entity_type, EntityBlocklist.entity_value,
                   EntityBlocklist.severity, EntityBlocklist.expires_at)
            .where(or_(EntityBlocklist.expires_at.is_(None), EntityBlocklist.expires_at > now))
        ):
            out[_ent_key(etype, _norm(value))] = (sev.value, _ttl(exp))
    return out


async def warm_cache() -> None:
    """Replace the cached risk rows with Postgres truth. One worker at a time."""
    r = cache.redis
    try:
        if not await r.set(LOCK, 1, nx=True, ex=60):
            return
        try:
            fresh = await run_in_threadpool(_load_all)
            stale = {k for p in ("acct:*", "country:*", "ent:*") async for k in r.scan_iter(match=p)} - fresh.keys()
            pipe = r.pipeline()                # ponytail: one pipeline, chunk it past ~100k keys
            for k, (v, ttl) in fresh.items():
                pipe.set(k, v, ex=ttl)
            if stale:
                pipe.delete(*stale)
            pipe.set(WARM, 1, ex=WARM_TTL)
            await pipe.execute()
            logger.info("risk cache loaded keys=%d removed=%d", len(fresh), len(stale))
        finally:
            await r.delete(LOCK)
    except (*_REDIS_DOWN, SQLAlchemyError):
        logger.exception("risk cache reload failed, will retry")


async def reload_forever() -> None:
    while True:
        await warm_cache()
        await asyncio.sleep(settings.risk_reload_s)
