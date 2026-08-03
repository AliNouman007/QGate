"""Canonical result envelope for lifecycle and black-box MCP tools."""

from __future__ import annotations


def envelope(
    success: bool,
    summary: str,
    data: dict[str, object] | None = None,
    artifacts: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, object]:
    return {
        "success": success,
        "summary": summary,
        "data": data or {},
        "artifacts": artifacts or [],
        "errors": errors or [],
    }
