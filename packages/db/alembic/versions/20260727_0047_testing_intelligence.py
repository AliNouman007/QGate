"""Testing approaches and versioned risk-based strategies.

Revision ID: 0047_testing_intelligence
Revises: 0046_case_stale_slug_guard
Create Date: 2026-07-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047_testing_intelligence"
down_revision: str | None = "0046_case_stale_slug_guard"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    approach = postgresql.ENUM(
        "BLACK_BOX",
        "GRAY_BOX",
        "WHITE_BOX",
        name="testing_approach",
        create_type=False,
    )
    level = postgresql.ENUM(
        "UNIT",
        "COMPONENT",
        "INTEGRATION",
        "SYSTEM",
        "E2E",
        name="test_level",
        create_type=False,
    )
    strategy_status = postgresql.ENUM(
        "DRAFT",
        "APPROVED",
        "SUPERSEDED",
        name="test_strategy_status",
        create_type=False,
    )
    bind = op.get_bind()
    postgresql.ENUM("BLACK_BOX", "GRAY_BOX", "WHITE_BOX", name="testing_approach").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("UNIT", "COMPONENT", "INTEGRATION", "SYSTEM", "E2E", name="test_level").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("DRAFT", "APPROVED", "SUPERSEDED", name="test_strategy_status").create(
        bind, checkfirst=True
    )

    op.create_table(
        "test_strategies",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("workspace_id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", strategy_status, nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("agent_session_id", sa.String(length=32), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *[
            sa.Column(
                name,
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            )
            for name in ("created_at", "updated_at")
        ],
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_session_id"], ["agent_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version", name="uq_test_strategies_project_version"),
    )
    op.create_index(
        "ix_test_strategies_project_status",
        "test_strategies",
        ["project_id", "status"],
    )
    op.create_index(
        "uq_test_strategies_project_approved",
        "test_strategies",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPROVED'"),
    )
    op.add_column("suites", sa.Column("default_testing_approach", approach, nullable=True))
    op.add_column("test_cases", sa.Column("testing_approach", approach, nullable=True))
    op.add_column("test_cases", sa.Column("test_level", level, nullable=True))
    op.add_column("test_cases", sa.Column("framework", sa.String(length=64), nullable=True))
    op.add_column("test_cases", sa.Column("strategy_id", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        "fk_test_cases_strategy_id",
        "test_cases",
        "test_strategies",
        ["strategy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_test_cases_testing_approach", "test_cases", ["testing_approach"])
    op.create_index("ix_test_cases_strategy_id", "test_cases", ["strategy_id"])


def downgrade() -> None:
    op.drop_index("ix_test_cases_strategy_id", table_name="test_cases")
    op.drop_index("ix_test_cases_testing_approach", table_name="test_cases")
    op.drop_constraint("fk_test_cases_strategy_id", "test_cases", type_="foreignkey")
    op.drop_column("test_cases", "strategy_id")
    op.drop_column("test_cases", "framework")
    op.drop_column("test_cases", "test_level")
    op.drop_column("test_cases", "testing_approach")
    op.drop_column("suites", "default_testing_approach")
    op.drop_index("uq_test_strategies_project_approved", table_name="test_strategies")
    op.drop_index("ix_test_strategies_project_status", table_name="test_strategies")
    op.drop_table("test_strategies")
    bind = op.get_bind()
    sa.Enum(name="test_strategy_status").drop(bind, checkfirst=True)
    sa.Enum(name="test_level").drop(bind, checkfirst=True)
    sa.Enum(name="testing_approach").drop(bind, checkfirst=True)
