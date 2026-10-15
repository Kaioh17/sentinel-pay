from sqlmodel import Session, SQLModel, create_engine, text

from app import models  # noqa: F401
from app.settings import Settings


def test_settings_defaults():
    assert Settings().environment in ("dev", "prod")


def test_metadata_creates_and_session_works():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        assert s.exec(text("select 1")).scalar() == 1
