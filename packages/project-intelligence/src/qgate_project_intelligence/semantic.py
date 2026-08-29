from __future__ import annotations

import re
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

_LITERAL_COMPARISON = re.compile(
    r"(?P<left>[A-Za-z_$][\w.$]*)\s*(?:===|==|!==|!=)\s*"
    r"(?P<quote>['\"])(?P<value>[^'\"]{1,64})(?P=quote)"
)
_REVERSE_LITERAL_COMPARISON = re.compile(
    r"(?P<quote>['\"])(?P<value>[^'\"]{1,64})(?P=quote)\s*"
    r"(?:===|==|!==|!=)\s*(?P<left>[A-Za-z_$][\w.$]*)"
)
_USER_HINTS = ("user", "customer", "account", "login", "logged", "auth", "member")
_ACCESS_HINTS = ("role", "permission", "access", "owner", "admin")
_FEATURE_HINTS = ("variant", "experiment", "feature", "flag", "abtest")


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


def derive_concrete_branch_states(
    files: Iterable[FileAnalysis], *, max_states: int = 200
) -> list[SemanticState]:
    """Derive explicit branch variants from comparisons like ``userMode === 'wallet'``.

    Generic behavior packs remain useful for broad project understanding, but equality
    branches carry stronger state identity. These states retain source evidence and are
    bounded so arbitrary string-heavy files cannot explode scenario generation.
    """
    if max_states < 1:
        raise ValueError("max_states must be positive")
    states: list[SemanticState] = []
    seen: set[tuple[str, str, int]] = set()
    for file in files:
        for fact in file.behaviors:
            if not fact.meaningful:
                continue
            match = _LITERAL_COMPARISON.search(fact.expression) or _REVERSE_LITERAL_COMPARISON.search(
                fact.expression
            )
            if match is None:
                continue
            variable = match.group("left")
            value = match.group("value").strip()
            if not value or _looks_non_state_literal(value):
                continue
            dedupe_key = (file.record.path, variable, fact.evidence.line)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            label = _humanize_state_value(value)
            kind = _kind_for_branch_variable(variable, fact.category)
            states.append(
                SemanticState(
                    key=f"{file.record.path}:{variable}:{value}",
                    label=label,
                    kind=kind,
                    explanation=(
                        f"Source branch compares {variable} with literal state {value!r}; "
                        "runtime setup still requires evidence for how that state is activated."
                    ),
                    confidence=(
                        Confidence.HIGH
                        if fact.confidence == Confidence.HIGH
                        else Confidence.MEDIUM
                    ),
                    evidence=[fact.evidence],
                    needs_runtime_verification=False,
                )
            )
            if len(states) >= max_states:
                return states
    return states


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


def _kind_for_branch_variable(variable: str, category: BehaviorCategory) -> SemanticStateKind:
    normalized = variable.lower()
    if any(token in normalized for token in _USER_HINTS):
        return SemanticStateKind.USER_STATE
    if any(token in normalized for token in _ACCESS_HINTS):
        return SemanticStateKind.ACCESS_STATE
    if any(token in normalized for token in _FEATURE_HINTS):
        return SemanticStateKind.FEATURE_STATE
    if category == BehaviorCategory.AUTH:
        return SemanticStateKind.USER_STATE
    if category == BehaviorCategory.PERMISSION:
        return SemanticStateKind.ACCESS_STATE
    if category == BehaviorCategory.FEATURE_FLAG:
        return SemanticStateKind.FEATURE_STATE
    return SemanticStateKind.GENERAL


def _humanize_state_value(value: str) -> str:
    normalized = re.sub(r"[_-]+", " ", value).strip()
    return " ".join(part.capitalize() for part in normalized.split()) or value


def _looks_non_state_literal(value: str) -> bool:
    lowered = value.lower()
    return (
        len(value) > 64
        or lowered.startswith(("http://", "https://", "/"))
        or "@" in value
        or "\n" in value
    )


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
