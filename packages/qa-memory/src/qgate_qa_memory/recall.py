from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from qgate_impact_analysis.models import ImpactLevel, ImpactReport, ImpactTargetType

from .models import (
    ConfirmedMemory,
    MemoryRecallGap,
    MemoryRecallResult,
    MemoryStatus,
    RecallBudget,
    RecalledMemoryMatch,
    RecalledRuleMatch,
    RegressionRule,
)

if TYPE_CHECKING:
    from qgate_project_intelligence.models import ProjectKnowledge


class MemoryRecallInputMismatchError(ValueError):
    pass


class MemoryRecallEngine:
    def recall(
        self,
        knowledge: ProjectKnowledge,
        impact: ImpactReport,
        memories: list[ConfirmedMemory],
        rules: list[RegressionRule],
        *,
        budget: RecallBudget | None = None,
    ) -> MemoryRecallResult:
        if knowledge.metadata.source_id != impact.metadata.project_source_id:
            raise MemoryRecallInputMismatchError("project source ids do not match")
        if knowledge.metadata.source_fingerprint != impact.metadata.project_fingerprint:
            raise MemoryRecallInputMismatchError("project fingerprints do not match")

        recall_budget = budget or RecallBudget()
        active_memories = [
            memory
            for memory in memories
            if memory.project_source_id == knowledge.metadata.source_id
            and memory.status == MemoryStatus.ACTIVE
        ]
        active_memory_keys = {memory.key for memory in active_memories}
        active_rules = [
            rule
            for rule in rules
            if rule.project_source_id == knowledge.metadata.source_id
            and rule.active
            and rule.source_memory_key in active_memory_keys
        ]

        memory_matches = [
            match
            for memory in active_memories
            if (match := self._score_memory(memory, knowledge, impact)) is not None
        ]
        memory_matches.sort(key=lambda item: (-item.score, item.memory_key))

        score_by_memory = {item.memory_key: item.score for item in memory_matches}
        reasons_by_memory = {item.memory_key: item.reasons for item in memory_matches}
        rule_matches = [
            RecalledRuleMatch(
                rule_key=rule.key,
                source_memory_key=rule.source_memory_key,
                score=score_by_memory[rule.source_memory_key],
                reasons=reasons_by_memory[rule.source_memory_key],
                evidence=rule.evidence[: recall_budget.max_evidence_per_item],
            )
            for rule in active_rules
            if rule.source_memory_key in score_by_memory
        ]
        rule_matches.sort(key=lambda item: (-item.score, item.rule_key))

        gaps: list[MemoryRecallGap] = []
        if len(memory_matches) > recall_budget.max_memories:
            gaps.append(
                MemoryRecallGap(
                    reason="memory_recall_truncated",
                    detail=f"{len(memory_matches)} matches exceeded max_memories={recall_budget.max_memories}",
                )
            )
        if len(rule_matches) > recall_budget.max_rules:
            gaps.append(
                MemoryRecallGap(
                    reason="rule_recall_truncated",
                    detail=f"{len(rule_matches)} matches exceeded max_rules={recall_budget.max_rules}",
                )
            )

        return MemoryRecallResult(
            project_source_id=knowledge.metadata.source_id,
            project_fingerprint=knowledge.metadata.source_fingerprint,
            impact_change_source_id=impact.metadata.change_source_id,
            generated_at=datetime.now(UTC),
            matched_memories=memory_matches[: recall_budget.max_memories],
            matched_rules=rule_matches[: recall_budget.max_rules],
            coverage_gaps=gaps,
            budget=recall_budget,
        )

    def _score_memory(
        self,
        memory: ConfirmedMemory,
        knowledge: ProjectKnowledge,
        impact: ImpactReport,
    ) -> RecalledMemoryMatch | None:
        impacted = (
            impact.direct_impacts
            + impact.indirect_impacts
            + impact.possible_impacts
            + impact.unknown_impacts
        )
        impacted_routes = {item.target for item in impact.affected_routes}
        impacted_states = {item.target for item in impact.affected_states}
        impacted_symbols = {
            item.target
            for item in impacted
            if item.target_type in {ImpactTargetType.SYMBOL, ImpactTargetType.COMPONENT, ImpactTargetType.MODULE}
        }
        changed_symbols = {item.symbol_name for item in impact.changed_symbols}

        score = 0
        reasons: list[str] = []
        symbol_matches = set(memory.symbols + memory.components) & (impacted_symbols | changed_symbols)
        state_matches = set(memory.states) & impacted_states
        route_matches = set(memory.routes) & impacted_routes

        if symbol_matches and state_matches:
            score += 100
            reasons.append("same symbol/component + state")
        elif route_matches and state_matches:
            score += 85
            reasons.append("same route + state")
        elif symbol_matches:
            score += 65
            reasons.append("same symbol/component")
        elif route_matches:
            score += 50
            reasons.append("same route")

        dependency_files = self._dependency_related_files(memory, knowledge)
        impacted_files = {
            item.target
            for item in impacted
            if item.target_type in {ImpactTargetType.FILE, ImpactTargetType.MODULE}
        }
        if dependency_files & impacted_files:
            score += 25
            reasons.append("dependency-supported relationship")

        strongest_level = self._strongest_level_for(memory, impacted)
        if strongest_level == ImpactLevel.DIRECT:
            score += 20
            reasons.append("direct current impact")
        elif strongest_level == ImpactLevel.INDIRECT:
            score += 10
            reasons.append("indirect current impact")
        elif strongest_level == ImpactLevel.POSSIBLE:
            score += 3
            reasons.append("possible current impact")

        severity_bonus = {
            "critical": 8,
            "high": 6,
            "medium": 3,
            "low": 1,
            "unknown": 0,
        }[memory.severity.value]
        score += severity_bonus

        confidence_bonus = {"high": 5, "medium": 3, "low": 1}[memory.confidence.value]
        score += confidence_bonus

        if score < 25:
            return None
        return RecalledMemoryMatch(
            memory_key=memory.key,
            score=score,
            reasons=reasons,
            evidence=memory.evidence,
        )

    @staticmethod
    def _strongest_level_for(memory: ConfirmedMemory, impacted: list[Any]) -> ImpactLevel | None:
        targets = set(memory.symbols + memory.components + memory.routes + memory.states + memory.targets)
        levels = [item.level for item in impacted if item.target in targets]
        for level in (ImpactLevel.DIRECT, ImpactLevel.INDIRECT, ImpactLevel.POSSIBLE, ImpactLevel.UNKNOWN):
            if level in levels:
                return level
        return None

    @staticmethod
    def _dependency_related_files(memory: ConfirmedMemory, knowledge: ProjectKnowledge) -> set[str]:
        needles = set(memory.symbols + memory.components + memory.targets)
        related: set[str] = set()
        for file_analysis in knowledge.files:
            if any(symbol.name in needles for symbol in file_analysis.symbols):
                related.add(file_analysis.record.path)
        changed = True
        while changed:
            changed = False
            for edge in knowledge.dependencies:
                if edge.source in related or edge.target in related:
                    before = len(related)
                    related.add(edge.source)
                    related.add(edge.target)
                    changed = changed or len(related) > before
        return related
