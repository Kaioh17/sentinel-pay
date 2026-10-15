from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: Literal["dev", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/sentinelpay"
    db_pool_size: int = 10
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_timeout_s: float = 0.05
    risk_reload_s: int = 300                   # full Postgres -> Redis reload period


settings = Settings()
