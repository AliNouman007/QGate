"""Optional LLM enrichment for bounded Project Intelligence evidence packs.

The deterministic Project Intelligence package never depends on an LLM. This
adapter lives in the agent layer and can enrich one bounded EvidencePack at a
time through the existing provider contract. Model output never supplies source
evidence and cannot raise confidence above the deterministic supporting facts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError
from qgate_project_intelligence.models import Confidence, SemanticState, SemanticStateKind
from qgate_project_intelligence.semantic import EvidencePack, HeuristicSemanticClassifier

from suitest_agent.providers.base import ChatMessage, LLMProvider, ModelCall, ProviderError


class _AIClassification(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    kind: SemanticStateKind
    explanation: str = Field(min_length=1, max_length=600)
    confidence: Confidence
    needs_runtime_verification: bool


async def enrich_evidence_pack(
    provider: LLMProvider,
    *,
    model: str,
    pack: EvidencePack,
) -> SemanticState:
    """Classify one bounded pack, falling back safely on provider/shape failure."""
    fallback = HeuristicSemanticClassifier().classify(pack)
    call = ModelCall(
        model=model,
        temperature=0,
        max_tokens=600,
        messages=[
            ChatMessage(
                role="system",
                content=(
                    "You classify software QA states from supplied deterministic evidence. "
                    "Return JSON only with keys label, kind, explanation, confidence, "
                    "needs_runtime_verification. Never invent source facts. If evidence is "
                    "ambiguous or runtime reachability is unknown, set needs_runtime_verification=true. "
                    "Allowed kind values: user_state, access_state, feature_state, data_state, "
                    "viewport_state, runtime_state, technical, general. Allowed confidence: "
                    "high, medium, low."
                ),
            ),
            ChatMessage(role="user", content=pack.model_dump_json()),
        ],
    )
    try:
        result = await provider.complete(call)
        ai = _AIClassification.model_validate_json(result.content)
    except (ProviderError, ValidationError):
        return fallback.to_state()

    supporting_confidence = _supporting_confidence(pack)
    confidence = _clamp_confidence(ai.confidence, supporting_confidence)
    return SemanticState(
        key=pack.key,
        label=ai.label,
        kind=ai.kind,
        explanation=ai.explanation,
        confidence=confidence,
        evidence=pack.evidence,
        needs_runtime_verification=(
            ai.needs_runtime_verification
            or fallback.needs_runtime_verification
            or confidence == Confidence.LOW
        ),
    )


async def enrich_evidence_packs(
    provider: LLMProvider,
    *,
    model: str,
    packs: list[EvidencePack],
) -> list[SemanticState]:
    """Enrich already-bounded packs sequentially to keep provider use predictable."""
    states: list[SemanticState] = []
    for pack in packs:
        states.append(await enrich_evidence_pack(provider, model=model, pack=pack))
    return states


def _supporting_confidence(pack: EvidencePack) -> Confidence:
    meaningful = [fact.confidence for fact in pack.facts if fact.meaningful]
    if not meaningful:
        return Confidence.MEDIUM
    if Confidence.LOW in meaningful:
        return Confidence.LOW
    if all(confidence == Confidence.HIGH for confidence in meaningful):
        return Confidence.HIGH
    return Confidence.MEDIUM


def _clamp_confidence(ai: Confidence, supporting: Confidence) -> Confidence:
    rank = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
    return ai if rank[ai] <= rank[supporting] else supporting
