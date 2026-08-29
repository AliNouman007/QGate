from __future__ import annotations

import hashlib

from qgate_browser_execution.models import ExecutionStatus, FailureCategory
from qgate_scenario_intelligence.models import AutomationReadiness

from .coverage import build_coverage
from .integrity import validate_input_integrity
from .models import (
    CoverageItem,
    CoverageOutcome,
    DecisionTraceEntry,
    GateConfidence,
    GateFinding,
    GateInputBundle,
    GateMetadata,
    GateReasonKind,
    GateReport,
    GateVerdict,
    HistoricalRisk,
    VerdictEffect,
)

_MANUAL_FAILURE_KINDS: dict[FailureCategory, GateReasonKind] = {
    FailureCategory.ENVIRONMENT_FAILURE: GateReasonKind.ENVIRONMENT_OR_SETUP_GAP,
    FailureCategory.BROWSER_FAILURE: GateReasonKind.ENVIRONMENT_OR_SETUP_GAP,
    FailureCategory.NETWORK_INFRA_FAILURE: GateReasonKind.ENVIRONMENT_OR_SETUP_GAP,
    FailureCategory.STATE_SETUP_FAILURE: GateReasonKind.ENVIRONMENT_OR_SETUP_GAP,
    FailureCategory.TARGET_RESOLUTION_FAILURE: GateReasonKind.TARGET_RESOLUTION_GAP,
    FailureCategory.TEST_DEFINITION_ERROR: GateReasonKind.TEST_DEFINITION_GAP,
    FailureCategory.TIMEOUT: GateReasonKind.TIMEOUT_UNRESOLVED,
    FailureCategory.UNKNOWN_EXECUTION_FAILURE: GateReasonKind.REQUIRED_SCENARIO_UNVERIFIED,
    FailureCategory.NAVIGATION_FAILURE: GateReasonKind.REQUIRED_SCENARIO_UNVERIFIED,
}


