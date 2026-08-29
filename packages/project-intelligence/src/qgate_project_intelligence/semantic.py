from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field

from .models import (
    BehaviorCategory,
    BehaviorFact,
    Confidence,
    Evidence,
    FileAnalysis,
    FrameworkFact,
    SemanticState,
    SemanticStateKind,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


class EvidencePack(BaseModel):
    key: str
    facts: list[BehaviorFact]
    framework_context: list[FrameworkFact] = Field(default_factory=list)
    evidence: list[Evidence]


class SemanticClassification(BaseModel):
    key: str
    label: str
    kind: SemanticStateKind
    explanation: str
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)
    needs_runtime_verification: bool = False

    def to_state(self) -> SemanticState:
        return SemanticState(**self.model_dump())


class SemanticClassifier(Protocol):
    def classify(self, pack: EvidencePack) -> SemanticClassification: ...


class HeuristicSemanticClassifier:
    def classify(self, pack: EvidencePack) -> SemanticClassification:
        meaningful = [fact for fact in pack.facts if fact.meaningful]
        if not meaningful:
            return SemanticClassification(
                key=pack.key,
                label="Technical guard",
                kind=SemanticStateKind.TECHNICAL,
                explanation="Only implementation guards were found in this evidence pack.",
                confidence=Confidence.MEDIUM,
                evidence=pack.evidence,
                needs_runtime_verification=False,
            )

        categories = Counter(fact.category for fact in meaningful)
        dominant = categories.most_common(1)[0][0]
        kind = _state_kind(dominant)
        framework_names = sorted({fact.framework.value for fact in pack.framework_context})
        framework_suffix = f" in {'/'.join(framework_names)} code" if framework_names else ""
        confidence = _bounded_confidence(meaningful)
        needs_runtime = dominant in {BehaviorCategory.GENERAL, BehaviorCategory.RESPONSIVE}
        label = _label_for(dominant)
        explanation = (
            f"Evidence suggests a {label.lower()} state{framework_suffix}. "
            "This label summarizes deterministic conditions; runtime behavior still controls QA truth."
        )
        return SemanticClassification(
            key=pack.key,
            label=label,
            kind=kind,
            explanation=explanation,
            confidence=confidence,
            evidence=pack.evidence,
            needs_runtime_verification=needs_runtime or confidence == Confidence.LOW,
        )


def classify_evidence_packs(
    packs: Iterable[EvidencePack],
    classifier: SemanticClassifier | None = None,
) -> list[SemanticState]:
    active = classifier or HeuristicSemanticClassifier()
    return [active.classify(pack).to_state() for pack in packs]


def build_evidence_packs(
    files: Iterable[FileAnalysis],
    *,
    max_facts_per_pack: int = 20,
    max_packs: int = 500,
) -> list[EvidencePack]:
    if max_facts_per_pack < 1 or max_packs < 1:
        raise ValueError("Evidence pack limits must be positive")
    packs: list[EvidencePack] = []
    for file in files:
        if not file.behaviors:
            continue
        framework_context = file.frameworks[:20]
        for start in range(0, len(file.behaviors), max_facts_per_pack):
            facts = file.behaviors[start : start + max_facts_per_pack]
            evidence = [fact.evidence for fact in facts]
            packs.append(
                EvidencePack(
                    key=f"{file.record.path}:{start // max_facts_per_pack}",
                    facts=facts,
                    framework_context=framework_context,
                    evidence=evidence,
                )
            )
            if len(packs) >= max_packs:
                return packs
    return packs


def _bounded_confidence(facts: list[BehaviorFact]) -> Confidence:
    if facts and all(fact.confidence == Confidence.HIGH for fact in facts):
        return Confidence.HIGH
    if any(fact.confidence == Confidence.LOW for fact in facts):
        return Confidence.LOW
    return Confidence.MEDIUM


def _state_kind(category: BehaviorCategory) -> SemanticStateKind:
    mapping = {
        BehaviorCategory.AUTH: SemanticStateKind.USER_STATE,
        BehaviorCategory.PERMISSION: SemanticStateKind.ACCESS_STATE,
        BehaviorCategory.FEATURE_FLAG: SemanticStateKind.FEATURE_STATE,
        BehaviorCategory.LOADING: SemanticStateKind.DATA_STATE,
        BehaviorCategory.ERROR: SemanticStateKind.DATA_STATE,
        BehaviorCategory.EMPTY: SemanticStateKind.DATA_STATE,
        BehaviorCategory.STORAGE: SemanticStateKind.RUNTIME_STATE,
        BehaviorCategory.RESPONSIVE: SemanticStateKind.VIEWPORT_STATE,
        BehaviorCategory.TECHNICAL_GUARD: SemanticStateKind.TECHNICAL,
        BehaviorCategory.GENERAL: SemanticStateKind.GENERAL,
    }
    return mapping[category]


def _label_for(category: BehaviorCategory) -> str:
    labels = {
        BehaviorCategory.AUTH: "Authentication state",
        BehaviorCategory.PERMISSION: "Permission state",
        BehaviorCategory.FEATURE_FLAG: "Feature variation",
        BehaviorCategory.LOADING: "Loading state",
        BehaviorCategory.ERROR: "Error state",
        BehaviorCategory.EMPTY: "Empty-data state",
        BehaviorCategory.STORAGE: "Client storage state",
        BehaviorCategory.RESPONSIVE: "Viewport state",
        BehaviorCategory.GENERAL: "Behavioral state",
        BehaviorCategory.TECHNICAL_GUARD: "Technical guard",
    }
    return labels[category]
