from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from qgate_project_intelligence.models import (
    AnalysisMetadata,
    BehaviorCategory,
    BehaviorFact,
    Confidence,
    Evidence,
    ProjectKnowledge,
    ProjectSummary,
    SemanticState,
    SemanticStateKind,
)
from qgate_project_intelligence.semantic import EvidencePack
from suitest_agent import project_intelligence_semantic
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


@pytest.mark.asyncio
async def test_project_enrichment_augments_instead_of_overwriting_deterministic_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wallet_evidence = Evidence(
        path="app/shop-context.js",
        line=3,
        excerpt="user === 'wallet'",
        kind="literal_comparison",
    )
    deterministic_wallet = SemanticState(
        key="app/shop-context.js:user:wallet",
        label="Wallet",
        kind=SemanticStateKind.USER_STATE,
        explanation="Deterministic concrete state.",
        confidence=Confidence.HIGH,
        evidence=[wallet_evidence],
    )
    ai_generic = SemanticState(
        key="app/shop-context.js:0",
        label="Behavioral state",
        kind=SemanticStateKind.GENERAL,
        explanation="AI-enriched generic state.",
        confidence=Confidence.MEDIUM,
        evidence=[wallet_evidence],
        needs_runtime_verification=True,
    )
    knowledge = ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/demo", source_fingerprint="abc123"),
        summary=ProjectSummary(),
        files=[],
        semantic_states=[deterministic_wallet],
    )

    async def fake_enrich_evidence_packs(*args: object, **kwargs: object) -> list[SemanticState]:
        return [ai_generic]

    monkeypatch.setattr(
        project_intelligence_semantic,
        "enrich_evidence_packs",
        fake_enrich_evidence_packs,
    )

    result = await project_intelligence_semantic.enrich_project_knowledge(
        FakeProvider("{}"), model="test-model", knowledge=knowledge
    )

    by_key = {state.key: state for state in result.semantic_states}
    assert by_key[deterministic_wallet.key] == deterministic_wallet
    assert by_key[ai_generic.key] == ai_generic
