from fastapi import APIRouter

from app.schemas import Thresholds
from app.service import store
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/thresholds")
async def get_thresholds() -> Thresholds:
    return store.THRESHOLDS


@router.put("/thresholds")
async def set_thresholds(body: Thresholds) -> Thresholds:
    """Adjust risk appetite live. Should reject step_up >= decline."""
    raise NotImplementedError
