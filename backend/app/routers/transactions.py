from fastapi import APIRouter, BackgroundTasks

from app.logger import get_logger
from app.models import RiskDecision, TransactionCreate
from app.service import transaction

logger = get_logger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("")
async def create_transaction(body: TransactionCreate, tasks: BackgroundTasks) -> RiskDecision:
    return await transaction.make_transaction(body, tasks)
