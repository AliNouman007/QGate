from qgate_impact_analysis.models import (
    ChangeSet,
    ChangeSourceKind,
    ImpactItem,
    ImpactLevel,
    ImpactMetadata,
    ImpactReport,
    ImpactSummary,
    ImpactTargetType,
)
from qgate_project_intelligence.models import (
    AnalysisMetadata,
    Confidence,
    Evidence,
    ProjectKnowledge,
    ProjectSummary,
)
from qgate_qa_memory.models import (
    ConfirmedMemory,
    MemorySeverity,
    MemoryStatus,
    RecallBudget,
    RegressionRule,
)
from qgate_qa_memory.recall import MemoryRecallEngine


def _knowledge() -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/shop", source_fingerprint="fp"),
        summary=ProjectSummary(),
        files=[],
    )


def _impact(route: str = "/checkout", state: str = "wallet") -> ImpactReport:
    route_item = ImpactItem(
        key=f"route:{route}",
        target_type=ImpactTargetType.ROUTE,
        target=route,
        level=ImpactLevel.DIRECT,
        reason="changed checkout",
        confidence=Confidence.HIGH,
        evidence=[Evidence(path="src/Checkout.tsx", line=1, excerpt="checkout", kind="route")],
    )
    state_item = ImpactItem(
        key=f"state:{state}",
        target_type=ImpactTargetType.STATE,
        target=state,
        level=ImpactLevel.DIRECT,
        reason="wallet branch",
        confidence=Confidence.HIGH,
        evidence=[Evidence(path="src/Checkout.tsx", line=2, excerpt="wallet", kind="state")],
    )
    return ImpactReport(
        metadata=ImpactMetadata(
            project_source_id="local:/shop",
            project_fingerprint="fp",
            change_source_id="git:main...feature",
        ),
        change_set=ChangeSet(source_kind=ChangeSourceKind.LOCAL_GIT, source_id="git:main...feature"),
        summary=ImpactSummary(affected_routes=1, affected_states=1),
        direct_impacts=[route_item, state_item],
        affected_routes=[route_item],
        affected_states=[state_item],
    )


def _memory(status: MemoryStatus = MemoryStatus.ACTIVE) -> ConfirmedMemory:
    return ConfirmedMemory(
        key="memory_checkout",
        project_source_id="local:/shop",
        title="Checkout wallet label",
        invariant="Final payable must show You Pay",
        severity=MemorySeverity.HIGH,
        routes=["/checkout"],
        components=["CheckoutSummary"],
        states=["wallet"],
        confidence=Confidence.HIGH,
        status=status,
        confirmed_by="human",
        semantic_signature="semantic_checkout",
    )


def _rule(active: bool = True) -> RegressionRule:
    return RegressionRule(
        key="rule_checkout",
        source_memory_key="memory_checkout",
        project_source_id="local:/shop",
        title="Regression checkout label",
        routes=["/checkout"],
        components=["CheckoutSummary"],
        states=["wallet"],
        expected_invariant="Final payable must show You Pay",
        scenario_objective="Verify final payable label in wallet state",
        severity_hint=MemorySeverity.HIGH,
        active=active,
    )


def test_relevant_active_memory_and_rule_are_recalled() -> None:
    result = MemoryRecallEngine().recall(_knowledge(), _impact(), [_memory()], [_rule()])
    assert [item.memory_key for item in result.matched_memories] == ["memory_checkout"]
    assert [item.rule_key for item in result.matched_rules] == ["rule_checkout"]
    assert result.matched_memories[0].score >= 85


def test_inactive_memory_and_unrelated_route_are_not_recalled() -> None:
    inactive = MemoryRecallEngine().recall(
        _knowledge(), _impact(), [_memory(MemoryStatus.INACTIVE)], [_rule()]
    )
    assert inactive.matched_memories == []
    unrelated = MemoryRecallEngine().recall(_knowledge(), _impact("/admin", "admin"), [_memory()], [_rule()])
    assert unrelated.matched_memories == []


def test_recall_budget_records_truncation() -> None:
    memories = [
        _memory().model_copy(update={"key": f"memory_checkout_{index}", "semantic_signature": f"sig{index}"})
        for index in range(3)
    ]
    result = MemoryRecallEngine().recall(
        _knowledge(), _impact(), memories, [], budget=RecallBudget(max_memories=1, max_rules=1)
    )
    assert len(result.matched_memories) == 1
    assert any(gap.reason == "memory_recall_truncated" for gap in result.coverage_gaps)
