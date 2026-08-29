"""Workspace repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel
from sqlalchemy import case, exists, select
from sqlalchemy.orm import selectinload
from suitest_db.models.project import Project
from suitest_db.models.tenancy import Membership
from suitest_db.models.user import User
from suitest_db.models.workspace import Workspace
from suitest_db.repositories.base import AsyncRepository
from suitest_shared.domain.enums import Role

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from sqlalchemy.sql.elements import ColumnElement


class WorkspaceCreate(BaseModel):
    slug: str
    name: str
    region: str = "ap-southeast-1"


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    strict_zero_validation: bool | None = None
    mcp_routing_overrides: dict[str, Any] | None = None


class WorkspaceRepo(AsyncRepository[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Workspace]:
        # Only active (non-tombstoned) workspaces — DELETE /workspaces/:id sets
        # ``deleted_at`` and we hide the row from list/detail immediately so the
        # FE Danger Zone confirm leaves no zombie entry visible while the async
        # ``workspace_cleanup`` ARQ job tears down children.
        stmt = (
            select(Workspace)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user_id, Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at.desc(), Workspace.id.desc())
        )
        return (await self.session.scalars(stmt)).all()

    async def mark_deleted(self, workspace_id: str) -> Workspace | None:
        """Set ``deleted_at = now()`` and return the row (or ``None`` if missing).

        The actual children-cleanup is performed asynchronously by the
        ``workspace_cleanup`` ARQ job (see ``apps/runner/.../workspace_cleanup.py``).
        Tombstoning here only flips visibility — caller is responsible for
        enqueueing the job and committing the surrounding transaction.
        """
        row = await self.get_by_id(workspace_id)
        if row is None:
            return None
        row.deleted_at = datetime.now(tz=UTC)
        await self.session.flush()
        return row

    async def get_by_slug(self, slug: str) -> Workspace | None:
        result: Workspace | None = await self.session.scalar(
            select(Workspace).where(Workspace.slug == slug)
        )
        return result

    async def list_memberships_for_user(self, user_id: uuid.UUID) -> Sequence[Membership]:
        """Memberships for a user with the parent ``workspace`` eager-loaded.

        Powers ``GET /auth/me`` — one query, no N+1 to fetch each workspace.
        """
        stmt = (
            select(Membership)
            .where(Membership.user_id == user_id)
            .options(selectinload(Membership.workspace))
            .order_by(Membership.created_at.asc(), Membership.id.asc())
        )
        return (await self.session.scalars(stmt)).all()

    async def list_members(self, workspace_id: str) -> Sequence[Membership]:
        """Memberships in a workspace with the ``user`` eager-loaded.

        Powers ``GET /workspaces/:id/members`` — one query, no N+1.
        """
        stmt = (
            select(Membership)
            .where(Membership.workspace_id == workspace_id)
            .options(selectinload(Membership.user))
            .order_by(Membership.created_at.asc(), Membership.id.asc())
        )
        return (await self.session.scalars(stmt)).all()

    async def get_local_admin_membership(self) -> Membership | None:
        """Return the deterministic local OWNER/ADMIN membership for dev sessions.

        The full local seed creates Maya as an OWNER of Nusantara Retail. A
        different local seed remains supported: OWNER wins over ADMIN, then a
        workspace with a project wins over an empty workspace. Users without an
        active workspace membership are never eligible.
        """
        role_priority = case((Membership.role == Role.OWNER, 0), else_=1)
        project_priority = case(
            (
                exists(select(Project.id).where(Project.workspace_id == Membership.workspace_id)),
                0,
            ),
            else_=1,
        )
        stmt = (
            select(Membership)
            .join(User, Membership.user_id == User.id)
            .join(Workspace, Workspace.id == Membership.workspace_id)
            .where(
                cast("ColumnElement[bool]", User.is_active).is_(True),
                User.must_change_password.is_(False),
                Workspace.deleted_at.is_(None),
                Membership.role.in_((Role.OWNER, Role.ADMIN)),
            )
            .options(selectinload(Membership.user))
            .order_by(
                role_priority.asc(),
                project_priority.asc(),
                Membership.created_at.asc(),
                Membership.id.asc(),
            )
            .limit(1)
        )
        return cast("Membership | None", await self.session.scalar(stmt))
