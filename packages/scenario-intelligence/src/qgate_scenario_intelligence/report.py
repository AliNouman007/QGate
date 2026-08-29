from __future__ import annotations

from .models import ScenarioPlan


def render_scenario_plan(plan: ScenarioPlan) -> str:
    lines = [
        "QGate Scenario Plan",
        f"Project: {plan.metadata.project_source_id}",
        f"Change: {plan.metadata.impact_change_source_id}",
        f"Scenarios: {plan.summary.total} | READY: {plan.summary.ready} | Runtime discovery: {plan.summary.runtime_discovery}",
        "",
    ]
    for scenario in plan.scenarios:
        target = ", ".join(scenario.routes or scenario.targets) or "runtime discovery"
        lines.extend(
            [
                f"[{scenario.priority}] {scenario.title}",
                f"  Kind: {scenario.kind.value} | Readiness: {scenario.readiness.value} | Confidence: {scenario.confidence.value}",
                f"  Target: {target}",
                f"  Why: {scenario.reason}",
            ]
        )
        for step in scenario.steps:
            lines.append(f"  - {step.action}")
            lines.append(f"    Expect: {step.expected}")
        if scenario.needs_runtime_discovery:
            lines.append("  Runtime discovery required")
        lines.append("")
    if plan.coverage_gaps:
        lines.append("Coverage gaps:")
        for gap in plan.coverage_gaps:
            lines.append(f"- {gap.reason}: {gap.detail or ''}".rstrip())
    return "\n".join(lines).rstrip() + "\n"
