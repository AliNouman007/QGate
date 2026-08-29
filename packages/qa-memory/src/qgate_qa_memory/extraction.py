from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from qgate_browser_execution.models import ExecutionReport, ExecutionStatus, FailureCategory
from qgate_project_intelligence.models import Confidence, Evidence

from .models import CandidateKind, MemoryCandidate, MemorySeverity, OccurrenceRef
from .signature import candidate_signature

if TYPE_CHECKING:
    from qgate_browser_execution.models import StepExecution


class CandidateExtractor:
    def extract(self, report: ExecutionReport) -> list[MemoryCandidate]:
        candidates: list[MemoryCandidate] = []
        for scenario in report.scenarios:
            if not scenario.verified:
                continue
            if scenario.status != ExecutionStatus.FAILED:
                continue
            if scenario.failure_category != FailureCategory.ASSERTION_FAILURE:
                continue

            failing_step = next(
                (
                    step
                    for step in scenario.steps
                    if step.status == ExecutionStatus.FAILED
                    and step.failure_category == FailureCategory.ASSERTION_FAILURE
                ),
                None,
            )
            if failing_step is None:
                continue

            expected = failing_step.expected or failing_step.source_expected or scenario.title
            route = scenario.target_route or failing_step.evidence.requested_route
            evidence = self._evidence_for_step(scenario.scenario_key, failing_step)
            components, symbols, states, targets = self._scope_from_impact_keys(
                scenario.source_impact_keys
            )
            candidate = MemoryCandidate(
                key=self._candidate_key(report.metadata.run_id, scenario.scenario_key, failing_step.index),
                project_source_id=report.metadata.project_source_id,
                project_fingerprint=report.metadata.project_fingerprint,
                title=scenario.title,
                invariant=expected,
                kind=CandidateKind.ASSERTION_REGRESSION,
                severity=self._severity_from_priority(scenario.priority),
                routes=[route] if route else [],
                components=components,
                symbols=symbols,
                states=states,
                targets=targets,
                source_scenario_key=scenario.scenario_key,
                source_execution_run_id=report.metadata.run_id,
                source_impact_keys=scenario.source_impact_keys,
                evidence=evidence,
                confidence=Confidence.HIGH,
                dedupe_signature="pending",
                occurrences=[
                    OccurrenceRef(
                        execution_run_id=report.metadata.run_id,
                        scenario_key=scenario.scenario_key,
                    )
                ],
            )
            candidate.dedupe_signature = candidate_signature(candidate)
            candidates.append(candidate)
        return candidates

    @staticmethod
    def _candidate_key(run_id: str, scenario_key: str, step_index: int) -> str:
        raw = f"{run_id}\0{scenario_key}\0{step_index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    @staticmethod
    def _severity_from_priority(priority: str) -> MemorySeverity:
        return {
            "P0": MemorySeverity.CRITICAL,
            "P1": MemorySeverity.HIGH,
            "P2": MemorySeverity.MEDIUM,
            "P3": MemorySeverity.LOW,
        }.get(priority.upper(), MemorySeverity.UNKNOWN)

    @staticmethod
    def _scope_from_impact_keys(
        keys: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        components: set[str] = set()
        symbols: set[str] = set()
        states: set[str] = set()
        targets: set[str] = set()
        for key in keys:
            prefix, separator, value = key.partition(":")
            if not separator or not value:
                continue
            if prefix == "component":
                components.add(value)
            elif prefix == "symbol":
                symbols.add(value)
            elif prefix == "state":
                states.add(value)
            elif prefix in {"file", "module"}:
                targets.add(value)
        return sorted(components), sorted(symbols), sorted(states), sorted(targets)

    @staticmethod
    def _evidence_for_step(scenario_key: str, step: StepExecution) -> list[Evidence]:
        evidence: list[Evidence] = []
        if step.evidence.dom and step.evidence.dom.html_excerpt:
            evidence.append(
                Evidence(
                    path=f"execution:{scenario_key}",
                    line=1,
                    excerpt=step.evidence.dom.html_excerpt[:500],
                    kind="browser_dom",
                )
            )
        if step.detail:
            evidence.append(
                Evidence(
                    path=f"execution:{scenario_key}",
                    line=1,
                    excerpt=step.detail[:500],
                    kind="assertion_failure",
                )
            )
        return evidence
