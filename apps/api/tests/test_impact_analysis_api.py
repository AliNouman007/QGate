from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from qgate_impact_analysis.engine import ImpactAnalyzer
from qgate_impact_analysis.source import UnifiedDiffSource
from qgate_impact_analysis.store import JsonImpactStore
from qgate_project_intelligence.models import AnalysisMetadata, ProjectKnowledge, ProjectSummary
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings


@pytest_asyncio.fixture
async def impact_local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'impact_api.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


def _saved_report(store_dir: Path):
    knowledge = ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/demo", source_fingerprint="fingerprint"),
        summary=ProjectSummary(),
        files=[],
    )
    patch = """diff --git a/new.ts b/new.ts
new file mode 100644
--- /dev/null
+++ b/new.ts
@@ -0,0 +1 @@
+export const x = 1;
"""
    report = ImpactAnalyzer(knowledge).analyze(UnifiedDiffSource(patch, source_id="patch:api").load())
    JsonImpactStore(store_dir).save(report)
    return report


@pytest.mark.asyncio
async def test_impact_latest_list_and_detail_are_local_and_authenticated(
    impact_local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await impact_local_api_db.seed_user(email="impact@example.test")
    workspace = await impact_local_api_db.member_workspace(user, slug="impact")
    store_dir = tmp_path / "impact-store"
    report = _saved_report(store_dir)
    key = JsonImpactStore.key_for(report)
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_IMPACT_ANALYSIS_DIR", str(store_dir))

    async with impact_local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        latest = await client.get("/api/v1/impact-analysis/latest", headers=headers)
        listing = await client.get("/api/v1/impact-analysis/reports", headers=headers)
        detail = await client.get(f"/api/v1/impact-analysis/reports/{key}", headers=headers)

    assert latest.status_code == 200
    assert latest.json()["metadata"]["change_source_id"] == "patch:api"
    assert listing.status_code == 200
    assert listing.json()[0]["key"] == key
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_impact_latest_returns_404_when_store_empty(
    impact_local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await impact_local_api_db.seed_user(email="impact-empty@example.test")
    workspace = await impact_local_api_db.member_workspace(user, slug="impact-empty")
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_IMPACT_ANALYSIS_DIR", str(tmp_path / "empty"))

    async with impact_local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/impact-analysis/latest",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_impact_api_is_hidden_in_server_mode(
    impact_local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await impact_local_api_db.seed_user(email="impact-server@example.test")
    workspace = await impact_local_api_db.member_workspace(user, slug="impact-server")
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_IMPACT_ANALYSIS_DIR", str(tmp_path))

    async with impact_local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/impact-analysis/reports",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404
