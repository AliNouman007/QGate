"""Local-only session bootstrap for development without a login prompt."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from api_harness import ApiDb
from sqlalchemy.ext.asyncio import async_sessionmaker
from suitest_api.auth.manager import get_jwt_strategy
from suitest_db.bootstrap import create_local_schema
from suitest_db.engine import make_engine
from suitest_db.settings import DbSettings
from suitest_shared.domain.enums import Role


@pytest_asyncio.fixture
async def local_api_db(tmp_path: Path) -> AsyncIterator[ApiDb]:
    """Real SQLite API harness so local-mode auth never depends on Docker."""
    settings = DbSettings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}")
    engine = make_engine(settings)
    await create_local_schema(engine)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield ApiDb(maker=maker)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_local_auth_bypass_issues_real_owner_session(
    local_api_db: ApiDb, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing the local-session route or its cookie issuance must fail this test."""
    admin = await local_api_db.seed_user(email="admin-local@example.test", name="Local Admin")
    owner = await local_api_db.seed_user(email="owner-local@example.test", name="Local Owner")
    admin_ws = await local_api_db.seed_workspace(slug="admin-local", name="Admin Local")
    owner_ws = await local_api_db.seed_workspace(slug="owner-local", name="Owner Local")
    await local_api_db.seed_membership(workspace_id=admin_ws.id, user_id=admin.id, role=Role.ADMIN)
    await local_api_db.seed_membership(workspace_id=owner_ws.id, user_id=owner.id, role=Role.OWNER)
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_LOCAL_AUTH_BYPASS", "true")

    async with local_api_db.client(None) as client:
        response = await client.post("/api/v1/auth/local-session")
        me = await client.get("/api/v1/auth/me")
        repeated = await client.post("/api/v1/auth/local-session")

    assert response.status_code == 204
    assert "suitest_session" in response.cookies
    assert response.headers["X-Suitest-Workspace-Id"] == owner_ws.id
    assert repeated.headers["X-Suitest-Workspace-Id"] == owner_ws.id
    assert me.status_code == 200
    assert me.json()["email"] == "owner-local@example.test"
    assert me.json()["memberships"][0]["workspace_id"] == owner_ws.id


@pytest.mark.asyncio
async def test_local_auth_bypass_disabled_preserves_unauthenticated_behavior(
    local_api_db: ApiDb, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enabling code must not change the default login requirement."""
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_LOCAL_AUTH_BYPASS", "false")

    async with local_api_db.client(None) as client:
        local_session = await client.post("/api/v1/auth/local-session")
        me = await client.get("/api/v1/auth/me")

    assert local_session.status_code == 404
    assert "suitest_session" not in local_session.cookies
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_local_auth_bypass_requires_seeded_admin_membership(
    local_api_db: ApiDb, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A random active user without an admin workspace must never gain a session."""
    await local_api_db.seed_user(email="unscoped-local@example.test")
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_LOCAL_AUTH_BYPASS", "true")

    async with local_api_db.client(None) as client:
        response = await client.post("/api/v1/auth/local-session")

    assert response.status_code == 503
    assert "suitest_session" not in response.cookies


@pytest.mark.asyncio
async def test_local_auth_bypass_replaces_existing_non_admin_session(
    local_api_db: ApiDb, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale local cookie must not prevent selection of the default admin."""
    stale_user = await local_api_db.seed_user(email="stale-local@example.test")
    owner = await local_api_db.seed_user(email="default-owner@example.test")
    workspace = await local_api_db.seed_workspace(slug="default-owner", name="Default Owner")
    await local_api_db.seed_membership(workspace_id=workspace.id, user_id=owner.id, role=Role.OWNER)
    stale_token = await get_jwt_strategy().write_token(stale_user)
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_LOCAL_AUTH_BYPASS", "true")

    async with local_api_db.client(None) as client:
        client.cookies.set("suitest_session", stale_token)
        response = await client.post("/api/v1/auth/local-session")
        me = await client.get("/api/v1/auth/me")

    assert response.status_code == 204
    assert response.headers["X-Suitest-Workspace-Id"] == workspace.id
    assert me.json()["email"] == "default-owner@example.test"


@pytest.mark.asyncio
async def test_local_auth_bypass_skips_password_change_blocked_owner(
    local_api_db: ApiDb, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bypass must not land on the mandatory password-change screen."""
    forced_owner = await local_api_db.seed_user(email="forced-owner@example.test")
    ready_admin = await local_api_db.seed_user(email="ready-admin@example.test")
    owner_ws = await local_api_db.seed_workspace(slug="forced-owner", name="Forced Owner")
    admin_ws = await local_api_db.seed_workspace(slug="ready-admin", name="Ready Admin")
    await local_api_db.seed_membership(
        workspace_id=owner_ws.id, user_id=forced_owner.id, role=Role.OWNER
    )
    await local_api_db.seed_membership(
        workspace_id=admin_ws.id, user_id=ready_admin.id, role=Role.ADMIN
    )
    async with local_api_db.maker() as session:
        row = await session.get(type(forced_owner), forced_owner.id)
        assert row is not None
        row.must_change_password = True
        await session.commit()
    monkeypatch.setenv("SUITEST_MODE", "local")
    monkeypatch.setenv("SUITEST_LOCAL_AUTH_BYPASS", "true")

    async with local_api_db.client(None) as client:
        response = await client.post("/api/v1/auth/local-session")
        me = await client.get("/api/v1/auth/me")

    assert response.status_code == 204
    assert response.headers["X-Suitest-Workspace-Id"] == admin_ws.id
    assert me.json()["email"] == "ready-admin@example.test"
    assert me.json()["must_change_password"] is False
