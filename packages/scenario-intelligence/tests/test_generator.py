from __future__ import annotations

import pytest
from qgate_impact_analysis.models import (
    ChangeCategory,
    ChangeSet,
    ChangeSourceKind,
    DependencyStep,
    ImpactItem,
    ImpactLevel,
    ImpactMetadata,
    ImpactReport,
    ImpactSummary,
    ImpactTargetType,
    SharedImpactGroup,
)
from qgate_project_intelligence.models import (
    AnalysisMetadata,
    Confidence,
    Evidence,
    ProjectKnowledge,
    ProjectSummary,
    SemanticState,
    SemanticStateKind,
)
from qgate_scenario_intelligence.generator import ScenarioGenerator, ScenarioInputMismatchError
from qgate_scenario_intelligence.models import (
    AutomationReadiness,
    GenerationBudget,
    ScenarioKind,
    StateSetupMechanism,
)


def _e(path: str, line: int, excerpt: str) -> Evidence:
    return Evidence(path=path, line=line, excerpt=excerpt, kind="test")


def _knowledge() -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/demo", source_fingerprint="fp1"),
        summary=ProjectSummary(total_files=3),
        files=[],
        semantic_states=[
            SemanticState(
                key="rating:present",
                label="Rating present",
                kind=SemanticStateKind.DATA_STATE,
                explanation="A rating value is present.",
                confidence=Confidence.HIGH,
                evidence=[_e("src/Card.tsx", 5, "rating")],
            ),
            SemanticState(
                key="rating:absent",
                label="Rating absent",
                kind=SemanticStateKind.DATA_STATE,
                explanation="A rating value is absent.",
                confidence=Confidence.HIGH,
                evidence=[_e("src/Card.tsx", 6, "!rating")],
            ),
        ],
    )


def _impact() -> ImpactReport:
    direct = ImpactItem(
        key="file:src/Card.tsx",
        target_type=ImpactTargetType.COMPONENT,
        target="Card",
        level=ImpactLevel.DIRECT,
        reason="Card changed",
        confidence=Confidence.HIGH,
        evidence=[_e("src/Card.tsx", 5, "className")],
        categories=[ChangeCategory.UI, ChangeCategory.STATE, ChangeCategory.SHARED],
    )
    route = ImpactItem(
        key="route:/search",
        target_type=ImpactTargetType.ROUTE,
        target="/search",
        level=ImpactLevel.INDIRECT,
        reason="Search depends on Card",
        confidence=Confidence.HIGH,
        evidence=[_e("src/app/search/page.tsx", 1, "Card")],
        categories=[ChangeCategory.UI, ChangeCategory.SHARED],
    )
    states = [
        ImpactItem(
            key="state:rating:present",
            target_type=ImpactTargetType.STATE,
            target="Rating present",
            level=ImpactLevel.DIRECT,
            reason="Changed rating branch",
            confidence=Confidence.HIGH,
            evidence=[_e("src/Card.tsx", 5, "rating")],
            categories=[ChangeCategory.STATE],
        ),
        ImpactItem(
            key="state:rating:absent",
            target_type=ImpactTargetType.STATE,
            target="Rating absent",
            level=ImpactLevel.DIRECT,
            reason="Changed no-rating branch",
            confidence=Confidence.HIGH,
            evidence=[_e("src/Card.tsx", 6, "!rating")],
            categories=[ChangeCategory.STATE],
        ),
    ]
    return ImpactReport(
        metadata=ImpactMetadata(
            project_source_id="local:/demo",
            project_fingerprint="fp1",
            change_source_id="git:main...feature",
        ),
        change_set=ChangeSet(
            source_kind=ChangeSourceKind.LOCAL_GIT, source_id="git:main...feature"
        ),
        summary=ImpactSummary(),
        direct_impacts=[direct],
        affected_routes=[route],
        affected_states=states,
        shared_groups=[
            SharedImpactGroup(
                changed_target="src/Card.tsx", reuse_count=3, affected_routes=["/search"]
            )
        ],
    )


def test_generates_prioritized_state_and_cross_state_scenarios() -> None:
    plan = ScenarioGenerator().generate(_knowledge(), _impact())
    assert plan.summary.total >= 3
    assert any(
        item.kind == ScenarioKind.ROUTE_REGRESSION and "/search" in item.routes
        for item in plan.scenarios
    )
    assert {"rating:present", "rating:absent"}.issubset(
        {state for item in plan.scenarios for state in item.states}
    )
    assert any(item.kind == ScenarioKind.CROSS_STATE_COMPARISON for item in plan.scenarios)
    assert all(item.reason and item.evidence for item in plan.scenarios)


