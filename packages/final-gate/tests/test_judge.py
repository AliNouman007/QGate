from qgate_browser_execution.models import (
    ExecutionMetadata,
    ExecutionReport,
    ExecutionStatus,
    ExecutionSummary,
    FailureCategory,
    OperationKind,
    ScenarioExecution,
    StepExecution,
)
from qgate_final_gate.judge import FinalGateJudge
from qgate_final_gate.models import GateInputBundle, GateReasonKind, GateVerdict
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
    MemoryRecallResult,
    RecalledRuleMatch,
    RegressionScenarioHint,
)
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


def _evidence() -> Evidence:
    return Evidence(path="src/checkout.tsx", line=10, excerpt="checkout", kind="source")


def _project(fingerprint: str = "fp") -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/shop", source_fingerprint=fingerprint),
        summary=ProjectSummary(),
        files=[],
    )


def _impact(fingerprint: str = "fp") -> ImpactReport:
    direct = ImpactItem(
        key="impact:checkout",
        target_type=ImpactTargetType.ROUTE,
        target="/checkout",
        level=ImpactLevel.DIRECT,
        reason="changed checkout",
        confidence=Confidence.HIGH,
        evidence=[_evidence()],
    )
    return ImpactReport(
        metadata=ImpactMetadata(
            project_source_id="local:/shop",
            project_fingerprint=fingerprint,
            change_source_id="change:1",
        ),
        change_set=ChangeSet(source_kind=ChangeSourceKind.UNIFIED_DIFF, source_id="change:1"),
        summary=ImpactSummary(direct_impacts=1, affected_routes=1),
        direct_impacts=[direct],
        affected_routes=[direct],
    )


def _scenario(
    key: str = "checkout_wallet",
    priority: ScenarioPriority = ScenarioPriority.P1,
    readiness: AutomationReadiness = AutomationReadiness.READY,
) -> Scenario:
    return Scenario(
        key=key,
        title="Checkout wallet final payable",
        kind=ScenarioKind.STATE_VARIANT,
        priority=priority,
        confidence=Confidence.HIGH,
        routes=["/checkout"],
        states=["wallet"],
        steps=[ScenarioStep(action="inspect final payable", expected="You Pay")],
        reason="direct checkout impact",
        source_impact_keys=["impact:checkout"],
        evidence=[_evidence()],
        readiness=readiness,
    )


def _plan(*scenarios: Scenario) -> ScenarioPlan:
    selected = list(scenarios) or [_scenario()]
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/shop",
            project_fingerprint="fp",
            impact_change_source_id="change:1",
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=len(selected)),
        scenarios=selected,
    )


def _execution(
    *,
    key: str = "checkout_wallet",
    status: ExecutionStatus = ExecutionStatus.PASSED,
    verified: bool = True,
    category: FailureCategory | None = None,
    priority: str = "P1",
) -> ExecutionReport:
    steps = []
    if status == ExecutionStatus.FAILED:
        steps = [
            StepExecution(
                index=1,
                operation=OperationKind.ASSERT_TEXT,
                source_action="inspect final payable",
                source_expected="You Pay",
                expected="You Pay",
                actual="Total",
                status=status,
                failure_category=category,
                detail="expected You Pay but saw Total",
            )
        ]
    scenario = ScenarioExecution(
        scenario_key=key,
        title="Checkout wallet final payable",
        kind="state_variant",
        priority=priority,
        status=status,
        failure_category=category,
        verified=verified,
        target_route="/checkout",
        steps=steps,
        source_impact_keys=["impact:checkout"],
        detail="expected You Pay but saw Total" if status == ExecutionStatus.FAILED else None,
    )
    return ExecutionReport(
        metadata=ExecutionMetadata(
            run_id="run:1",
            scenario_plan_key="plan:1",
            project_source_id="local:/shop",
            project_fingerprint="fp",
            impact_change_source_id="change:1",
            config_fingerprint="cfg",
        ),
        summary=ExecutionSummary(selected=1, executed=1),
        scenarios=[scenario],
    )


