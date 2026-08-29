from qgate_browser_execution.models import (
    ExecutionMetadata,
    ExecutionReport,
    ExecutionStatus,
    ExecutionSummary,
    FailureCategory,
    OperationKind,
    ScenarioExecution,
    StepEvidence,
    StepExecution,
)
from qgate_qa_memory.extraction import CandidateExtractor


def _report(status: ExecutionStatus, category: FailureCategory | None, verified: bool) -> ExecutionReport:
    step = StepExecution(
        index=1,
        operation=OperationKind.ASSERT_TEXT,
        source_action='Assert text "You Pay"',
        source_expected="You Pay",
        status=status,
        failure_category=category,
        expected="You Pay",
        actual="Total",
        detail="expected text containing 'You Pay', observed 'Total'",
        evidence=StepEvidence(requested_route="/checkout", final_url="http://local/checkout"),
    )
    scenario = ScenarioExecution(
        scenario_key="checkout_wallet",
        title="Wallet checkout final payable label",
        kind="state_variant",
        priority="P0",
        status=status,
        failure_category=category,
        verified=verified,
        target_route="/checkout",
        steps=[step],
        source_impact_keys=["state:wallet"],
    )
    return ExecutionReport(
        metadata=ExecutionMetadata(
            run_id="run123456",
            scenario_plan_key="plan123456",
            project_source_id="local:/shop",
            project_fingerprint="fp",
            impact_change_source_id="git:main...feature",
            config_fingerprint="cfg",
        ),
        summary=ExecutionSummary(selected=1, executed=1),
        scenarios=[scenario],
    )


def test_verified_assertion_failure_creates_pending_candidate() -> None:
    items = CandidateExtractor().extract(
        _report(ExecutionStatus.FAILED, FailureCategory.ASSERTION_FAILURE, True)
    )
    assert len(items) == 1
    assert items[0].invariant == "You Pay"
    assert items[0].routes == ["/checkout"]
    assert items[0].status.value == "pending"


def test_environment_or_unverified_failure_does_not_create_product_memory_candidate() -> None:
    assert CandidateExtractor().extract(
        _report(ExecutionStatus.EXECUTION_ERROR, FailureCategory.ENVIRONMENT_FAILURE, False)
    ) == []
    assert CandidateExtractor().extract(
        _report(ExecutionStatus.UNVERIFIED, FailureCategory.STATE_SETUP_FAILURE, False)
    ) == []
