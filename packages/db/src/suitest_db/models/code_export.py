"""CodeExport — exported test code (docs/DATA_MODEL.md §4.7)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from suitest_db.base import Base
from suitest_db.ids import new_id
from suitest_db.types import UserGUID


class CodeExport(Base):
    __tablename__ = "code_exports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    target: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # playwright | cypress | selenium
    exported_code_text: Mapped[str] = mapped_column(Text, nullable=False)
    exported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UserGUID, ForeignKey("users.id"))

    __table_args__ = (Index("ix_code_exports_case_target", "case_id", "target"),)
