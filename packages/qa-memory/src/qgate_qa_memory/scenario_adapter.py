from __future__ import annotations

from .models import (
    ConfirmedMemory,
    MemoryRecallResult,
    RegressionRule,
    RegressionScenarioHint,
)


def build_regression_hints(
    recall: MemoryRecallResult,
    memories: list[ConfirmedMemory],
    rules: list[RegressionRule],
) -> list[RegressionScenarioHint]:
    memories_by_key = {memory.key: memory for memory in memories}
    rules_by_key = {rule.key: rule for rule in rules}
    hints: list[RegressionScenarioHint] = []
    for recalled_rule in recall.matched_rules:
        rule = rules_by_key.get(recalled_rule.rule_key)
        memory = memories_by_key.get(recalled_rule.source_memory_key)
        if rule is None or memory is None or not rule.active:
            continue
        hints.append(
            RegressionScenarioHint(
                source_memory_key=memory.key,
                source_rule_key=rule.key,
                objective=rule.scenario_objective,
                routes=rule.routes,
                components=rule.components,
                states=rule.states,
                expected_invariant=rule.expected_invariant,
                severity_hint=rule.severity_hint,
                evidence=recalled_rule.evidence,
                requires_runtime_setup=bool(rule.states),
            )
        )
    return hints
