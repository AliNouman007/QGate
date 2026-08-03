from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from suitest_api.capabilities import build_base_capabilities, build_workspace_overlay
from suitest_api.deps.scope import TenantContext
from suitest_api.deps.tier import require_autonomy, require_tier
from suitest_core.capabilities import TierFlag
from suitest_db.models.workspace_capability import WorkspaceCapability
from suitest_shared.domain.enums import AutonomyLevel, Role, Tier


class _NoLlmRepo:
    def __init__(self, _session: AsyncSession) -> None:
        pass

    async def get_active(self, _workspace_id: str) -> None:
        return None


class _CapabilityRepo:
    level = AutonomyLevel.MANUAL
    tier = Tier.ZERO

    def __init__(self, _session: AsyncSession) -> None:
        pass

    async def get(self, _workspace_id: str) -> object:
        return SimpleNamespace(tier=self.tier, autonomy_level=self.level)


def test_workspace_overlay_preserves_current_autonomy() -> None:
    capability = WorkspaceCapability(
        workspace_id="ws-1",
        tier=Tier.CLOUD,
        autonomy_level=AutonomyLevel.MANUAL,
        features_json={},
    )
    overlay = build_workspace_overlay(
        build_base_capabilities(),
        workspace_capability=capability,
        active_llm_config=None,
        mcp_providers=[],
    )
    assert overlay.autonomy.default.value == "manual"


@pytest.mark.asyncio
async def test_restricted_tier_and_autonomy_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("suitest_api.deps.tier.LLMConfigRepo", _NoLlmRepo)
    monkeypatch.setattr("suitest_api.deps.tier.WorkspaceCapabilityRepo", _CapabilityRepo)
    ctx = TenantContext(workspace_id="ws-1", user_id="user-1", role=Role.OWNER)
    session = AsyncSession()

    @require_tier(TierFlag.CLOUD | TierFlag.LOCAL)
    async def tier_endpoint(*, ctx: TenantContext, session: AsyncSession) -> bool:
        return True

    with pytest.raises(HTTPException) as tier_error:
        await tier_endpoint(ctx=ctx, session=session)
    assert tier_error.value.status_code == 409

    _CapabilityRepo.tier = Tier.CLOUD

    @require_autonomy(AutonomyLevel.ASSIST)
    async def autonomy_endpoint(*, ctx: TenantContext, session: AsyncSession) -> bool:
        return True

    with pytest.raises(HTTPException) as autonomy_error:
        await autonomy_endpoint(ctx=ctx, session=session)
    assert autonomy_error.value.status_code == 409

    _CapabilityRepo.level = AutonomyLevel.ASSIST
    assert await autonomy_endpoint(ctx=ctx, session=session)
    await session.close()
