from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .models import GateAIExplanation, GateReport


class GateEvidencePack(BaseModel):
    verdict: str
    headline: str
    fired_rule_ids: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    manual_reasons: list[str] = Field(default_factory=list)
    required_coverage: list[str] = Field(default_factory=list)
    historical_risks: list[str] = Field(default_factory=list)


class GateExplanationProvider(Protocol):
    def explain(self, pack: GateEvidencePack) -> GateAIExplanation | None: ...


def build_evidence_pack(report: GateReport, *, max_items: int = 12) -> GateEvidencePack:
    required = [
        f"{item.scenario_key}:{item.coverage_outcome.value}"
        for item in report.coverage_items
        if item.required
    ][:max_items]
    history = [
        f"{risk.rule_key or risk.memory_key}:{'covered' if risk.covered else 'unverified'}"
        for risk in report.historical_risks
        if risk.strong_match
    ][:max_items]
    return GateEvidencePack(
        verdict=report.verdict.value,
        headline=report.headline,
        fired_rule_ids=[item.rule_id for item in report.decision_trace][:max_items],
        blocking_reasons=[item.reason for item in report.blocking_findings][:max_items],
        manual_reasons=[item.reason for item in report.manual_review_findings][:max_items],
        required_coverage=required,
        historical_risks=history,
    )


def enrich_with_ai_explanation(
    report: GateReport,
    provider: GateExplanationProvider | None,
) -> GateReport:
    if provider is None:
        return report
    try:
        explanation = provider.explain(build_evidence_pack(report))
    except Exception:
        return report
    if explanation is None:
        return report
    updated = report.model_copy(deep=True)
    updated.ai_explanation = explanation
    return updated
