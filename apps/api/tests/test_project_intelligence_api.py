from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.source import LocalPathSource
from qgate_project_intelligence.store import JsonKnowledgeStore
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings


@pytest_asyncio.fixture
async def local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    """SQLite API harness so tests execute deterministically without Docker."""
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'pi_api.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_project_intelligence_latest_and_list_are_local_and_authenticated(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="project-map@example.test")
    workspace = await local_api_db.member_workspace(user, slug="project-map")
    project = tmp_path / "target"
    project.mkdir()
    (project / "app").mkdir()
    (project / "app/page.tsx").write_text(
        "export default function Home() { return <main>Home</main>; }\n",
        encoding="utf-8",
    )
    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(project))
    store_dir = tmp_path / "knowledge"
    JsonKnowledgeStore(store_dir).save(knowledge)

    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_PROJECT_INTELLIGENCE_DIR", str(store_dir))

    async with local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        latest = await client.get("/api/v1/project-intelligence/latest", headers=headers)
        listing = await client.get("/api/v1/project-intelligence/projects", headers=headers)

    assert latest.status_code == 200
    assert latest.json()["metadata"]["source_id"] == knowledge.metadata.source_id
    assert listing.status_code == 200
    assert listing.json()[0]["source_id"] == knowledge.metadata.source_id
    assert listing.json()[0]["key"] == store_dir.joinpath(
        JsonKnowledgeStore.key_for(knowledge.metadata.source_id) + ".json"
    ).stem


@pytest.mark.asyncio
async def test_project_intelligence_latest_returns_404_when_store_empty(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="empty-project-map@example.test")
    workspace = await local_api_db.member_workspace(user, slug="empty-project-map")
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_PROJECT_INTELLIGENCE_DIR", str(tmp_path / "empty"))

    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/project-intelligence/latest",
            headers={"X-Workspace-Id": workspace.id},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_intelligence_is_hidden_in_server_mode(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await local_api_db.seed_user(email="server-project-map@example.test")
    workspace = await local_api_db.member_workspace(user, slug="server-project-map")
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_PROJECT_INTELLIGENCE_DIR", str(tmp_path))

    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/project-intelligence/projects",
            headers={"X-Workspace-Id": workspace.id},
        )

    assert response.status_code == 404
