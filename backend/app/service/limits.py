from app.schemas import RuleResult, Thresholds, User
from app.logger import get_logger

logger = get_logger(__name__)


def check(user: User, amount: float, thresholds: Thresholds) -> RuleResult:
    """Layer 1. Absolute ceiling, insufficient balance."""
    raise NotImplementedError
