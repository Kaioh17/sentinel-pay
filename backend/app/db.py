from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.settings import settings

engine = create_engine(
    settings.database_url,
    echo=settings.environment == "dev",
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def warm_pool() -> None:
    """Open every pooled connection now, so no request pays the connect and auth handshake."""
    conns = [engine.raw_connection() for _ in range(settings.db_pool_size)]
    for c in conns:
        c.close()  # returns it to the pool


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
