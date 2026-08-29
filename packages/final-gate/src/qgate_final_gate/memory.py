from __future__ import annotations

from typing import TYPE_CHECKING

from .models import HistoricalRisk

if TYPE_CHECKING:
    from qgate_qa_memory.models import MemoryRecallResult, RegressionScenarioHint
    from qgate_scenario_intelligence.models import ScenarioPlan

_HIGH_SPECIFICITY_REASONS = {
    "same symbol/component + state",
    "same route + state",
}
_STRUCTURAL_REASONS = {
    "same symbol/component",
    "same route",
}
_CURRENT_IMPACT_REASONS = {
    "direct current impact",
    "indirect current impact",
}


def _is_strong(reasons: list[str]) -> bool:
    reason_set = set(reasons)
    return bool(
        reason_set & _HIGH_SPECIFICITY_REASONS
        or (reason_set & _STRUCTURAL_REASONS and reason_set & _CURRENT_IMPACT_REASONS)
    )


def _related_scenarios(hint: RegressionScenarioHint, plan: ScenarioPlan) -> list[str]:
    related: list[str] = []
    hint_routes = set(hint.routes)
    hint_components = set(hint.components)
    hint_states = set(hint.states)
    for scenario in plan.scenarios:
        route_match = bool(hint_routes & set(scenario.routes)) if hint_routes else False
        target_match = bool(hint_components & set(scenario.targets)) if hint_components else False
        state_match = bool(hint_states & set(scenario.states)) if hint_states else not hint_states
        invariant_match = any(
            hint.expected_invariant.casefold() in step.expected.casefold()
            or step.expected.casefold() in hint.expected_invariant.casefold()
            for step in scenario.steps
            if step.expected.strip()
        route_match = bool(hint_routes & set(scenario.routes)) if hint_routes else True
        target_match = bool(hint_components & set(scenario.targets)) if hint_components else True
        state_match = bool(hint_states & set(scenario.states)) if hint_states else True
        if not (route_match and target_match and state_match):
            continue

        invariant_match = (
            any(
                hint.expected_invariant.casefold() in step.expected.casefold()
                or step.expected.casefold() in hint.expected_invariant.casefold()
                for step in scenario.steps
                if step.expected.strip()
            )
            if hint.expected_invariant
            else True
        )
        if (route_match or target_match or invariant_match) and state_match:
        if invariant_match:
            related.append(scenario.key)
    return related


def build_historical_risks(
    plan: ScenarioPlan,
    recall: MemoryRecallResult | None,
    hints: list[RegressionScenarioHint],
    verified_pass_scenario_keys: set[str],
) -> list[HistoricalRisk]:
    if recall is None:
        return []

    hints_by_rule = {hint.source_rule_key: hint for hint in hints if hint.source_rule_key}
    risks: list[HistoricalRisk] = []
    for match in recall.matched_rules:
        hint = hints_by_rule.get(match.rule_key)
        related = _related_scenarios(hint, plan) if hint is not None else []
        strong = _is_strong(match.reasons)
        risks.append(
            HistoricalRisk(
                memory_key=match.source_memory_key,
                rule_key=match.rule_key,
                score=match.score,
                reasons=match.reasons,
                strong_match=strong,
                objective=hint.objective if hint else None,
                expected_invariant=hint.expected_invariant if hint else None,
                routes=hint.routes if hint else [],
                components=hint.components if hint else [],
                states=hint.states if hint else [],
                related_scenario_keys=related,
                covered=bool(related) and any(key in verified_pass_scenario_keys for key in related),
                evidence=match.evidence,
            )
        )
    return risks


def historical_links_for_scenario(
    scenario_key: str,
    risks: list[HistoricalRisk],
) -> tuple[list[str], list[str]]:
    memory_keys = sorted(
        {risk.memory_key for risk in risks if risk.strong_match and scenario_key in risk.related_scenario_keys}
    )
    rule_keys = sorted(
        {
            risk.rule_key
            for risk in risks
            if risk.strong_match and scenario_key in risk.related_scenario_keys and risk.rule_key
        }
    )
    return memory_keys, rule_keys
