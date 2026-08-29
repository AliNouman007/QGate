from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .models import (
    AuditAction,
    CandidateStatus,
    ConfirmedMemory,
    MemoryAuditEvent,
    MemoryCandidate,
    MemoryStatus,
    RegressionRule,
)
from .signature import semantic_signature

if TYPE_CHECKING:
    from .store import JsonQAMemoryStore


class InvalidMemoryTransitionError(ValueError):
    pass


class QAMemoryService:
    def __init__(self, store: JsonQAMemoryStore) -> None:
        self.store = store

    def ingest_candidate(self, candidate: MemoryCandidate, *, actor: str = "qgate") -> MemoryCandidate:
        existing = self._find_by_signature(candidate.project_source_id, candidate.dedupe_signature)
        if existing is not None:
            known = {
                (item.execution_run_id, item.scenario_key, item.defect_id)
                for item in existing.occurrences
            }
            for occurrence in candidate.occurrences:
                key = (occurrence.execution_run_id, occurrence.scenario_key, occurrence.defect_id)
                if key not in known:
                    existing.occurrences.append(occurrence)
                    known.add(key)
            self.store.save_candidate(existing)
            self._audit(existing.key, "candidate", AuditAction.OCCURRENCE_LINKED, actor)
            return existing
        self.store.save_candidate(candidate)
        self._audit(candidate.key, "candidate", AuditAction.CREATED, actor)
        return candidate

    def confirm_candidate(
        self,
        key: str,
        *,
        reviewer: str,
        note: str | None = None,
        create_rule: bool = True,
    ) -> tuple[MemoryCandidate, ConfirmedMemory, RegressionRule | None]:
        candidate = self._required_candidate(key)
        if candidate.status != CandidateStatus.PENDING:
            raise InvalidMemoryTransitionError("only pending candidates can be confirmed")

        signature = semantic_signature(
            project_source_id=candidate.project_source_id,
            invariant=candidate.invariant,
            routes=candidate.routes,
            components=candidate.components,
            symbols=candidate.symbols,
            states=candidate.states,
        )
        memory = self._find_memory_by_signature(candidate.project_source_id, signature)
        if memory is None:
            memory = ConfirmedMemory(
                key=self._stable_key("memory", candidate.project_source_id, candidate.key),
                project_source_id=candidate.project_source_id,
                title=candidate.title,
                invariant=candidate.invariant,
                severity=candidate.severity,
                routes=candidate.routes,
                components=candidate.components,
                symbols=candidate.symbols,
                targets=candidate.targets,
                states=candidate.states,
                originating_candidate_keys=[candidate.key],
                source_defect_ids=[candidate.source_defect_id] if candidate.source_defect_id else [],
                source_execution_run_ids=[candidate.source_execution_run_id]
                if candidate.source_execution_run_id
                else [],
                source_scenario_keys=[candidate.source_scenario_key] if candidate.source_scenario_key else [],
                evidence=candidate.evidence,
                confidence=candidate.confidence,
                confirmed_by=reviewer,
                semantic_signature=signature,
            )
        else:
            self._merge_candidate_provenance(memory, candidate)
        self.store.save_memory(memory)

        rule = None
        if create_rule:
            rule = self._rule_for(memory)
            self.store.save_rule(rule)

        candidate.status = CandidateStatus.CONFIRMED
        candidate.reviewed_at = datetime.now(UTC)
        candidate.reviewed_by = reviewer
        candidate.review_note = note
        candidate.confirmed_memory_key = memory.key
        self.store.save_candidate(candidate)
        self._audit(candidate.key, "candidate", AuditAction.CONFIRMED, reviewer, note)
        return candidate, memory, rule

    def reject_candidate(self, key: str, *, reviewer: str, note: str | None = None) -> MemoryCandidate:
        candidate = self._required_candidate(key)
        if candidate.status != CandidateStatus.PENDING:
            raise InvalidMemoryTransitionError("only pending candidates can be rejected")
        candidate.status = CandidateStatus.REJECTED
        candidate.reviewed_at = datetime.now(UTC)
        candidate.reviewed_by = reviewer
        candidate.review_note = note
        self.store.save_candidate(candidate)
        self._audit(candidate.key, "candidate", AuditAction.REJECTED, reviewer, note)
        return candidate

    def supersede_memory(
        self, key: str, *, replacement_key: str, reviewer: str, note: str | None = None
    ) -> ConfirmedMemory:
        if key == replacement_key:
            raise InvalidMemoryTransitionError("memory cannot supersede itself")
        memory = self._required_memory(key)
        replacement = self._required_memory(replacement_key)
        if memory.project_source_id != replacement.project_source_id:
            raise InvalidMemoryTransitionError("replacement memory must belong to same project")
        if memory.status != MemoryStatus.ACTIVE:
            raise InvalidMemoryTransitionError("only active memories can be superseded")
        if replacement.status != MemoryStatus.ACTIVE:
            raise InvalidMemoryTransitionError("replacement memory must be active")
        memory.status = MemoryStatus.SUPERSEDED
        memory.superseded_by = replacement.key
        self.store.save_memory(memory)
        for rule in self.store.list_rules(project_source_id=memory.project_source_id):
            if rule.source_memory_key == memory.key:
                rule.active = False
                self.store.save_rule(rule)
        self._audit(memory.key, "memory", AuditAction.SUPERSEDED, reviewer, note)
        return memory

    def deactivate_memory(self, key: str, *, reviewer: str, note: str | None = None) -> ConfirmedMemory:
        memory = self._required_memory(key)
        if memory.status != MemoryStatus.ACTIVE:
            raise InvalidMemoryTransitionError("only active memories can be deactivated")
        memory.status = MemoryStatus.INACTIVE
        self.store.save_memory(memory)
        self._set_rules_active(memory.key, False)
        self._audit(memory.key, "memory", AuditAction.DEACTIVATED, reviewer, note)
        return memory

    def reactivate_memory(self, key: str, *, reviewer: str, note: str | None = None) -> ConfirmedMemory:
        memory = self._required_memory(key)
        if memory.status != MemoryStatus.INACTIVE:
            raise InvalidMemoryTransitionError("only inactive memories can be reactivated")
        memory.status = MemoryStatus.ACTIVE
        self.store.save_memory(memory)
        self._set_rules_active(memory.key, True)
        self._audit(memory.key, "memory", AuditAction.REACTIVATED, reviewer, note)
        return memory

    def _find_by_signature(self, project_source_id: str, signature: str) -> MemoryCandidate | None:
        return next(
            (
                candidate
                for candidate in self.store.list_candidates(project_source_id=project_source_id)
                if candidate.dedupe_signature == signature
            ),
            None,
        )

    def _find_memory_by_signature(self, project_source_id: str, signature: str) -> ConfirmedMemory | None:
        return next(
            (
                memory
                for memory in self.store.list_memories(project_source_id=project_source_id)
                if memory.semantic_signature == signature and memory.status == MemoryStatus.ACTIVE
            ),
            None,
        )

    def _required_candidate(self, key: str) -> MemoryCandidate:
        candidate = self.store.load_candidate(key)
        if candidate is None:
            raise KeyError(f"candidate not found: {key}")
        return candidate

    def _required_memory(self, key: str) -> ConfirmedMemory:
        memory = self.store.load_memory(key)
        if memory is None:
            raise KeyError(f"memory not found: {key}")
        return memory

    @staticmethod
    def _append_unique(values: list[str], value: str | None) -> None:
        if value and value not in values:
            values.append(value)

    def _merge_candidate_provenance(
        self, memory: ConfirmedMemory, candidate: MemoryCandidate
    ) -> None:
        self._append_unique(memory.originating_candidate_keys, candidate.key)
        self._append_unique(memory.source_defect_ids, candidate.source_defect_id)
        self._append_unique(memory.source_execution_run_ids, candidate.source_execution_run_id)
        self._append_unique(memory.source_scenario_keys, candidate.source_scenario_key)
        known_evidence = {(item.path, item.line, item.kind, item.excerpt) for item in memory.evidence}
        for evidence in candidate.evidence:
            identity = (evidence.path, evidence.line, evidence.kind, evidence.excerpt)
            if identity not in known_evidence:
                memory.evidence.append(evidence)
                known_evidence.add(identity)

    def _set_rules_active(self, memory_key: str, active: bool) -> None:
        for rule in self.store.list_rules():
            if rule.source_memory_key == memory_key:
                rule.active = active
                self.store.save_rule(rule)

    def _rule_for(self, memory: ConfirmedMemory) -> RegressionRule:
        return RegressionRule(
            key=self._stable_key("rule", memory.project_source_id, memory.key),
            source_memory_key=memory.key,
            project_source_id=memory.project_source_id,
            title=f"Regression: {memory.title}",
            routes=memory.routes,
            components=memory.components,
            symbols=memory.symbols,
            states=memory.states,
            preconditions=memory.states,
            expected_invariant=memory.invariant,
            scenario_objective=f"Re-verify historical regression invariant: {memory.invariant}",
            severity_hint=memory.severity,
            evidence=memory.evidence,
        )

    def _audit(
        self,
        entity_key: str,
        entity_type: str,
        action: AuditAction,
        actor: str,
        note: str | None = None,
    ) -> None:
        raw = f"{entity_type}\0{entity_key}\0{action.value}\0{actor}\0{datetime.now(UTC).isoformat()}"
        self.store.append_audit(
            MemoryAuditEvent(
                key=hashlib.sha256(raw.encode()).hexdigest()[:24],
                entity_type=entity_type,
                entity_key=entity_key,
                action=action,
                actor=actor,
                note=note,
            )
        )

    @staticmethod
    def _stable_key(prefix: str, project_source_id: str, identity: str) -> str:
        digest = hashlib.sha256(f"{project_source_id}\0{identity}".encode()).hexdigest()[:20]
        return f"{prefix}_{digest}"
