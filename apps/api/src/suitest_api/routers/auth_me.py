"""``GET /auth/me`` — current user + memberships (docs/API.md §3.1).

User-scoped (NOT workspace-scoped): it answers "who am I and which workspaces can
I see", so it depends only on ``current_active_user`` + a DB session, never on
``require_workspace_membership``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from suitest_db.models.user import User
from suitest_db.repositories.workspaces import WorkspaceRepo

from suitest_api.auth.db import get_async_session
from suitest_api.auth.manager import (
    auth_backend,
    current_active_user,
    current_active_user_optional,
    get_jwt_strategy,
)
from suitest_api.schemas.workspace import (
    MembershipPublic,
    MeResponse,
    WorkspacePublic,
)
from suitest_api.settings import Settings

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/local-session", include_in_schema=False)
async def create_local_session(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    authenticated_user: User | None = Depends(current_active_user_optional),
) -> Response:
    """Issue a normal session cookie for a seeded local OWNER/ADMIN.

    The endpoint is deliberately indistinguishable from a missing route unless
    both local mode and the explicit bypass flag were accepted at startup.
    """
    settings: Settings = request.app.state.settings
    if not settings.local_auth_bypass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    membership = await WorkspaceRepo(session).get_local_admin_membership()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local auth bypass requires a seeded OWNER or ADMIN workspace membership",
        )
    response = (
        Response(status_code=status.HTTP_204_NO_CONTENT)
        if authenticated_user is not None and authenticated_user.id == membership.user_id
        else await auth_backend.login(get_jwt_strategy(), membership.user)
    )
    response.headers["X-Suitest-Workspace-Id"] = membership.workspace_id
    return response


@router.get("/auth/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> MeResponse:
    """Return the authenticated user plus every workspace membership they hold."""
    memberships = await WorkspaceRepo(session).list_memberships_for_user(user.id)
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        must_change_password=user.must_change_password,
        is_superuser=user.is_superuser,
        memberships=[
            MembershipPublic(
                workspace_id=m.workspace_id,
                role=m.role,
                workspace=WorkspacePublic.model_validate(m.workspace),
            )
            for m in memberships
        ],
    )
