from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session

from app.db import engine
from app.logger import get_logger
from app.models import RiskDecision, Transaction, TransactionCreate
from app.service import risk

logger = get_logger(__name__)


async def mock_past_transactions(user_id, db):
    pass


async def make_transaction(body: TransactionCreate, tasks: BackgroundTasks) -> RiskDecision:
    """Decide from the risk cache, answer, and persist after the response is sent."""
    result = await risk.assess(body)
    tasks.add_task(save_transaction, body, result)
    return result


def save_transaction(body: TransactionCreate, result: RiskDecision) -> None:
    row = Transaction(**body.model_dump(), decision=result.decision, rule_triggered=result.rule_triggered)
    with Session(engine) as db:
        try:
            db.add(row)
            db.commit()
        except IntegrityError:                 # retried transaction_id: the first row already holds the decision
            db.rollback()
            logger.info("duplicate transaction_id=%s ignored", body.transaction_id)
        except SQLAlchemyError:
            # ponytail: no retry or outbox, a failed write is lost. Add an outbox if that is not acceptable.
            logger.exception("transaction not saved transaction_id=%s", body.transaction_id)
