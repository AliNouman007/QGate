from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from qgate_qa_memory.lifecycle import QAMemoryService
from qgate_qa_memory.models import CandidateKind, MemoryCandidate
from qgate_qa_memory.signature import candidate_signature
from qgate_qa_memory.store import JsonQAMemoryStore
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings


@pytest_asyncio.fixture
async def local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'qa_memory_api.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


def _candidate() -> MemoryCandidate:
    item = MemoryCandidate(
        key="candidate_12345678",
        project_source_id="local:/shop",
        project_fingerprint="fp",
        title="Checkout label",
        invariant="Final payable must show You Pay",
        kind=CandidateKind.ASSERTION_REGRESSION,
        routes=["/checkout"],
        states=["wallet"],
        dedupe_signature="pending",
    )
    item.dedupe_signature = candidate_signature(item)
    return item


@pytest.mark.asyncio
async def test_qa_memory_read_and_confirm_are_local_authenticated(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUITEST_MODE", "local")
    root = tmp_path / "memory"
    monkeypatch.setenv("SUITEST_QA_MEMORY_DIR", str(root))
    user = await local_api_db.seed_user(email="memory@example.test")
    workspace = await local_api_db.member_workspace(user, slug="memory")
    root = tmp_path / "memory"
    service = QAMemoryService(JsonQAMemoryStore(root))
    candidate = service.ingest_candidate(_candidate())
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_QA_MEMORY_DIR", str(root))

    async with local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        listing = await client.get("/api/v1/qa-memory/candidates", headers=headers)
        confirm = await client.post(
            f"/api/v1/qa-memory/candidates/{candidate.key}/confirm",
            headers=headers,
            json={"note": "confirmed by QA"},
        )
        memories = await client.get("/api/v1/qa-memory/memories", headers=headers)

    assert listing.status_code == 200
    assert listing.json()[0]["status"] == "pending"
    assert confirm.status_code == 200
    assert confirm.json()["candidate"]["status"] == "confirmed"
    assert confirm.json()["memory"]["confirmed_by"] == str(user.id)
    assert memories.status_code == 200
    assert len(memories.json()) == 1


@pytest.mark.asyncio
async def test_rejected_candidate_cannot_be_confirmed(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUITEST_MODE", "local")
    root = tmp_path / "memory"
    monkeypatch.setenv("SUITEST_QA_MEMORY_DIR", str(root))
    user = await local_api_db.seed_user(email="reject@example.test")
    workspace = await local_api_db.member_workspace(user, slug="reject")
    root = tmp_path / "memory"
    service = QAMemoryService(JsonQAMemoryStore(root))
    candidate = service.ingest_candidate(_candidate())
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_QA_MEMORY_DIR", str(root))
    async with local_api_db.client(user) as client:
        headers = {"X-Workspace-Id": workspace.id}
        rejected = await client.post(
            f"/api/v1/qa-memory/candidates/{candidate.key}/reject",
            headers=headers,
            json={"note": "not realistically reachable"},
        )
        confirm = await client.post(
            f"/api/v1/qa-memory/candidates/{candidate.key}/confirm",
            headers=headers,
            json={},
        )
    assert rejected.status_code == 200
    assert rejected.json()["candidate"]["status"] == "rejected"
    assert confirm.status_code == 409


@pytest.mark.asyncio
async def test_qa_memory_hidden_in_server_mode(
    local_api_db: ApiDb,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_QA_MEMORY_DIR", str(tmp_path / "memory"))
    user = await local_api_db.seed_user(email="server-memory@example.test")
    workspace = await local_api_db.member_workspace(user, slug="server-memory")
    monkeypatch.setenv("SUITEST_MODE", "server")
    monkeypatch.setenv("SUITEST_QA_MEMORY_DIR", str(tmp_path / "memory"))
    async with local_api_db.client(user) as client:
        response = await client.get(
            "/api/v1/qa-memory/candidates",
            headers={"X-Workspace-Id": workspace.id},
        )
    assert response.status_code == 404
