import logging

from app.settings import settings

logging.basicConfig(
    level=logging.DEBUG if settings.environment == "dev" else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
