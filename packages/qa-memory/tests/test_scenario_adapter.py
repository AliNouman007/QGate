from qgate_project_intelligence.models import Confidence
from qgate_qa_memory.models import (
    ConfirmedMemory,
    MemoryRecallResult,
    MemorySeverity,
    RecalledRuleMatch,
    RegressionRule,
)
from qgate_qa_memory.scenario_adapter import build_regression_hints


def test_recalled_rule_becomes_planning_hint_not_current_bug_claim() -> None:
    memory = ConfirmedMemory(
        key="memory_checkout",
        project_source_id="local:/shop",
        title="Checkout label",
        invariant="Final payable must show You Pay",
        severity=MemorySeverity.HIGH,
        routes=["/checkout"],
        states=["wallet"],
        confidence=Confidence.HIGH,
        confirmed_by="human",
        semantic_signature="sig_checkout",
    )
    rule = RegressionRule(
        key="rule_checkout",
        source_memory_key=memory.key,
        project_source_id="local:/shop",
        title="Regression checkout label",
        routes=["/checkout"],
        states=["wallet"],
        expected_invariant=memory.invariant,
        scenario_objective="Verify wallet checkout final payable label",
        severity_hint=MemorySeverity.HIGH,
    )
    recall = MemoryRecallResult(
        project_source_id="local:/shop",
        project_fingerprint="fp",
        impact_change_source_id="git:future",
        matched_rules=[
            RecalledRuleMatch(
                rule_key=rule.key,
                source_memory_key=memory.key,
                score=100,
                reasons=["same route + state"],
            )
        ],
    )
    hints = build_regression_hints(recall, [memory], [rule])
    assert len(hints) == 1
    assert hints[0].expected_invariant == memory.invariant
    assert hints[0].requires_runtime_setup is True
    assert "not evidence that current code is broken" in hints[0].note.lower()
