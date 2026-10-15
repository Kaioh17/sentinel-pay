"""Seed 8 mock users with 10-15 transactions each. Run from backend/: python -m scripts.seed_mock"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import (
    AccountRiskStatus, AccountStatus, BlocklistSeverity, CountryRestriction, Decision, EntityBlocklist, EntityType,
    RestrictionType, RiskTier, Transaction, User,
)

random.seed(42)

# One account per Layer 1 account/entity outcome, so each can be picked on purpose in the UI.
# (account_number, name, email, phone, country, status, tier, flag_reason)
A, F, SU, R = AccountStatus.ACTIVE, AccountStatus.FROZEN, AccountStatus.SUSPENDED, AccountStatus.RESTRICTED
LOW, MED, HIGH = RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH
USERS = [
    ("ACC-1001", "Amara Okafor", "amara.okafor@example.com", "+2348012345001", "NG", A, LOW, None),    # clean
    ("ACC-1002", "Lukas Brandt", "lukas.brandt@example.com", "+493012340104", "DE", A, LOW, None),      # clean
    ("ACC-1003", "James Whitfield", "james.whitfield@example.com", "+14155550102", "US", F, LOW, "Chargeback abuse"),  # DECLINE
    ("ACC-1004", "Sofia Marin", "sofia.marin@example.com", "+34911230105", "ES", SU, MED, "KYC documents expired"),   # DECLINE
    ("ACC-1005", "Priya Raman", "priya.raman@example.com", "+442071230103", "GB", R, MED, "Compliance hold"),         # REVIEW
    ("ACC-1006", "Carlos Mendes", "carlos.mendes@example.com", "+5511987650105", "BR", A, HIGH, "Repeated disputes"),  # REVIEW
    ("ACC-1007", "Tunde Bakare", "tunde.bakare@tempmail.test", "+2348012345007", "NG", A, LOW, None),   # email domain flagged: REVIEW
    ("ACC-1008", "Ivan Petrov", "ivan.petrov@fraudmail.test", "+79015550108", "RU", A, LOW, None),      # email domain blocked: DECLINE
]
MERCHANTS = ["merch_amazon", "merch_uber", "merch_netflix", "merch_shell", "merch_walmart", "merch_steam"]
CURRENCY = {"NG": "NGN", "US": "USD", "GB": "GBP", "DE": "EUR", "BR": "BRL", "ES": "EUR", "RU": "RUB"}


# Hit by the frontend scenarios (frontend/src/scenarioData.ts) and the accounts above. Keep values lower case:
# the checks lower-case what they look up.
COUNTRIES = [("KP", RestrictionType.BLOCKED, "sanctions"), ("RU", RestrictionType.REQUIRES_STEP_UP, "corridor policy")]
BLOCK, FLAG = BlocklistSeverity.BLOCK_IMMEDIATELY, BlocklistSeverity.FLAG_FOR_REVIEW
ENTITIES = [
    (EntityType.IP_ADDRESS, "203.0.113.150", FLAG),
    (EntityType.IP_ADDRESS, "203.0.113.200", BLOCK),
    (EntityType.DEVICE_FINGERPRINT, "dfp_new_device_9f2c", FLAG),
    (EntityType.DEVICE_FINGERPRINT, "dfp_takeover_3b1a", BLOCK),
    (EntityType.CARD_HASH, "card_disputed_21", FLAG),
    (EntityType.CARD_HASH, "card_tested_77", BLOCK),
    (EntityType.EMAIL_DOMAIN, "tempmail.test", FLAG),
    (EntityType.EMAIL_DOMAIN, "fraudmail.test", BLOCK),
]


def seed_risk(db: Session) -> None:
    for code, kind, reason in COUNTRIES:
        if not db.exec(select(CountryRestriction).where(CountryRestriction.country_code == code)).first():
            db.add(CountryRestriction(country_code=code, restriction_type=kind, reason=reason, updated_by="seed"))
    for etype, value, severity in ENTITIES:
        if not db.exec(select(EntityBlocklist).where(EntityBlocklist.entity_type == etype,
                                                     EntityBlocklist.entity_value == value)).first():
            db.add(EntityBlocklist(entity_type=etype, entity_value=value, severity=severity, created_by="seed"))
    db.commit()


def mock_transaction(user: User, tier: RiskTier, n: int) -> Transaction:
    risky = random.random() < (0.3 if tier == RiskTier.HIGH else 0.08)
    score = round(random.uniform(0.70, 0.99) if risky else random.uniform(0.01, 0.30), 2)
    amount = random.uniform(500, 5000) if risky else random.uniform(5, 250)
    return Transaction(
        transaction_id=f"txn_{user.account_number}_{n:02d}_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        amount=Decimal(f"{amount:.2f}"),
        currency=CURRENCY[user.country_code],
        merchant_id=random.choice(MERCHANTS),
        ip_address=f"203.0.113.{random.randint(1, 99)}",  # documentation range, below the blocklisted .150 and .200
        device_fingerprint=f"dfp_{uuid.uuid4().hex[:12]}",
        country_code=user.country_code,
        risk_score=score,
        rule_triggered="velocity_limit" if risky and score > 0.9 else None,
        decision=Decision.DECLINE if score > 0.9 else Decision.REVIEW if score > 0.7 else Decision.APPROVE,
        is_fraud=True if score > 0.9 else None,
        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 60), minutes=random.randint(0, 1440)),
    )


def main() -> None:
    init_db()
    with Session(engine) as db:
        seed_risk(db)
        for acc, name, email, phone, country, status, tier, reason in USERS:
            if db.exec(select(User).where(User.account_number == acc)).first():
                print(f"skip {acc} (exists)")
                continue
            user = User(account_number=acc, full_name=name, email=email, phone_number=phone,
                        country_code=country)
            db.add(user)
            db.commit()
            db.refresh(user)
            db.add(AccountRiskStatus(user_id=user.id, status=status, risk_tier=tier, flag_reason=reason, updated_by="seed"))
            txns = [mock_transaction(user, tier, i) for i in range(random.randint(10, 15))]
            db.add_all(txns)
            db.commit()
            print(f"{acc}: user {user.id} + {len(txns)} transactions")


if __name__ == "__main__":
    main()
