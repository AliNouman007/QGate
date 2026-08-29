"""Optional provider-backed enrichment for deterministic QGate Impact Reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError
from qgate_impact_analysis.semantic import build_impact_evidence_packs
from qgate_project_intelligence.models import Confidence

if TYPE_CHECKING:
    from qgate_impact_analysis.models import ImpactItem, ImpactReport

from suitest_agent.providers.base import ChatMessage, LLMProvider, ModelCall, ProviderError


class _AIImpactItem(BaseModel):
    key: str
    explanation: str = Field(min_length=1, max_length=600)
    priority_hint: str | None = Field(default=None, max_length=120)
    confidence: Confidence
    needs_runtime_verification: bool


class _AIImpactResponse(BaseModel):
    items: list[_AIImpactItem] = Field(default_factory=list)


async def enrich_impact_report(
    provider: LLMProvider,
    *,
    model: str,
    report: ImpactReport,
    max_items_per_pack: int = 6,
    max_packs: int = 20,
) -> ImpactReport:
    """Enrich existing impact items without allowing AI to create impact targets."""
    enriched = report.model_copy(deep=True)
    by_key = _items_by_key(enriched)
    packs = build_impact_evidence_packs(
        report, max_items_per_pack=max_items_per_pack, max_packs=max_packs
    )
    for pack in packs:
        call = ModelCall(
            model=model,
            temperature=0,
            max_tokens=1200,
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "You explain already-determined software impact items. Return JSON only as "
                        "{\"items\":[{\"key\":...,\"explanation\":...,\"priority_hint\":null|string,"
                        "\"confidence\":\"high|medium|low\",\"needs_runtime_verification\":true|false}]}. "
                        "Use only keys supplied in the evidence pack. Do not add affected files, routes, states, "
                        "or relationships. Do not claim runtime reachability from static evidence."
                    ),
                ),
                ChatMessage(role="user", content=pack.model_dump_json()),
            ],
        )
        try:
            result = await provider.complete(call)
            response = _AIImpactResponse.model_validate_json(result.content)
        except (ProviderError, ValidationError):
            continue
        allowed = {item.key for item in pack.items}
        for ai_item in response.items:
            if ai_item.key not in allowed:
                continue
            target = by_key.get(ai_item.key)
            if target is None:
                continue
            target.explanation = ai_item.explanation
            target.priority_hint = ai_item.priority_hint
            target.confidence = _clamp_confidence(ai_item.confidence, target.confidence)
            target.needs_runtime_verification = (
                target.needs_runtime_verification or ai_item.needs_runtime_verification
            )
    enriched.summary.runtime_verification_items = sum(
        1 for item in by_key.values() if item.needs_runtime_verification
    ) + len(enriched.coverage_gaps)
    return enriched


def _items_by_key(report: ImpactReport) -> dict[str, ImpactItem]:
    result: dict[str, ImpactItem] = {}
    for collection in (
        report.direct_impacts,
        report.indirect_impacts,
        report.possible_impacts,
        report.unknown_impacts,
        report.affected_routes,
        report.affected_states,
    ):
        for item in collection:
            result[item.key] = item
    return result


def _clamp_confidence(ai: Confidence, deterministic: Confidence) -> Confidence:
    rank = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
    return ai if rank[ai] <= rank[deterministic] else deterministic
