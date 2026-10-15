from app.schemas import Scenario, Thresholds, User
from app.logger import get_logger

logger = get_logger(__name__)

# In-memory state for the simulation. No database.
USERS: dict[str, User] = {}
SCENARIOS: list[Scenario] = []  # ponytail: fill from sampled dataset rows (legit / borderline / fraud)
THRESHOLDS = Thresholds()
