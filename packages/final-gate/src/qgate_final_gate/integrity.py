from __future__ import annotations

from .models import GateInputBundle, InputIntegrityFinding


def validate_input_integrity(bundle: GateInputBundle) -> list[InputIntegrityFinding]:
    findings: list[InputIntegrityFinding] = []

    def add(reason: str) -> None:
        findings.append(InputIntegrityFinding(reason=reason))

    project = bundle.project.metadata
    impact = bundle.impact.metadata
    scenario = bundle.scenario_plan.metadata
    execution = bundle.execution.metadata

    if project.source_id != impact.project_source_id:
        add("ProjectKnowledge source id does not match ImpactReport project source id")
    if project.source_fingerprint != impact.project_fingerprint:
        add("ProjectKnowledge fingerprint does not match ImpactReport project fingerprint")
    if scenario.project_source_id != impact.project_source_id:
        add("ScenarioPlan project source id does not match ImpactReport")
    if scenario.project_fingerprint != impact.project_fingerprint:
        add("ScenarioPlan project fingerprint does not match ImpactReport")
    if scenario.impact_change_source_id != impact.change_source_id:
        add("ScenarioPlan change source id does not match ImpactReport")
    if execution.project_source_id != scenario.project_source_id:
        add("ExecutionReport project source id does not match ScenarioPlan")
    if execution.project_fingerprint != scenario.project_fingerprint:
        add("ExecutionReport project fingerprint does not match ScenarioPlan")
    if execution.impact_change_source_id != scenario.impact_change_source_id:
        add("ExecutionReport change source id does not match ScenarioPlan")
    if execution.scenario_plan_key != bundle.scenario_plan_key:
        add("ExecutionReport scenario plan key does not match the selected ScenarioPlan")

    recall = bundle.memory_recall
    if recall is not None:
        if recall.project_source_id != project.source_id:
            add("MemoryRecallResult project source id does not match ProjectKnowledge")
        if recall.project_fingerprint != project.source_fingerprint:
            add("MemoryRecallResult project fingerprint does not match ProjectKnowledge")
        if recall.impact_change_source_id != impact.change_source_id:
            add("MemoryRecallResult change source id does not match ImpactReport")

    return findings