def test_ui_reachable_user_state_gets_deterministic_setup_hint() -> None:
    knowledge = _knowledge()
    knowledge.semantic_states.append(
        SemanticState(
            key="user:wallet",
            label="Logged In + Wallet",
            kind=SemanticStateKind.USER_STATE,
            explanation="A visible user-state control selects the wallet customer fixture.",
            confidence=Confidence.HIGH,
            evidence=[_e("src/Card.tsx", 20, "Logged In + Wallet")],
        )
    )
    impact = _impact()
    impact.affected_states.append(
        ImpactItem(
            key="state:user:wallet",
            target_type=ImpactTargetType.STATE,
            target="Logged In + Wallet",
            level=ImpactLevel.DIRECT,
            reason="Wallet-dependent checkout behavior changed",
            confidence=Confidence.HIGH,
            evidence=[_e("src/Card.tsx", 20, "Logged In + Wallet")],
            categories=[ChangeCategory.STATE],
        )
    )

    plan = ScenarioGenerator().generate(knowledge, impact)
    scenario = next(item for item in plan.scenarios if "Logged In + Wallet" in item.title)
    assert scenario.readiness == AutomationReadiness.READY
    assert len(scenario.state_setup_hints) == 1
    assert scenario.state_setup_hints[0].mechanism == StateSetupMechanism.UI_CONTROL
    assert scenario.state_setup_hints[0].target_label == "Logged In + Wallet"


def test_state_route_selection_prefers_stronger_deterministic_state_evidence() -> None:
    state = SemanticState(
        key="src/shop-context.tsx:user:wallet",
        label="Wallet",
        kind=SemanticStateKind.USER_STATE,
        explanation="Wallet user state changes the payable total.",
        confidence=Confidence.HIGH,
        evidence=[_e("src/shop-context.tsx", 8, "userMode === 'wallet'")],
    )
    cart = ImpactItem(
        key="route:/cart",
        target_type=ImpactTargetType.ROUTE,
        target="/cart",
        level=ImpactLevel.INDIRECT,
        reason="Cart depends on shared shop context",
        confidence=Confidence.HIGH,
        evidence=[_e("src/cart/page.tsx", 1, "const { subtotal } = useShop()")],
        dependency_path=[
            DependencyStep(
                source="src/cart/page.tsx",
                target="src/shop-context.tsx",
                module="../shop-context",
            )
        ],
    )
    checkout = ImpactItem(
        key="route:/checkout",
        target_type=ImpactTargetType.ROUTE,
        target="/checkout",
        level=ImpactLevel.INDIRECT,
        reason="Checkout depends on shared shop context",
        confidence=Confidence.HIGH,
        evidence=[
            _e(
                "src/checkout/page.tsx",
                1,
                "const { wallet, total } = useShop(); Final payable; Wallet deduction",
            )
        ],
        dependency_path=[
            DependencyStep(
                source="src/checkout/page.tsx",
                target="src/shop-context.tsx",
                module="../shop-context",
            )
        ],
    )
    impact = ImpactReport(
        metadata=ImpactMetadata(
            project_source_id="local:/demo",
            project_fingerprint="fp1",
            change_source_id="git:main...feature",
        ),
        change_set=ChangeSet(
            source_kind=ChangeSourceKind.LOCAL_GIT,
            source_id="git:main...feature",
        ),
        summary=ImpactSummary(),
        affected_routes=[cart, checkout],
    )

    assert ScenarioGenerator._best_route_for_state(
        state, impact.affected_routes, impact
    ) == "/checkout"


def test_data_state_without_safe_setup_hint_stays_runtime_discovery() -> None:
    plan = ScenarioGenerator().generate(_knowledge(), _impact())
    scenario = next(item for item in plan.scenarios if item.states == ["rating:present"])
    assert scenario.readiness == AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED
    assert scenario.state_setup_hints == []


def test_mismatched_fingerprint_fails_closed() -> None:
    knowledge = _knowledge()
    impact = _impact()
    impact.metadata.project_fingerprint = "different"
    with pytest.raises(ScenarioInputMismatchError):
        ScenarioGenerator().generate(knowledge, impact)


def test_unknown_impact_becomes_runtime_discovery_not_ready() -> None:
    impact = _impact()
    impact.unknown_impacts.append(
        ImpactItem(
            key="unknown:dynamic",
            target_type=ImpactTargetType.STATE,
            target="Dynamic state",
            level=ImpactLevel.UNKNOWN,
            reason="Dynamic state cannot be resolved statically",
            confidence=Confidence.LOW,
            evidence=[_e("src/Card.tsx", 9, "dynamic")],
            needs_runtime_verification=True,
        )
    )
    plan = ScenarioGenerator().generate(_knowledge(), impact)
    scenario = next(item for item in plan.scenarios if "Dynamic state" in item.title)
    assert scenario.readiness == AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED
    assert scenario.needs_runtime_discovery


def test_generation_budget_limits_scenarios_and_records_gap() -> None:
    plan = ScenarioGenerator(GenerationBudget(max_scenarios=2)).generate(
        _knowledge(), _impact()
    )
    assert len(plan.scenarios) == 2
    assert any(gap.reason == "scenario_budget_reached" for gap in plan.coverage_gaps)
