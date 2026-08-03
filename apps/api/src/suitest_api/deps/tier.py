"""Workspace capability and autonomy enforcement decorators."""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from suitest_core.capabilities import Tier, TierFlag, tier_in
from suitest_db.repositories.llm_configs import LLMConfigRepo
from suitest_db.repositories.workspace_capabilities import WorkspaceCapabilityRepo
from suitest_shared.domain.enums import AutonomyLevel

from suitest_api.capabilities import provider_to_tier
from suitest_api.deps.scope import TenantContext

P = ParamSpec("P")
R = TypeVar("R")

REQUIRED_TIER_ATTR = "__suitest_required_tier__"


def require_tier(
    flag: TierFlag = TierFlag.ANY,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Enforce ``flag`` for workspace-aware endpoints and record the contract.

    ``TierFlag.ANY`` remains a zero-cost marker for deterministic service methods.
    Restricted endpoints must expose their injected ``ctx`` and ``session`` keyword
    arguments so a missing dependency fails closed.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if flag is not TierFlag.ANY:
                ctx = kwargs.get("ctx")
                session = kwargs.get("session")
                if not isinstance(ctx, TenantContext) or not isinstance(session, AsyncSession):
                    raise RuntimeError("restricted endpoint requires ctx and session dependencies")
                config = await LLMConfigRepo(session).get_active(ctx.workspace_id)
                if config is not None:
                    tier = provider_to_tier(config.provider)
                else:
                    capability = await WorkspaceCapabilityRepo(session).get(ctx.workspace_id)
                    tier = Tier(capability.tier.value) if capability is not None else Tier.ZERO
                if not tier_in(tier, flag):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "code": "LLM_NOT_CONFIGURED",
                            "message": "This endpoint requires LOCAL or CLOUD tier.",
                            "currentTier": tier.value,
                        },
                    )
            return await fn(*args, **kwargs)

        setattr(wrapper, REQUIRED_TIER_ATTR, flag)
        return wrapper

    return decorator


_AUTONOMY_RANK = {
    AutonomyLevel.MANUAL: 0,
    AutonomyLevel.ASSIST: 1,
    AutonomyLevel.SEMI_AUTO: 2,
    AutonomyLevel.AUTO: 3,
}


def require_autonomy(
    minimum: AutonomyLevel,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Enforce the workspace autonomy dial for agent actions."""

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ctx = kwargs.get("ctx")
            session = kwargs.get("session")
            if not isinstance(ctx, TenantContext) or not isinstance(session, AsyncSession):
                raise RuntimeError("autonomy-gated endpoint requires ctx and session dependencies")
            capability = await WorkspaceCapabilityRepo(session).get(ctx.workspace_id)
            current = capability.autonomy_level if capability is not None else AutonomyLevel.MANUAL
            if _AUTONOMY_RANK[current] < _AUTONOMY_RANK[minimum]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "SELF_HEAL_REQUIRES_ASSIST",
                        "message": f"This endpoint requires {minimum.value} autonomy or higher.",
                        "currentAutonomy": current.value,
                    },
                )
            return await fn(*args, **kwargs)

        return wrapper

    return decorator
