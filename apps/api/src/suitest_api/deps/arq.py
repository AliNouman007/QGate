"""FastAPI dependency: shared :class:`arq.connections.ArqRedis` pool.

The pool is constructed once per app on first call and stashed on
``app.state.arq`` so subsequent requests reuse it. In local development or
when Redis is unavailable, returns ``None`` so run creation persists the SQL
record without timing out on Redis.
"""

from __future__ import annotations

import os

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import Request


async def get_arq(request: Request) -> ArqRedis | None:
    """Return a shared :class:`ArqRedis` for ``app.state.arq``, building it on first hit.

    Returns ``None`` in local mode or when Redis connection fails so API endpoints
    stay operational without requiring a running Redis broker.
    """
    settings = getattr(request.app.state, "settings", None)
    mode = os.environ.get("SUITEST_MODE", getattr(settings, "mode", "server"))
    if mode == "local":
        return None

    existing = getattr(request.app.state, "arq", None)
    if isinstance(existing, ArqRedis):
        return existing

    url = os.environ.get("SUITEST_REDIS_URL", "redis://localhost:6379/0")
    try:
        pool = await create_pool(RedisSettings.from_dsn(url))
        request.app.state.arq = pool
        return pool
    except Exception:
        return None
