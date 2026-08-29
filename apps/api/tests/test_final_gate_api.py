from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from qgate_final_gate.models import (
    CoverageSummary,
    GateConfidence,
    GateMetadata,
    GateReport,
    GateVerdict,
)
from qgate_final_gate.store import JsonGateReportStore
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings


@pytest_asyncio.fixture
async def local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'final_gate_api.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


def _report() -> GateReport:
    return GateReport(
        metadata=GateMetadata(
            report_key="gate_1234567890abcdef1234",
            project_source_id="local:/shop",
            project_fingerprint="fp",
            change_source_id="change:1",
            scenario_plan_key="plan:1",
            execution_run_id="run:1",
        ),
        verdict=GateVerdict.PASS,
        confidence=GateConfidence.HIGH,
        headline="PASS — all required scenarios verified",
        coverage_summary=CoverageSummary(required_total=1, required_verified_pass=1),
    )


@pytest.mark.asyncio
async def test_final_gate_reports_are_local_authenticated(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="gate@example.test")
    workspace = await local_api_db.member_workspace(user, slug="gate")
    root = tmp_path / "gate"
    JsonGateReportStore(root).save(_report())
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_FINAL_GATE_DIR", str(root))

    async with local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        listing = await client.get("/api/v1/final-gate/reports", headers=headers)
        latest = await client.get("/api/v1/final-gate/latest", headers=headers)
        detail = await client.get(
            "/api/v1/final-gate/reports/gate_1234567890abcdef1234",
            headers=headers,
        )

    assert listing.status_code == 200
    assert listing.json()[0]["verdict"] == "PASS"
    assert latest.status_code == 200
    assert latest.json()["metadata"]["report_key"] == "gate_1234567890abcdef1234"
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_final_gate_latest_returns_404_when_empty(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="gate-empty@example.test")
    workspace = await local_api_db.member_workspace(user, slug="gate-empty")
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_FINAL_GATE_DIR", str(tmp_path / "empty"))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/final-gate/latest",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_final_gate_hidden_in_server_mode(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="gate-server@example.test")
    workspace = await local_api_db.member_workspace(user, slug="gate-server")
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_FINAL_GATE_DIR", str(tmp_path / "gate"))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/final-gate/reports",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404
