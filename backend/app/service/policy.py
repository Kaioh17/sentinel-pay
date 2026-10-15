from app.models import Decision
from app.schemas import Thresholds
from app.logger import get_logger

logger = get_logger(__name__)


def decide(score: float, thresholds: Thresholds) -> Decision:
    """Layer 2. score < step_up: APPROVE, < decline: REVIEW, else DECLINE."""
    raise NotImplementedError
