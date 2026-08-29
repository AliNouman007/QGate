from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel, Field

from .models import BehaviorFact, Confidence, Evidence, FileAnalysis


class EvidencePack(BaseModel):
    key: str
    facts: list[BehaviorFact]
    evidence: list[Evidence]


class SemanticClassification(BaseModel):
    key: str
    label: str
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)
    needs_runtime_verification: bool = False


class SemanticClassifier(Protocol):
    def classify(self, pack: EvidencePack) -> SemanticClassification: ...


class HeuristicSemanticClassifier:
    def classify(self, pack: EvidencePack) -> SemanticClassification:
        meaningful = [fact for fact in pack.facts if fact.meaningful]
        if not meaningful:
            return SemanticClassification(
                key=pack.key,
                label="technical guard",
                confidence=Confidence.MEDIUM,
                evidence=pack.evidence,
                needs_runtime_verification=False,
            )
        categories = {fact.category.value for fact in meaningful}
        confidence = Confidence.HIGH if all(fact.confidence == Confidence.HIGH for fact in meaningful) else Confidence.MEDIUM
        return SemanticClassification(
            key=pack.key,
            label=" / ".join(sorted(categories)),
            confidence=confidence,
            evidence=pack.evidence,
            needs_runtime_verification=confidence == Confidence.LOW,
        )


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
        for start in range(0, len(file.behaviors), max_facts_per_pack):
            facts = file.behaviors[start : start + max_facts_per_pack]
            evidence = [fact.evidence for fact in facts]
            packs.append(EvidencePack(key=f"{file.record.path}:{start // max_facts_per_pack}", facts=facts, evidence=evidence))
            if len(packs) >= max_packs:
                return packs
    return packs
