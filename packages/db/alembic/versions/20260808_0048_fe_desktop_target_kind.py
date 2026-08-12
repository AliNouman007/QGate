"""Add FE_DESKTOP to the target_kind enum (M14 desktop testing).

Revision ID: 0048_fe_desktop_target_kind
Revises: 0047_testing_intelligence
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0048_fe_desktop_target_kind"
down_revision: str | None = "0047_testing_intelligence"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    bind = op.get_bind()
    # Only Postgres stores target_kind as a real ENUM type; add the new value
    # there. SQLite represents enums as VARCHAR CHECK constraints, so the value
    # is picked up automatically from the application enum — nothing to alter.
    if bind.dialect.name == "postgresql":
        try:
            op.execute("ALTER TYPE target_kind ADD VALUE IF NOT EXISTS 'FE_DESKTOP'")
        except sa.exc.DBAPIError:  # pragma: no cover - defensive for < PG 9.6
            op.execute("ALTER TYPE target_kind ADD VALUE 'FE_DESKTOP'")


def downgrade() -> None:
    # PostgreSQL cannot remove a value from an enum type without a data-migration
    # dance (recreate the type + drop/reassign any rows referencing it). Desktop
    # steps require no schema rollback beyond the app-level enum — leave the
    # type untouched so existing rows with FE_DESKTOP never orphan.
    pass
