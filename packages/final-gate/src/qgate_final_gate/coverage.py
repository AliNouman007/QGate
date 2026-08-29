from __future__ import annotations

from qgate_browser_execution.models import ExecutionReport, ExecutionStatus, ScenarioExecution
from qgate_impact_analysis.models import ImpactReport
from qgate_qa_memory.models import MemoryRecallResult, RegressionScenarioHint
from qgate_scenario_intelligence.models import ScenarioPlan, ScenarioPriority

from .memory import build_historical_risks, historical_links_for_scenario
from .models import (
    CoverageItem,
    CoverageOutcome,
    CoverageSummary,
    EvidenceRef,
    HistoricalRisk,
)


def _execution_evidence_refs(execution: ScenarioExecution) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for step in execution.steps:
        for artifact in step.evidence.artifacts:
            refs.append(EvidenceRef(kind=artifact.kind, source=artifact.path, detail=artifact.sha256))
    return refs


def _required_base(
    priority: ScenarioPriority,
    source_impact_keys: list[str],
    impact: ImpactReport,
) -> tuple[bool, str | None]:
    if priority == ScenarioPriority.P0:
        return True, "P0 scenario is always required"
    if priority == ScenarioPriority.P1:
        return True, "P1 scenario is always required"
    direct_keys = {item.key for item in impact.direct_impacts}
    if priority == ScenarioPriority.P2 and direct_keys.intersection(source_impact_keys):
        return True, "P2 scenario is required because it covers direct current impact"
    return False, None


def build_coverage(
    plan: ScenarioPlan,
    execution_report: ExecutionReport,
    impact: ImpactReport,
    memory_recall: MemoryRecallResult | None,
    regression_hints: list[RegressionScenarioHint],
) -> tuple[list[CoverageItem], CoverageSummary, list[HistoricalRisk]]:
    executions = {item.scenario_key: item for item in execution_report.scenarios}
    verified_pass_keys = {
        item.scenario_key
        for item in execution_report.scenarios
        if item.status == ExecutionStatus.PASSED and item.verified
    }
    risks = build_historical_risks(plan, memory_recall, regression_hints, verified_pass_keys)

    items: list[CoverageItem] = []
    for scenario in plan.scenarios:
        required, required_reason = _required_base(
            scenario.priority,
            scenario.source_impact_keys,
            impact,
        )
        memory_keys, rule_keys = historical_links_for_scenario(scenario.key, risks)
        if rule_keys:
            required = True
            required_reason = (
                "Scenario is required by strongly matched confirmed historical regression risk"
            )

        execution = executions.get(scenario.key)
        status = execution.status if execution else None
        verified = execution.verified if execution else False
        failure_category = execution.failure_category if execution else None

        if execution and execution.status == ExecutionStatus.PASSED and execution.verified:
            outcome = CoverageOutcome.VERIFIED_PASS
        elif execution and execution.status == ExecutionStatus.FAILED and execution.verified:
            outcome = CoverageOutcome.VERIFIED_FAIL
        elif execution and execution.status == ExecutionStatus.SKIPPED_MANUAL:
            outcome = CoverageOutcome.MANUAL
        elif execution and execution.status == ExecutionStatus.BLOCKED:
            outcome = CoverageOutcome.BLOCKED
        elif required:
            outcome = CoverageOutcome.UNVERIFIED
        else:
            outcome = CoverageOutcome.OPTIONAL

        items.append(
            CoverageItem(
                scenario_key=scenario.key,
                title=scenario.title,
                priority=scenario.priority,
                required=required,
                required_reason=required_reason,
                readiness=scenario.readiness,
                execution_status=status.value if status else None,
                verified=verified,
                failure_category=failure_category,
                coverage_outcome=outcome,
                routes=scenario.routes,
                states=scenario.states,
                source_impact_keys=scenario.source_impact_keys,
                historical_memory_keys=memory_keys,
                historical_rule_keys=rule_keys,
                evidence_refs=_execution_evidence_refs(execution) if execution else [],
            )
        )

    summary = CoverageSummary()
    for item in items:
        if item.required:
            summary.required_total += 1
            if item.coverage_outcome == CoverageOutcome.VERIFIED_PASS:
                summary.required_verified_pass += 1
            elif item.coverage_outcome == CoverageOutcome.VERIFIED_FAIL:
                summary.required_verified_fail += 1
            elif item.coverage_outcome == CoverageOutcome.MANUAL:
                summary.required_manual += 1
            elif item.coverage_outcome == CoverageOutcome.BLOCKED:
                summary.required_blocked += 1
            else:
                summary.required_unverified += 1
        else:
            summary.optional_total += 1
            if item.coverage_outcome in {
                CoverageOutcome.VERIFIED_PASS,
                CoverageOutcome.VERIFIED_FAIL,
            }:
                summary.optional_verified += 1

    strong_risks = [risk for risk in risks if risk.strong_match]
    summary.historical_required_total = len(strong_risks)
    summary.historical_required_verified = sum(1 for risk in strong_risks if risk.covered)
    summary.has_coverage_gaps = bool(plan.coverage_gaps or execution_report.coverage_gaps)
    summary.truncated = any(
        "trunc" in gap.reason.casefold() or "budget" in gap.reason.casefold()
        for gap in plan.coverage_gaps
    ) or bool(memory_recall and memory_recall.coverage_gaps)
    return items, summary, risks
