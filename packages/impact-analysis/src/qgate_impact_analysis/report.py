from __future__ import annotations

from .models import ImpactItem, ImpactReport


def render_impact_report(report: ImpactReport) -> str:
    lines = [
        "QGate Impact Report",
        f"Change: {report.metadata.change_source_id}",
        f"Project fingerprint: {report.metadata.project_fingerprint[:12]}",
        (
            "Summary: "
            f"changed_files={report.summary.changed_files}, "
            f"direct={report.summary.direct_impacts}, "
            f"indirect={report.summary.indirect_impacts}, "
            f"routes={report.summary.affected_routes}, "
            f"states={report.summary.affected_states}, "
            f"runtime_verify={report.summary.runtime_verification_items}"
        ),
    ]
    _append_section(lines, "Direct impact", report.direct_impacts)
    _append_section(lines, "Indirect/shared blast radius", report.indirect_impacts)
    _append_section(lines, "Affected routes", report.affected_routes)
    _append_section(lines, "Affected states", report.affected_states)
    _append_section(lines, "Possible impact", report.possible_impacts)
    _append_section(lines, "Unknown impact", report.unknown_impacts)
    if report.shared_groups:
        lines.append("Shared/reused groups:")
        for group in report.shared_groups:
            lines.append(
                f"  - {group.changed_target}: {group.reuse_count} known importers; "
                f"routes={', '.join(group.affected_routes) or 'none'}"
            )
    if report.coverage_gaps:
        lines.append("Coverage gaps / manual attention:")
        for gap in report.coverage_gaps:
            target = f"{gap.path}: " if gap.path else ""
            lines.append(f"  - {target}{gap.reason}{' — ' + gap.detail if gap.detail else ''}")
    return "\n".join(lines)


def _append_section(lines: list[str], heading: str, items: list[ImpactItem]) -> None:
    if not items:
        return
    lines.append(f"{heading}:")
    for item in items[:80]:
        runtime = " [runtime verification]" if item.needs_runtime_verification else ""
        lines.append(
            f"  - [{item.level.value}/{item.confidence.value}] {item.target} — {item.reason}{runtime}"
        )
