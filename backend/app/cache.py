from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.settings import settings

# Short timeouts and no client retries: a down Redis must cost milliseconds before the Postgres
# failover. The client default retries with seconds of backoff.
redis = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    decode_responses=True,
    socket_connect_timeout=settings.redis_timeout_s,
    socket_timeout=settings.redis_timeout_s,
    retry=Retry(NoBackoff(), 0),
)
