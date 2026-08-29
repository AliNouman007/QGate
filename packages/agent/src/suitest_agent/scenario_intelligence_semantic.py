"""Optional provider-backed enrichment for deterministic QGate Scenario Plans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError
from qgate_project_intelligence.models import Confidence
from qgate_scenario_intelligence.models import AutomationReadiness
from qgate_scenario_intelligence.semantic import build_scenario_evidence_packs

if TYPE_CHECKING:
    from qgate_scenario_intelligence.models import Scenario, ScenarioPlan

from suitest_agent.providers.base import ChatMessage, LLMProvider, ModelCall, ProviderError


class _AIScenarioItem(BaseModel):
    key: str
    title: str = Field(min_length=1, max_length=220)
    explanation: str = Field(min_length=1, max_length=700)
    priority_hint: str | None = Field(default=None, max_length=120)
    confidence: Confidence
    readiness: AutomationReadiness
    needs_runtime_discovery: bool


class _AIScenarioResponse(BaseModel):
    scenarios: list[_AIScenarioItem] = Field(default_factory=list)


async def enrich_scenario_plan(
    provider: LLMProvider,
    *,
    model: str,
    plan: ScenarioPlan,
    max_scenarios_per_pack: int = 4,
    max_packs: int = 20,
) -> ScenarioPlan:
    """Improve wording without allowing AI to invent or relax deterministic coverage."""
    enriched = plan.model_copy(deep=True)
    by_key = {item.key: item for item in enriched.scenarios}
    packs = build_scenario_evidence_packs(
        plan, max_scenarios_per_pack=max_scenarios_per_pack, max_packs=max_packs
    )
    for pack in packs:
        call = ModelCall(
            model=model,
            temperature=0,
            max_tokens=1400,
            messages=[
                ChatMessage(
                    role="system",
                    content=(
                        "You may only improve human-facing wording for already-created QA scenarios. "
                        "Return JSON only as {\"scenarios\":[{\"key\":...,\"title\":...,"
                        "\"explanation\":...,\"priority_hint\":null|string,\"confidence\":"
                        "\"high|medium|low\",\"readiness\":\"ready|runtime_discovery_required|manual_only|blocked_by_gap\","
                        "\"needs_runtime_discovery\":true|false}]}. Use only supplied keys. Do not add routes, "
                        "states, selectors, credentials, data, steps or scenarios. Never make a scenario more "
                        "executable than deterministic evidence allows."
                    ),
                ),
                ChatMessage(role="user", content=pack.model_dump_json()),
            ],
        )
        try:
            result = await provider.complete(call)
            response = _AIScenarioResponse.model_validate_json(result.content)
        except (ProviderError, ValidationError):
            continue
        allowed = {item.key for item in pack.scenarios}
        for ai_item in response.scenarios:
            if ai_item.key not in allowed:
                continue
            target = by_key.get(ai_item.key)
            if target is None:
                continue
            target.title = ai_item.title
            target.explanation = ai_item.explanation
            target.priority_hint = ai_item.priority_hint
            target.confidence = _clamp_confidence(ai_item.confidence, target.confidence)
            target.readiness = _clamp_readiness(ai_item.readiness, target.readiness)
            target.needs_runtime_discovery = (
                target.needs_runtime_discovery or ai_item.needs_runtime_discovery
            )
    return enriched


def _clamp_confidence(ai: Confidence, deterministic: Confidence) -> Confidence:
    rank = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
    return ai if rank[ai] <= rank[deterministic] else deterministic


def _clamp_readiness(ai: AutomationReadiness, deterministic: AutomationReadiness) -> AutomationReadiness:
    strictness = {
        AutomationReadiness.READY: 0,
        AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED: 1,
        AutomationReadiness.MANUAL_ONLY: 2,
        AutomationReadiness.BLOCKED_BY_GAP: 3,
    }
    return ai if strictness[ai] >= strictness[deterministic] else deterministic
