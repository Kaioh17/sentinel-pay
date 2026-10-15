from app.schemas import ModelFeatures, User
from app.logger import get_logger

logger = get_logger(__name__)


def build(user: User, scenario_id: str, amount: float) -> ModelFeatures:
    """Layer 2. Assemble the vector in FEATURES order (scenario row + historical aggregates)."""
    raise NotImplementedError