def _bundle(plan: ScenarioPlan | None = None, execution: ExecutionReport | None = None) -> GateInputBundle:
    return GateInputBundle(
        project=_project(),
        impact=_impact(),
        scenario_plan=plan or _plan(_scenario()),
        scenario_plan_key="plan:1",
        execution=execution or _execution(),
    )


def test_verified_required_assertion_failure_blocks() -> None:
    report = FinalGateJudge().evaluate(
        _bundle(execution=_execution(status=ExecutionStatus.FAILED, category=FailureCategory.ASSERTION_FAILURE))
    )
    assert report.verdict == GateVerdict.BLOCK
    assert report.blocking_findings[0].kind == GateReasonKind.VERIFIED_PRODUCT_FAILURE


def test_required_environment_failure_is_manual_not_block() -> None:
    report = FinalGateJudge().evaluate(
        _bundle(
            execution=_execution(
                status=ExecutionStatus.FAILED,
                category=FailureCategory.ENVIRONMENT_FAILURE,
            )
        )
    )
    assert report.verdict == GateVerdict.MANUAL_REVIEW_REQUIRED
    assert report.blocking_findings == []


def test_all_required_verified_pass_returns_pass() -> None:
    report = FinalGateJudge().evaluate(_bundle())
    assert report.verdict == GateVerdict.PASS
    assert report.coverage_summary.required_verified_pass == 1


def test_zero_required_coverage_is_manual() -> None:
    p3 = _scenario(key="optional", priority=ScenarioPriority.P3)
    report = FinalGateJudge().evaluate(
        _bundle(plan=_plan(p3), execution=_execution(key="optional", priority="P3"))
    )
    assert report.verdict == GateVerdict.MANUAL_REVIEW_REQUIRED
    assert any(item.kind == GateReasonKind.NO_REQUIRED_COVERAGE for item in report.manual_review_findings)


def test_fingerprint_mismatch_fails_closed_to_manual() -> None:
    bundle = _bundle()
    bundle.execution.metadata.project_fingerprint = "stale"
    report = FinalGateJudge().evaluate(bundle)
    assert report.verdict == GateVerdict.MANUAL_REVIEW_REQUIRED
    assert report.input_integrity_findings
    assert report.blocking_findings == []


def test_strong_historical_regression_without_matching_scenario_is_manual() -> None:
    bundle = _bundle()
    bundle.memory_recall = MemoryRecallResult(
        project_source_id="local:/shop",
        project_fingerprint="fp",
        impact_change_source_id="change:1",
        matched_rules=[
            RecalledRuleMatch(
                rule_key="rule:wallet",
                source_memory_key="memory:wallet",
                score=105,
                reasons=["same route + state", "direct current impact"],
            )
        ],
    )
    bundle.regression_hints = [
        RegressionScenarioHint(
            source_memory_key="memory:wallet",
            source_rule_key="rule:wallet",
            objective="Verify wallet payable label",
            routes=["/different-route"],
            states=["wallet"],
            expected_invariant="Wallet payable label is You Pay",
        )
    ]
    report = FinalGateJudge().evaluate(bundle)
    assert report.verdict == GateVerdict.MANUAL_REVIEW_REQUIRED
    assert any(
        item.kind == GateReasonKind.HISTORICAL_REGRESSION_UNVERIFIED
        for item in report.manual_review_findings
    )


def test_optional_p3_environment_failure_does_not_override_required_pass() -> None:
    required = _scenario()
    optional = _scenario(key="optional", priority=ScenarioPriority.P3)
    execution = _execution()
    execution.scenarios.append(
        ScenarioExecution(
            scenario_key="optional",
            title="Optional",
            kind="smoke",
            priority="P3",
            status=ExecutionStatus.FAILED,
            failure_category=FailureCategory.ENVIRONMENT_FAILURE,
            verified=True,
            target_route="/checkout",
        )
    )
    report = FinalGateJudge().evaluate(_bundle(plan=_plan(required, optional), execution=execution))
    assert report.verdict == GateVerdict.PASS
