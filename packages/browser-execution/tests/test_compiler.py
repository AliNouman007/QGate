from qgate_browser_execution.compiler import ScenarioCompiler
from qgate_browser_execution.models import ExecutionConfig, ExecutionStatus, OperationKind
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


def _plan(
    readiness: AutomationReadiness = AutomationReadiness.READY,
    *,
    preconditions: list[str] | None = None,
    action: str = 'Assert text "You Pay"',
    states: list[str] | None = None,
    state_setup_hints: list[StateSetupHint] | None = None,
) -> ScenarioPlan:
    scenario = Scenario(
        key="scn_demo",
        title="Checkout label",
        kind=ScenarioKind.STATE_VARIANT,
        priority=ScenarioPriority.P0,
        confidence=Confidence.HIGH,
        routes=["/checkout"],
        targets=["checkout"],
        states=states or [],
        state_setup_hints=state_setup_hints or [],
        preconditions=preconditions or [],
        steps=[ScenarioStep(action=action, expected="You Pay", route="/checkout")],
        reason="changed checkout label",
        source_impact_keys=["impact:checkout"],
        readiness=readiness,
        needs_runtime_discovery=readiness != AutomationReadiness.READY,
    )
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/demo",
            project_fingerprint="fingerprint",
            impact_change_source_id="diff:1",
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=1, ready=1 if readiness == AutomationReadiness.READY else 0),
        scenarios=[scenario],
    )


def _wallet_hint() -> StateSetupHint:
    return StateSetupHint(
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


def test_ready_route_scenario_compiles_to_navigation_and_assertion() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(), ExecutionConfig(base_url="http://127.0.0.1:4173")
    )
    assert len(request.scenarios) == 1
    assert [step.operation for step in request.scenarios[0].steps] == [
        OperationKind.NAVIGATE,
        OperationKind.ASSERT_TEXT,
    ]


def test_stateful_scenario_compiles_setup_before_assertion() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(
            states=["user:wallet"],
            state_setup_hints=[_wallet_hint()],
            preconditions=["Establish Logged In + Wallet"],
        ),
        ExecutionConfig(base_url="http://127.0.0.1:4173"),
    )
    assert len(request.scenarios) == 1
    steps = request.scenarios[0].steps
    assert [step.operation for step in steps] == [
        OperationKind.NAVIGATE,
        OperationKind.CLICK,
        OperationKind.ASSERT_VISIBLE,
        OperationKind.ASSERT_TEXT,
    ]
    assert steps[1].state_setup is True
    assert steps[2].state_setup is True


def test_runtime_discovery_is_not_promoted_to_ready() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED),
        ExecutionConfig(base_url="http://127.0.0.1:4173"),
    )
    assert request.scenarios == []
    assert request.preclassified[0].status == ExecutionStatus.UNVERIFIED


def test_stateful_scenario_without_setup_hint_fails_closed() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(states=["user:wallet"]),
        ExecutionConfig(base_url="http://127.0.0.1:4173"),
    )
    assert request.scenarios == []
    assert request.preclassified[0].status == ExecutionStatus.UNVERIFIED
    assert "state setup" in request.preclassified[0].reason


def test_ready_scenario_with_unknown_preconditions_fails_closed() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(preconditions=["Establish authenticated wallet state"]),
        ExecutionConfig(base_url="http://127.0.0.1:4173"),
    )
    assert request.scenarios == []
    assert request.preclassified[0].status == ExecutionStatus.UNVERIFIED
    assert "preconditions" in request.preclassified[0].reason


def test_ready_scenario_with_unsupported_step_fails_closed() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(action="Exercise checkout in both states and compare layout"),
        ExecutionConfig(base_url="http://127.0.0.1:4173"),
    )
    assert request.scenarios == []
    assert request.preclassified[0].status == ExecutionStatus.UNVERIFIED
    assert "Unsupported deterministic browser step" in request.preclassified[0].reason
