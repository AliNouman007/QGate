from __future__ import annotations

from collections import Counter

from .models import FileRole, ProjectKnowledge


def render_project_map(knowledge: ProjectKnowledge) -> str:
    summary = knowledge.summary
    lines = [
        "QGate Project Map",
        f"Source: {knowledge.metadata.source_id}",
        f"Fingerprint: {knowledge.metadata.source_fingerprint[:12]}",
        f"Files: {summary.total_files} | Bytes: {summary.total_source_bytes}",
        f"Languages: {_format_counts(summary.languages)}",
        f"Roles: {_format_counts(summary.roles)}",
    ]

    routes = [file.record.path for file in knowledge.files if file.record.role == FileRole.ROUTE]
    components = [
        file.record.path for file in knowledge.files if file.record.role == FileRole.COMPONENT
    ]
    lines.append(f"Routes/pages: {len(routes)}")
    lines.extend(f"  - {path}" for path in routes[:20])
    lines.append(f"Components: {len(components)}")
    lines.extend(f"  - {path}" for path in components[:20])

    lines.append(f"Behavioral states/signals: {_format_counts(summary.behavioral_categories)}")
    if summary.reused_modules:
        lines.append("Shared/reused modules:")
        for path, count in list(summary.reused_modules.items())[:20]:
            lines.append(f"  - {path}: {count} importers")

    meaningful = [
        behavior for file in knowledge.files for behavior in file.behaviors if behavior.meaningful
    ]
    if meaningful:
        lines.append("Evidence-backed behavioral facts:")
        for fact in meaningful[:30]:
            lines.append(
                f"  - [{fact.category.value}/{fact.confidence.value}] "
                f"{fact.evidence.path}:{fact.evidence.line} {fact.expression[:100]}"
            )

    if knowledge.coverage_gaps:
        lines.append(f"Coverage gaps: {len(knowledge.coverage_gaps)}")
        reason_counts = Counter(gap.reason for gap in knowledge.coverage_gaps)
        for reason, count in sorted(reason_counts.items()):
            lines.append(f"  - {reason}: {count}")
    else:
        lines.append("Coverage gaps: 0")

    return "\n".join(lines)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none detected"
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
