from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from qgate_project_intelligence.models import (
    BehaviorCategory,
    BehaviorFact,
    Confidence,
    Evidence,
    SemanticStateKind,
)
from qgate_project_intelligence.semantic import EvidencePack
from suitest_agent.project_intelligence_semantic import enrich_evidence_pack
from suitest_agent.providers.base import CompletionResult, ModelCall, StreamChunk


class FakeProvider:
    name = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[ModelCall] = []

    async def complete(self, call: ModelCall) -> CompletionResult:
        self.calls.append(call)
        return CompletionResult(content=self.content, model=call.model)

    def stream_complete(self, call: ModelCall) -> AsyncIterator[StreamChunk]:
        async def stream() -> AsyncIterator[StreamChunk]:
            yield StreamChunk(done=True)

        return stream()

    def cost_usd(self, result: CompletionResult) -> float:
        return 0.0


def _pack() -> EvidencePack:
    evidence = Evidence(
        path="src/app/page.tsx",
        line=8,
        excerpt="if (loading) return <Spinner />",
        kind="condition",
    )
    fact = BehaviorFact(
        expression="loading",
        category=BehaviorCategory.LOADING,
        confidence=Confidence.MEDIUM,
        evidence=evidence,
        meaningful=True,
    )
    return EvidencePack(key="src/app/page.tsx:0", facts=[fact], evidence=[evidence])


@pytest.mark.asyncio
async def test_ai_semantic_enrichment_preserves_evidence_and_clamps_confidence() -> None:
    provider = FakeProvider(
        '{"label":"Page loading","kind":"data_state","explanation":"Loading gates the rendered page.",'
        '"confidence":"high","needs_runtime_verification":false}'
    )
    pack = _pack()

    state = await enrich_evidence_pack(provider, model="test-model", pack=pack)

    assert state.label == "Page loading"
    assert state.kind == SemanticStateKind.DATA_STATE
    assert state.confidence == Confidence.MEDIUM
    assert state.evidence == pack.evidence
    assert len(provider.calls) == 1
    assert pack.model_dump_json() in provider.calls[0].messages[1].content


@pytest.mark.asyncio
async def test_ai_semantic_enrichment_falls_back_on_invalid_model_output() -> None:
    provider = FakeProvider("not-json")

    state = await enrich_evidence_pack(provider, model="test-model", pack=_pack())

    assert state.label == "Loading state"
    assert state.kind == SemanticStateKind.DATA_STATE
    assert state.evidence
