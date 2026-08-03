"""Repository for versioned project test strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy import func, select
from suitest_db.models.project import Project
from suitest_db.models.test_strategy import TestStrategy
from suitest_shared.domain.enums import TestStrategyStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestStrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_project(self, project_id: str) -> None:
        """Serialize project-scoped strategy state transitions in this transaction."""
        await self.session.execute(
            select(Project.id).where(Project.id == project_id).with_for_update()
        )

    async def next_version(self, project_id: str) -> int:
        await self.lock_project(project_id)
        current = await self.session.scalar(
            select(func.max(TestStrategy.version)).where(TestStrategy.project_id == project_id)
        )
        return int(current or 0) + 1

    async def list_for_project(self, project_id: str) -> list[TestStrategy]:
        return list(
            (
                await self.session.scalars(
                    select(TestStrategy)
                    .where(TestStrategy.project_id == project_id)
                    .order_by(TestStrategy.version.desc())
                )
            ).all()
        )

    async def get(self, strategy_id: str) -> TestStrategy | None:
        return await self.session.get(TestStrategy, strategy_id)

    async def approved_for_project(self, project_id: str) -> TestStrategy | None:
        return cast(
            "TestStrategy | None",
            await self.session.scalar(
                select(TestStrategy)
                .where(
                    TestStrategy.project_id == project_id,
                    TestStrategy.status == TestStrategyStatus.APPROVED,
                )
                .order_by(TestStrategy.version.desc())
            ),
        )
