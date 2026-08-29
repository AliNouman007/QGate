from qgate_browser_execution.compiler import ScenarioCompiler
from qgate_browser_execution.models import ExecutionConfig, ExecutionStatus, OperationKind
from qgate_project_intelligence.models import Confidence
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
)


def _plan(readiness: AutomationReadiness = AutomationReadiness.READY) -> ScenarioPlan:
    scenario = Scenario(
        key="scn_demo",
        title="Checkout label",
        kind=ScenarioKind.STATE_VARIANT,
        priority=ScenarioPriority.P0,
        confidence=Confidence.HIGH,
        routes=["/checkout"],
        targets=["checkout"],
        states=["guest"],
        steps=[ScenarioStep(action='Assert text "You Pay"', expected="You Pay", route="/checkout")],
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


def test_ready_route_scenario_compiles_to_navigation_and_assertion() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(), ExecutionConfig(base_url="http://127.0.0.1:4173")
    )
    assert len(request.scenarios) == 1
    assert [step.operation for step in request.scenarios[0].steps] == [
        OperationKind.NAVIGATE,
        OperationKind.ASSERT_TEXT,
    ]


def test_runtime_discovery_is_not_promoted_to_ready() -> None:
    request = ScenarioCompiler().compile_plan(
        _plan(AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED),
        ExecutionConfig(base_url="http://127.0.0.1:4173"),
    )
    assert request.scenarios == []
    assert request.preclassified[0].status == ExecutionStatus.UNVERIFIED
