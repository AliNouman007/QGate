from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from qgate_project_intelligence.models import Confidence, Evidence
from qgate_scenario_intelligence.models import (
    AutomationReadiness,
    GenerationBudget,
    Scenario,
    ScenarioKind,
    ScenarioPlan,
    ScenarioPlanMetadata,
    ScenarioPriority,
    ScenarioStep,
    ScenarioSummary,
)
from qgate_scenario_intelligence.store import JsonScenarioPlanStore
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings


@pytest_asyncio.fixture
async def local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'scenario_api.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


def _plan() -> ScenarioPlan:
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/demo",
            project_fingerprint="fp",
            impact_change_source_id="git:main...feature",
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=1, ready=1, p1=1),
        scenarios=[
            Scenario(
                key="scn_1",
                title="Verify /search",
                kind=ScenarioKind.SMOKE,
                priority=ScenarioPriority.P1,
                confidence=Confidence.HIGH,
                routes=["/search"],
                steps=[ScenarioStep(action="Open /search", expected="Search loads", route="/search")],
                reason="Impacted route",
                source_impact_keys=["route:/search"],
                evidence=[Evidence(path="src/page.tsx", line=1, excerpt="page", kind="route")],
                readiness=AutomationReadiness.READY,
            )
        ],
    )


@pytest.mark.asyncio
async def test_scenario_intelligence_latest_list_and_detail_are_local_and_authenticated(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="scenarios@example.test")
    workspace = await local_api_db.member_workspace(user, slug="scenarios")
    store_dir = tmp_path / "plans"
    store = JsonScenarioPlanStore(store_dir)
    plan = _plan()
    store.save(plan)
    key = store.key_for(plan)
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_SCENARIO_INTELLIGENCE_DIR", str(store_dir))

    async with local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        latest = await client.get("/api/v1/scenario-intelligence/latest", headers=headers)
        listing = await client.get("/api/v1/scenario-intelligence/plans", headers=headers)
        detail = await client.get(f"/api/v1/scenario-intelligence/plans/{key}", headers=headers)

    assert latest.status_code == 200
    assert latest.json()["summary"]["total"] == 1
    assert listing.status_code == 200
    assert listing.json()[0]["key"] == key
    assert detail.status_code == 200
    assert detail.json()["scenarios"][0]["title"] == "Verify /search"


@pytest.mark.asyncio
async def test_scenario_intelligence_latest_returns_404_when_empty(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="empty-scenarios@example.test")
    workspace = await local_api_db.member_workspace(user, slug="empty-scenarios")
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_SCENARIO_INTELLIGENCE_DIR", str(tmp_path / "empty"))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/scenario-intelligence/latest",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_scenario_intelligence_is_hidden_in_server_mode(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="server-scenarios@example.test")
    workspace = await local_api_db.member_workspace(user, slug="server-scenarios")
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_SCENARIO_INTELLIGENCE_DIR", str(tmp_path))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/scenario-intelligence/plans",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404
