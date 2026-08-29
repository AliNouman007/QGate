from pathlib import Path

import pytest
from qgate_project_intelligence.models import Confidence
from qgate_qa_memory.lifecycle import InvalidMemoryTransitionError, QAMemoryService
from qgate_qa_memory.models import (
    CandidateKind,
    CandidateStatus,
    MemoryCandidate,
    MemoryStatus,
    OccurrenceRef,
)
from qgate_qa_memory.signature import candidate_signature
from qgate_qa_memory.store import JsonQAMemoryStore


def _candidate(run_id: str = "run1") -> MemoryCandidate:
    item = MemoryCandidate(
        key=f"candidate_{run_id}",
        project_source_id="local:/shop",
        project_fingerprint="fp",
        title="Checkout label",
        invariant="Final payable must show You Pay",
        kind=CandidateKind.ASSERTION_REGRESSION,
        routes=["/checkout"],
        components=["CheckoutSummary"],
        states=["logged_in", "wallet"],
        source_execution_run_id=run_id,
        source_scenario_key="checkout_wallet",
        confidence=Confidence.HIGH,
        dedupe_signature="pending",
        occurrences=[OccurrenceRef(execution_run_id=run_id, scenario_key="checkout_wallet")],
    )
    item.dedupe_signature = candidate_signature(item)
    return item


def test_duplicate_candidate_links_occurrence_instead_of_duplicate_memory(tmp_path: Path) -> None:
    store = JsonQAMemoryStore(tmp_path)
    service = QAMemoryService(store)
    first = service.ingest_candidate(_candidate("run1"))
    second = service.ingest_candidate(_candidate("run2"))
    assert second.key == first.key
    assert len(store.list_candidates()) == 1
    assert {item.execution_run_id for item in second.occurrences} == {"run1", "run2"}


def test_human_confirmation_creates_trusted_memory_and_rule(tmp_path: Path) -> None:
    store = JsonQAMemoryStore(tmp_path)
    service = QAMemoryService(store)
    candidate = service.ingest_candidate(_candidate())
    reviewed, memory, rule = service.confirm_candidate(candidate.key, reviewer="qa@example.test")
    assert reviewed.status == CandidateStatus.CONFIRMED
    assert reviewed.confirmed_memory_key == memory.key
    assert memory.status == MemoryStatus.ACTIVE
    assert memory.confirmed_by == "qa@example.test"
    assert rule is not None and rule.source_memory_key == memory.key and rule.active

    with pytest.raises(InvalidMemoryTransitionError):
        service.reject_candidate(candidate.key, reviewer="qa@example.test")


def test_reject_does_not_create_memory_and_preserves_audit(tmp_path: Path) -> None:
    store = JsonQAMemoryStore(tmp_path)
    service = QAMemoryService(store)
    candidate = service.ingest_candidate(_candidate())
    rejected = service.reject_candidate(candidate.key, reviewer="qa@example.test", note="unreachable")
    assert rejected.status == CandidateStatus.REJECTED
    assert store.list_memories() == []
    assert any(event.action.value == "rejected" for event in store.list_audit())


def test_new_confirmation_after_deactivation_does_not_overwrite_history(tmp_path: Path) -> None:
    store = JsonQAMemoryStore(tmp_path)
    service = QAMemoryService(store)
    first_candidate = service.ingest_candidate(_candidate("run1"))
    _, first_memory, _ = service.confirm_candidate(first_candidate.key, reviewer="qa@example.test")
    service.deactivate_memory(first_memory.key, reviewer="qa@example.test", note="old expectation paused")

    replacement = _candidate("run2")
    replacement.key = "candidate_reintroduced"
    replacement.dedupe_signature = "distinct_reintroduction_signature"
    replacement = service.ingest_candidate(replacement)
    _, second_memory, _ = service.confirm_candidate(replacement.key, reviewer="qa@example.test")

    assert first_memory.key != second_memory.key
    stored_first = store.load_memory(first_memory.key)
    stored_second = store.load_memory(second_memory.key)
    assert stored_first is not None and stored_first.status == MemoryStatus.INACTIVE
    assert stored_second is not None and stored_second.status == MemoryStatus.ACTIVE
