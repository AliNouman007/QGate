"""Shared project-to-workspace ownership check for API services."""

from __future__ import annotations

from suitest_db.repositories.projects import ProjectRepo


async def project_belongs_to_workspace(
    repo: ProjectRepo, project_id: str, workspace_id: str
) -> bool:
    project = await repo.get_by_id(project_id)
    return project is not None and project.workspace_id == workspace_id
