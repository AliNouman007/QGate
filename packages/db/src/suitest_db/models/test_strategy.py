"""Versioned, auditable risk-based test strategies."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from suitest_shared.domain.enums import TestStrategyStatus

from suitest_db.base import Base, TimestampMixin
from suitest_db.ids import new_id
from suitest_db.types import PortableJSON


class TestStrategy(Base, TimestampMixin):
    __tablename__ = "test_strategies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TestStrategyStatus] = mapped_column(
        SAEnum(TestStrategyStatus, name="test_strategy_status"),
        default=TestStrategyStatus.DRAFT,
        nullable=False,
    )
    document: Mapped[dict[str, object]] = mapped_column(PortableJSON, nullable=False)
    agent_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_test_strategies_project_version"),
        Index("ix_test_strategies_project_status", "project_id", "status"),
        Index(
            "uq_test_strategies_project_approved",
            "project_id",
            unique=True,
            postgresql_where=(status == TestStrategyStatus.APPROVED),
        ),
    )
