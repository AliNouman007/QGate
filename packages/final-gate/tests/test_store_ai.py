from pathlib import Path

from qgate_final_gate.ai import enrich_with_ai_explanation
from qgate_final_gate.models import (
    CoverageSummary,
    GateAIExplanation,
    GateConfidence,
    GateMetadata,
    GateReport,
    GateVerdict,
)
from qgate_final_gate.store import JsonGateReportStore


def _report(verdict: GateVerdict = GateVerdict.BLOCK) -> GateReport:
    return GateReport(
        metadata=GateMetadata(
            report_key="gate_1234567890abcdef1234",
            project_source_id="local:/shop",
            project_fingerprint="fp",
            change_source_id="change:1",
            scenario_plan_key="plan:1",
            execution_run_id="run:1",
        ),
        verdict=verdict,
        confidence=GateConfidence.HIGH,
        headline=f"{verdict.value} — deterministic",
        coverage_summary=CoverageSummary(required_total=1),
    )


class FakeProvider:
    def explain(self, _pack: object) -> GateAIExplanation:
        return GateAIExplanation(summary="AI would prefer PASS")


def test_ai_explanation_cannot_change_deterministic_verdict() -> None:
    enriched = enrich_with_ai_explanation(_report(), FakeProvider())
    assert enriched.verdict == GateVerdict.BLOCK
    assert enriched.confidence == GateConfidence.HIGH
    assert enriched.ai_explanation is not None
    assert enriched.ai_explanation.summary == "AI would prefer PASS"


def test_report_store_round_trip_and_rejects_traversal_key(tmp_path: Path) -> None:
    store = JsonGateReportStore(tmp_path)
    report = _report(GateVerdict.PASS)
    store.save(report)
    assert store.load_key(report.metadata.report_key) == report
    assert store.load_key("../../etc/passwd") is None
    assert store.latest() == report
