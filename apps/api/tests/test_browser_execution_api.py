from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from qgate_browser_execution.models import (
    ExecutionMetadata,
    ExecutionReport,
    ExecutionStatus,
    ExecutionSummary,
    ScenarioExecution,
)
from qgate_browser_execution.store import JsonExecutionReportStore
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings


@pytest_asyncio.fixture
async def local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'execution_api.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


def _report() -> ExecutionReport:
    return ExecutionReport(
        metadata=ExecutionMetadata(
            run_id="run-api",
            scenario_plan_key="plan-api",
            project_source_id="local:/demo",
            project_fingerprint="fingerprint",
            impact_change_source_id="diff:1",
            config_fingerprint="config",
            started_at=datetime.now(UTC),
        ),
        summary=ExecutionSummary(selected=1, executed=1, passed=1),
        scenarios=[
            ScenarioExecution(
                scenario_key="scn-1",
                title="Checkout smoke",
                kind="smoke",
                priority="P0",
                status=ExecutionStatus.PASSED,
                verified=True,
            )
        ],
    )


@pytest.mark.asyncio
async def test_browser_execution_latest_list_and_detail_are_local_and_authenticated(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="execution@example.test")
    workspace = await local_api_db.member_workspace(user, slug="execution")
    store_dir = tmp_path / "execution-reports"
    store = JsonExecutionReportStore(store_dir)
    report = _report()
    store.save(report)
    key = store.key_for(report)
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_BROWSER_EXECUTION_DIR", str(store_dir))

    async with local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        latest = await client.get("/api/v1/browser-execution/latest", headers=headers)
        listing = await client.get("/api/v1/browser-execution/reports", headers=headers)
        detail = await client.get(f"/api/v1/browser-execution/reports/{key}", headers=headers)

    assert latest.status_code == 200, f"Got status {latest.status_code}: {latest.json()}"
    assert latest.json()["summary"]["passed"] == 1
    assert listing.status_code == 200
    assert listing.json()[0]["key"] == key
    assert detail.status_code == 200
    assert detail.json()["scenarios"][0]["status"] == "passed"


@pytest.mark.asyncio
async def test_browser_execution_latest_returns_404_when_empty(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="empty-execution@example.test")
    workspace = await local_api_db.member_workspace(user, slug="empty-execution")
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_BROWSER_EXECUTION_DIR", str(tmp_path / "empty"))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/browser-execution/latest",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_browser_execution_is_hidden_in_server_mode(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="server-execution@example.test")
    workspace = await local_api_db.member_workspace(user, slug="server-execution")
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_BROWSER_EXECUTION_DIR", str(tmp_path))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/browser-execution/reports",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404
