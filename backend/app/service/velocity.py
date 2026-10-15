from app.schemas import RuleResult, Thresholds
from app.logger import get_logger

logger = get_logger(__name__)


def check(user_id: str, thresholds: Thresholds) -> RuleResult:
    """Layer 1. Redis sliding-window counter: tx count per user within the window."""
    raise NotImplementedError
