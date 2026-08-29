from pathlib import Path

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
from qgate_qa_memory.extraction import CandidateExtractor
from qgate_qa_memory.lifecycle import QAMemoryService
from qgate_qa_memory.models import CandidateKind, MemoryCandidate
from qgate_qa_memory.recall import MemoryRecallEngine
from qgate_qa_memory.scenario_adapter import build_regression_hints
from qgate_qa_memory.signature import candidate_signature
from qgate_qa_memory.store import JsonQAMemoryStore


def _execution() -> ExecutionReport:
    scenario = ScenarioExecution(
        scenario_key="checkout_wallet",
        title="Wallet checkout final payable",
        kind="state_variant",
        priority="P0",
        status=ExecutionStatus.FAILED,
        failure_category=FailureCategory.ASSERTION_FAILURE,
        verified=True,
        target_route="/checkout",
        steps=[
            StepExecution(
                index=1,
                operation=OperationKind.ASSERT_TEXT,
                source_action='Assert text "You Pay"',
                source_expected="You Pay",
                status=ExecutionStatus.FAILED,
                failure_category=FailureCategory.ASSERTION_FAILURE,
                expected="You Pay",
                actual="Total",
                detail="expected You Pay, observed Total",
            )
        ],
        source_impact_keys=["route:/checkout", "state:wallet"],
    )
    return ExecutionReport(
        metadata=ExecutionMetadata(
            run_id="run_checkout",
            scenario_plan_key="plan_checkout",
            project_source_id="local:/shop",
            project_fingerprint="fp",
            impact_change_source_id="git:old",
            config_fingerprint="cfg",
        ),
        summary=ExecutionSummary(selected=1, executed=1, failed=1),
        scenarios=[scenario],
    )


def _knowledge() -> ProjectKnowledge:
    return ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/shop", source_fingerprint="fp"),
        summary=ProjectSummary(),
        files=[],
    )


def _future_impact(route: str) -> ImpactReport:
    item = ImpactItem(
        key=f"route:{route}",
        target_type=ImpactTargetType.ROUTE,
        target=route,
        level=ImpactLevel.DIRECT,
        reason="future change",
        confidence=Confidence.HIGH,
        evidence=[Evidence(path="src/page.tsx", line=1, excerpt=route, kind="route")],
    )
    return ImpactReport(
        metadata=ImpactMetadata(
            project_source_id="local:/shop",
            project_fingerprint="fp",
            change_source_id="git:future",
        ),
        change_set=ChangeSet(source_kind=ChangeSourceKind.LOCAL_GIT, source_id="git:future"),
        summary=ImpactSummary(affected_routes=1),
        direct_impacts=[item],
        affected_routes=[item],
    )


def test_confirmed_memory_recalled_rejected_false_positive_excluded(tmp_path: Path) -> None:
    store = JsonQAMemoryStore(tmp_path)
    service = QAMemoryService(store)

    extracted = CandidateExtractor().extract(_execution())
    assert len(extracted) == 1
    confirmed_candidate = service.ingest_candidate(extracted[0])
    _, memory, rule = service.confirm_candidate(confirmed_candidate.key, reviewer="human-qa")
    assert rule is not None

    false_positive = MemoryCandidate(
        key="candidate_www_false_positive",
        project_source_id="local:/shop",
        project_fingerprint="fp",
        title="WWW shipping country",
        invariant="Shipping country must not be WWW",
        kind=CandidateKind.HUMAN_REPORTED,
        routes=["/checkout"],
        states=["missing_country_cookie"],
        dedupe_signature="pending",
    )
    false_positive.dedupe_signature = candidate_signature(false_positive)
    false_positive = service.ingest_candidate(false_positive, actor="human-qa")
    service.reject_candidate(
        false_positive.key,
        reviewer="human-qa",
        note="technically possible but not realistically reachable",
    )

    recall = MemoryRecallEngine().recall(
        _knowledge(),
        _future_impact("/checkout"),
        store.list_memories(project_source_id="local:/shop"),
        store.list_rules(project_source_id="local:/shop"),
    )
    assert [item.memory_key for item in recall.matched_memories] == [memory.key]
    hints = build_regression_hints(recall, store.list_memories(), store.list_rules())
    assert len(hints) == 1
    assert hints[0].expected_invariant == "You Pay"
    assert "not evidence that current code is broken" in hints[0].note.lower()
    assert all(candidate.status.value != "rejected" for candidate in [confirmed_candidate])

    unrelated = MemoryRecallEngine().recall(
        _knowledge(),
        _future_impact("/admin"),
        store.list_memories(project_source_id="local:/shop"),
        store.list_rules(project_source_id="local:/shop"),
    )
    assert unrelated.matched_memories == []
