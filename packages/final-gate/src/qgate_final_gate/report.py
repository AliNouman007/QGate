from __future__ import annotations

from .models import GateReport, GateVerdict


def render_gate_report(report: GateReport) -> str:
    lines = [report.headline]
    summary = report.coverage_summary
    lines.append(
        "Required coverage: "
        f"{summary.required_verified_pass}/{summary.required_total} passed, "
        f"{summary.required_verified_fail} failed, "
        f"{summary.required_unverified + summary.required_manual + summary.required_blocked} unresolved"
    )
    if report.blocking_findings:
        lines.append("Blocking findings:")
        lines.extend(f"- {item.title}: {item.reason}" for item in report.blocking_findings)
    if report.manual_review_findings:
        lines.append("Manual review:")
        lines.extend(f"- {item.title}: {item.reason}" for item in report.manual_review_findings)
    strong_risks = [risk for risk in report.historical_risks if risk.strong_match]
    if strong_risks:
        lines.append("Historical regression obligations:")
        lines.extend(
            f"- {risk.rule_key or risk.memory_key}: {'covered' if risk.covered else 'unverified'}"
            for risk in strong_risks
        )
    if report.verdict == GateVerdict.PASS:
        lines.append("Gate decision: ready to proceed to the next QA step.")
    elif report.verdict == GateVerdict.BLOCK:
        lines.append("Gate decision: stop; a verified product failure must be addressed.")
    else:
        lines.append("Gate decision: do not treat as PASS; human verification is required.")
    return "\n".join(lines)
