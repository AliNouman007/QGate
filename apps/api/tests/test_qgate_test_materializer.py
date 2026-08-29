from qgate_project_intelligence.models import Confidence, Evidence
from qgate_scenario_intelligence.models import (
    AutomationReadiness,
    GenerationBudget,
    Scenario,
    ScenarioKind,
    ScenarioPlan,
    ScenarioPlanMetadata,
    ScenarioPriority,
    ScenarioStep,
    ScenarioSummary,
    StateSetupHint,
    StateSetupMechanism,
)
from suitest_api.services.qgate_test_materializer import QGateTestMaterializer


def _plan(*, change_id: str = "git:main...feature") -> ScenarioPlan:
    hint = StateSetupHint(
        state_key="user:wallet",
        state_label="Logged In + Wallet",
        mechanism=StateSetupMechanism.UI_CONTROL,
        target_label="Logged In + Wallet",
        verification_text="Logged In + Wallet",
        confidence=Confidence.HIGH,
        evidence=[
            Evidence(
                path="app/shop-context.js",
                line=10,
                excerpt="Logged In + Wallet",
                kind="test",
            )
        ],
    )
    scenario = Scenario(
        key="scn_wallet",
        title="Verify Logged In + Wallet on /checkout",
        kind=ScenarioKind.STATE_VARIANT,
        priority=ScenarioPriority.P0,
        confidence=Confidence.HIGH,
        routes=["/checkout"],
        targets=["checkout"],
        states=["user:wallet"],
        state_setup_hints=[hint],
        preconditions=["Establish the evidence-backed state: Logged In + Wallet."],
        steps=[
            ScenarioStep(
                action='Assert text "Final payable"',
                expected="Final payable is correct for the wallet state.",
                route="/checkout",
            )
        ],
        reason="Wallet-sensitive checkout calculation changed.",
        source_impact_keys=["impact:wallet"],
        evidence=hint.evidence,
        readiness=AutomationReadiness.READY,
    )
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/shop",
            project_fingerprint="fingerprint-123",
            impact_change_source_id=change_id,
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=1, ready=1, p0=1),
        scenarios=[scenario],
    )


def test_executable_state_scenario_maps_to_visible_suitest_steps() -> None:
    scenario = _plan().scenarios[0]
    steps = QGateTestMaterializer._steps_for(scenario)
    assert steps is not None
    assert [step.mcp_provider for step in steps] == ["playwright-mcp"] * len(steps)
    assert steps[0].action == "Navigate to /checkout"
    assert "Logged In + Wallet" in steps[1].action
    assert any("Final payable" in step.action for step in steps)


def test_unresolved_state_scenario_is_not_materialized_as_executable() -> None:
    scenario = _plan().scenarios[0].model_copy(
        update={"readiness": AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED}
    )
    assert QGateTestMaterializer._steps_for(scenario) is None


def test_identity_tags_are_bounded_and_change_specific() -> None:
    long_change = "git:" + "x" * 200
    first = _plan(change_id=long_change)
    second = _plan(change_id=long_change + "-other")
    tags_first = QGateTestMaterializer._identity_tags(first, first.scenarios[0])
    tags_second = QGateTestMaterializer._identity_tags(second, second.scenarios[0])
    assert all(len(tag) <= 64 for tag in tags_first)
    assert "qgate-managed" in tags_first
    assert tags_first != tags_second
