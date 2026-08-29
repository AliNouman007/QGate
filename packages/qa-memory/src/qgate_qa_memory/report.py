from __future__ import annotations

from .models import MemoryRecallResult


def render_recall(result: MemoryRecallResult) -> str:
    lines = [
        f"QA Memory Recall: {result.project_source_id}",
        f"Impact: {result.impact_change_source_id}",
        f"Memories: {len(result.matched_memories)} | Rules: {len(result.matched_rules)}",
    ]
    for match in result.matched_memories:
        lines.append(f"- memory {match.memory_key} score={match.score}: {', '.join(match.reasons)}")
    for match in result.matched_rules:
        lines.append(f"- rule {match.rule_key} score={match.score}: {', '.join(match.reasons)}")
    for gap in result.coverage_gaps:
        lines.append(f"GAP {gap.reason}: {gap.detail or ''}".rstrip())
    return "\n".join(lines)
