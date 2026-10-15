from fastapi import APIRouter

from app.schemas import Scenario
from app.service.store import SCENARIOS
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
async def list_scenarios() -> list[Scenario]:
    """Authentic, suspicious and fraudulent options the user can pick from."""
    return SCENARIOS
