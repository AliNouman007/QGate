from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExecutionReport


def render_execution_report(report: ExecutionReport) -> str:
    lines = [
        "Browser Execution & Evidence",
        f"Run: {report.metadata.run_id}",
        f"Scenario plan: {report.metadata.scenario_plan_key}",
        f"Selected: {report.summary.selected}",
        (
            "Results: "
            f"passed={report.summary.passed} failed={report.summary.failed} "
            f"errors={report.summary.execution_error} unverified={report.summary.unverified} "
            f"manual={report.summary.skipped_manual} blocked={report.summary.blocked}"
        ),
        "",
    ]
    for scenario in report.scenarios:
        suffix = f" ({scenario.failure_category.value})" if scenario.failure_category else ""
        lines.append(
            f"[{scenario.status.value.upper()}] {scenario.scenario_key} {scenario.title}{suffix}"
        )
        if scenario.target_route:
            lines.append(f"  route: {scenario.target_route}")
        if scenario.detail:
            lines.append(f"  detail: {scenario.detail}")
        for step in scenario.steps:
            detail = f" — {step.detail}" if step.detail else ""
            lines.append(
                f"  step {step.index}: {step.operation.value} -> {step.status.value}{detail}"
            )
    if report.coverage_gaps:
        lines.extend(["", "Coverage gaps:"])
        for gap in report.coverage_gaps:
            lines.append(f"- {gap.reason}: {gap.detail or ''}".rstrip())
    return "\n".join(lines)
