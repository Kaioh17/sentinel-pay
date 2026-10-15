from app.schemas import ModelFeatures
from app.logger import get_logger

logger = get_logger(__name__)


def score(model, features: ModelFeatures) -> float:
    """Layer 2. model.predict_proba(features.to_frame())[:, 1] -> fraud probability in [0, 1]."""
    raise NotImplementedError