class FinalGateJudge:
    def evaluate(self, bundle: GateInputBundle) -> GateReport:
        integrity = validate_input_integrity(bundle)
        metadata = self._metadata(bundle)
        if integrity:
            findings = [
                GateFinding(
                    key=self._finding_key("integrity", str(index), item.reason),
                    kind=GateReasonKind.INPUT_INTEGRITY_GAP,
                    title="Artifact chain is inconsistent",
                    reason=item.reason,
                    verdict_effect=VerdictEffect.MANUAL_REVIEW,
                )
                for index, item in enumerate(integrity)
            ]
            return GateReport(
                metadata=metadata,
                verdict=GateVerdict.MANUAL_REVIEW_REQUIRED,
                confidence=GateConfidence.HIGH,
                headline="MANUAL REVIEW REQUIRED — QGate artifacts are stale or mismatched",
                manual_review_findings=findings,
                input_integrity_findings=integrity,
                decision_trace=[
                    DecisionTraceEntry(
                        rule_id="FG-INTEGRITY-FAIL-CLOSED",
                        reason=(
                            "Input artifact identity validation failed, so current execution "
                            "evidence is not trusted for PASS/BLOCK."
                        ),
                    )
                ],
            )

        coverage, summary, risks = build_coverage(
            bundle.scenario_plan,
            bundle.execution,
            bundle.impact,
            bundle.memory_recall,
            bundle.regression_hints,
        )
        conflicting = self._conflicting_required_scenarios(bundle, coverage)
        blocking = self._blocking_findings(bundle, coverage, conflicting)
        manual = self._manual_findings(bundle, coverage)
        manual.extend(self._conflict_findings(conflicting))
        informational: list[GateFinding] = []
        trace = [
            DecisionTraceEntry(
                rule_id="FG-INTEGRITY-VALID",
                reason=(
                    "Project, impact, scenario, execution and supplied memory artifacts belong "
                    "to the same evidence chain."
                ),
            )
        ]

        if summary.truncated:
            manual.append(
                GateFinding(
                    key=self._finding_key("coverage", "truncated", metadata.change_source_id),
                    kind=GateReasonKind.COVERAGE_TRUNCATED,
                    title="Required coverage may be truncated",
                    reason=(
                        "One or more scenario/memory generation budgets truncated evidence that "
                        "could affect required coverage."
                    ),
                    verdict_effect=VerdictEffect.MANUAL_REVIEW,
                )
            )

        for risk in risks:
            if risk.strong_match and not risk.covered:
                manual.append(self._historical_manual_finding(risk))

        if blocking:
            verdict = GateVerdict.BLOCK
            confidence = GateConfidence.HIGH
            headline = self._block_headline(blocking[0])
            trace.append(
                DecisionTraceEntry(
                    rule_id="FG-BLOCK-VERIFIED-PRODUCT",
                    reason="At least one relevant non-conflicting verified product assertion failed.",
                    scenario_key=blocking[0].scenario_key,
                    finding_key=blocking[0].key,
                )
            )
        else:
            if summary.required_total == 0:
                manual.append(
                    GateFinding(
                        key=self._finding_key("coverage", "none", metadata.change_source_id),
                        kind=GateReasonKind.NO_REQUIRED_COVERAGE,
                        title="No required browser/product coverage",
                        reason=(
                            "This meaningful change has no required evaluable scenario coverage, "
                            "so QGate cannot justify PASS."
                        ),
                        verdict_effect=VerdictEffect.MANUAL_REVIEW,
                    )
                )
            if manual:
                verdict = GateVerdict.MANUAL_REVIEW_REQUIRED
                confidence = self._manual_confidence(manual)
                headline = f"MANUAL REVIEW REQUIRED — {manual[0].reason}"
                trace.append(
                    DecisionTraceEntry(
                        rule_id="FG-MANUAL-REQUIRED-GAP",
                        reason=(
                            "No trusted verified product blocker exists, but required evidence is "
                            "incomplete, conflicting, ambiguous, or manual-only."
                        ),
                        scenario_key=manual[0].scenario_key,
                        finding_key=manual[0].key,
                    )
                )
            else:
                verdict = GateVerdict.PASS
                confidence = GateConfidence.HIGH
                headline = (
                    f"PASS — all {summary.required_total} required scenarios verified with no "
                    "blocking product failures"
                )
                informational.append(
                    GateFinding(
                        key=self._finding_key("coverage", "pass", metadata.change_source_id),
                        kind=GateReasonKind.ALL_REQUIRED_COVERAGE_VERIFIED,
                        title="All required coverage verified",
                        reason=headline.removeprefix("PASS — "),
                        verdict_effect=VerdictEffect.INFORMATIONAL,
                        verified=True,
                    )
                )
                trace.append(
                    DecisionTraceEntry(
                        rule_id="FG-PASS-ALL-REQUIRED",
                        reason=(
                            "All required scenarios are verified PASS, strong historical regression "
                            "obligations are covered, and no material gap remains."
                        ),
                    )
                )

        return GateReport(
            metadata=metadata,
            verdict=verdict,
            confidence=confidence,
            headline=headline,
            blocking_findings=blocking,
            manual_review_findings=self._dedupe_findings(manual),
            informational_findings=informational,
            coverage_summary=summary,
            coverage_items=coverage,
            historical_risks=risks,
            evidence_refs=[ref for item in coverage for ref in item.evidence_refs],
            decision_trace=trace,
        )

    def _blocking_findings(
        self,
        bundle: GateInputBundle,
        coverage: list[CoverageItem],
        conflicting_scenarios: set[str],
    ) -> list[GateFinding]:
        executions = {item.scenario_key: item for item in bundle.execution.scenarios}
        findings: list[GateFinding] = []
        for item in coverage:
            if item.scenario_key in conflicting_scenarios:
                continue
            if item.coverage_outcome != CoverageOutcome.VERIFIED_FAIL:
                continue
            execution = executions.get(item.scenario_key)
            if execution is None or not execution.verified:
                continue
            if execution.failure_category != FailureCategory.ASSERTION_FAILURE:
                continue
            if not item.required:
                continue
            failing_steps = [
                step
                for step in execution.steps
                if step.status == ExecutionStatus.FAILED
                and step.failure_category == FailureCategory.ASSERTION_FAILURE
            ]
            reason = execution.detail or (
                failing_steps[0].detail
                if failing_steps and failing_steps[0].detail
                else "Verified product assertion failed"
            )
            findings.append(
                GateFinding(
                    key=self._finding_key("block", item.scenario_key, reason),
                    kind=GateReasonKind.VERIFIED_PRODUCT_FAILURE,
                    title=item.title,
                    reason=reason,
                    verdict_effect=VerdictEffect.BLOCKING,
                    priority=item.priority,
                    scenario_key=item.scenario_key,
                    routes=item.routes,
                    states=item.states,
                    verified=True,
                    product_facing=True,
                    failure_category=execution.failure_category,
                    execution_run_id=bundle.execution.metadata.run_id,
                    execution_step_indexes=[step.index for step in failing_steps],
                    source_memory_keys=item.historical_memory_keys,
                    source_rule_keys=item.historical_rule_keys,
                    evidence_refs=item.evidence_refs,
                )
            )
        return findings

    def _manual_findings(
        self,
        bundle: GateInputBundle,
        coverage: list[CoverageItem],
    ) -> list[GateFinding]:
        findings: list[GateFinding] = []
        for item in coverage:
            if not item.required or item.coverage_outcome == CoverageOutcome.VERIFIED_PASS:
                continue
            if (
                item.coverage_outcome == CoverageOutcome.VERIFIED_FAIL
                and item.failure_category == FailureCategory.ASSERTION_FAILURE
            ):
                continue
            kind = self._manual_kind(item)
            reason = self._manual_reason(item)
            findings.append(
                GateFinding(
                    key=self._finding_key("manual", item.scenario_key, reason),
                    kind=kind,
                    title=item.title,
                    reason=reason,
                    verdict_effect=VerdictEffect.MANUAL_REVIEW,
                    priority=item.priority,
                    scenario_key=item.scenario_key,
                    routes=item.routes,
                    states=item.states,
                    verified=item.verified,
                    product_facing=False,
                    failure_category=item.failure_category,
                    execution_run_id=bundle.execution.metadata.run_id,
                    source_memory_keys=item.historical_memory_keys,
                    source_rule_keys=item.historical_rule_keys,
                    evidence_refs=item.evidence_refs,
                )
            )

        required_source_keys = {
            key for item in coverage if item.required for key in item.source_impact_keys
        }
        for gap in bundle.scenario_plan.coverage_gaps:
            truncated = "trunc" in gap.reason.casefold() or "budget" in gap.reason.casefold()
            affects_required = gap.source_impact_key in required_source_keys if gap.source_impact_key else truncated
            if affects_required:
                findings.append(
                    GateFinding(
                        key=self._finding_key("scenario-gap", gap.reason, gap.detail or ""),
                        kind=(
                            GateReasonKind.COVERAGE_TRUNCATED
                            if truncated
                            else GateReasonKind.REQUIRED_SCENARIO_UNVERIFIED
                        ),
                        title="Scenario planning coverage gap",
                        reason=gap.reason + (f" — {gap.detail}" if gap.detail else ""),
                        verdict_effect=VerdictEffect.MANUAL_REVIEW,
                    )
                )
        required_keys = {item.scenario_key for item in coverage if item.required}
        for gap in bundle.execution.coverage_gaps:
            if gap.scenario_key is None or gap.scenario_key in required_keys:
        for exec_gap in bundle.execution.coverage_gaps:
            if exec_gap.scenario_key is None or exec_gap.scenario_key in required_keys:
                findings.append(
                    GateFinding(
                        key=self._finding_key(
                            "execution-gap",
                            gap.scenario_key or "run",
                            gap.reason,
                            exec_gap.scenario_key or "run",
                            exec_gap.reason,
                        ),
                        kind=GateReasonKind.REQUIRED_SCENARIO_UNVERIFIED,
                        title="Browser execution coverage gap",
                        reason=gap.reason + (f" — {gap.detail}" if gap.detail else ""),
                        reason=exec_gap.reason + (f" — {exec_gap.detail}" if exec_gap.detail else ""),
                        verdict_effect=VerdictEffect.MANUAL_REVIEW,
                        scenario_key=gap.scenario_key,
                        scenario_key=exec_gap.scenario_key,
                    )
                )
        return findings

    def _conflicting_required_scenarios(
        self,
        bundle: GateInputBundle,
        coverage: list[CoverageItem],
    ) -> set[str]:
        required = {item.scenario_key for item in coverage if item.required}
        statuses: dict[str, set[ExecutionStatus]] = {}
        for execution in bundle.execution.scenarios:
            if execution.scenario_key not in required or not execution.verified:
                continue
            statuses.setdefault(execution.scenario_key, set()).add(execution.status)
        return {
            key
            for key, values in statuses.items()
            if ExecutionStatus.PASSED in values and ExecutionStatus.FAILED in values
        }

    def _conflict_findings(self, scenario_keys: set[str]) -> list[GateFinding]:
        return [
            GateFinding(
                key=self._finding_key("conflict", scenario_key),
                kind=GateReasonKind.CONFLICTING_EVIDENCE,
                title="Conflicting verified execution evidence",
                reason=(
                    f"Required scenario {scenario_key} has both verified PASS and verified FAIL "
                    "evidence for the same gate input chain."
                ),
                verdict_effect=VerdictEffect.MANUAL_REVIEW,
                scenario_key=scenario_key,
                verified=True,
            )
            for scenario_key in sorted(scenario_keys)
        ]

    @staticmethod
    def _manual_kind(item: CoverageItem) -> GateReasonKind:
        if (
            item.readiness == AutomationReadiness.MANUAL_ONLY
            or item.coverage_outcome == CoverageOutcome.MANUAL
        ):
            return GateReasonKind.REQUIRED_SCENARIO_MANUAL_ONLY
        if (
            item.readiness == AutomationReadiness.BLOCKED_BY_GAP
            or item.coverage_outcome == CoverageOutcome.BLOCKED
        ):
            return GateReasonKind.REQUIRED_SCENARIO_BLOCKED
        if item.failure_category is not None:
            return _MANUAL_FAILURE_KINDS.get(
                item.failure_category,
                GateReasonKind.REQUIRED_SCENARIO_UNVERIFIED,
            )
        return GateReasonKind.REQUIRED_SCENARIO_UNVERIFIED

    @staticmethod
    def _manual_reason(item: CoverageItem) -> str:
        if item.failure_category is not None:
            return (
                f"Required scenario {item.scenario_key} was not safely verified because "
                f"{item.failure_category.value}."
            )
        if item.readiness == AutomationReadiness.MANUAL_ONLY:
            return f"Required scenario {item.scenario_key} is manual-only."
        if item.readiness == AutomationReadiness.BLOCKED_BY_GAP:
            return (
                f"Required scenario {item.scenario_key} is blocked by an unresolved "
                "planning/runtime gap."
            )
        return f"Required scenario {item.scenario_key} has not been verified."

    def _historical_manual_finding(self, risk: HistoricalRisk) -> GateFinding:
        reason = "Strongly related confirmed historical regression was not re-verified for this change."
        if not risk.related_scenario_keys:
            reason = (
                "Strongly related confirmed historical regression has no matching planned scenario "
                "for this change."
            )
        return GateFinding(
            key=self._finding_key("history", risk.rule_key or risk.memory_key, reason),
            kind=GateReasonKind.HISTORICAL_REGRESSION_UNVERIFIED,
            title=risk.objective or "Historical regression requires verification",
            reason=reason,
            verdict_effect=VerdictEffect.MANUAL_REVIEW,
            routes=risk.routes,
            states=risk.states,
            source_memory_keys=[risk.memory_key],
            source_rule_keys=[risk.rule_key] if risk.rule_key else [],
            evidence=risk.evidence,
        )

    @staticmethod
    def _manual_confidence(findings: list[GateFinding]) -> GateConfidence:
        low_certainty = {
            GateReasonKind.TIMEOUT_UNRESOLVED,
            GateReasonKind.CONFLICTING_EVIDENCE,
        }
        return (
            GateConfidence.MEDIUM
            if any(item.kind in low_certainty for item in findings)
            else GateConfidence.HIGH
        )

    @staticmethod
    def _block_headline(finding: GateFinding) -> str:
        return f"BLOCK — {finding.title}: {finding.reason}"

    @staticmethod
    def _metadata(bundle: GateInputBundle) -> GateMetadata:
        raw = "\0".join(
            [
                bundle.project.metadata.source_id,
                bundle.project.metadata.source_fingerprint,
                bundle.impact.metadata.change_source_id,
                bundle.scenario_plan_key,
                bundle.execution.metadata.run_id,
            ]
        )
        return GateMetadata(
            report_key="gate_" + hashlib.sha256(raw.encode()).hexdigest()[:20],
            project_source_id=bundle.project.metadata.source_id,
            project_fingerprint=bundle.project.metadata.source_fingerprint,
            change_source_id=bundle.impact.metadata.change_source_id,
            scenario_plan_key=bundle.scenario_plan_key,
            execution_run_id=bundle.execution.metadata.run_id,
        )

    @staticmethod
    def _finding_key(*parts: str) -> str:
        return "finding_" + hashlib.sha256("\0".join(parts).encode()).hexdigest()[:20]

    @staticmethod
    def _dedupe_findings(findings: list[GateFinding]) -> list[GateFinding]:
        return list({item.key: item for item in findings}.values())
