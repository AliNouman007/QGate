from __future__ import annotations

from qgate_impact_analysis.engine import ImpactAnalyzer
from qgate_impact_analysis.source import UnifiedDiffSource
from qgate_project_intelligence.models import AnalysisMetadata, ProjectKnowledge, ProjectSummary
from suitest_agent.impact_analysis_semantic import enrich_impact_report
from suitest_agent.providers.base import CompletionResult, ModelCall


class _FakeProvider:
    name = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[ModelCall] = []

    async def complete(self, call: ModelCall) -> CompletionResult:
        self.calls.append(call)
        return CompletionResult(content=self.content, model=call.model)

    def cost_usd(self, result: CompletionResult) -> float:
        return 0.0


def _report():
    knowledge = ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/demo", source_fingerprint="fingerprint"),
        summary=ProjectSummary(),
        files=[],
    )
    patch = """diff --git a/new.ts b/new.ts
new file mode 100644
--- /dev/null
+++ b/new.ts
@@ -0,0 +1 @@
+export const x = 1;
"""
    return ImpactAnalyzer(knowledge).analyze(UnifiedDiffSource(patch).load())


async def test_ai_can_only_enrich_existing_keys_and_cannot_raise_confidence_or_remove_runtime_flag() -> None:
    report = _report()
    unknown = report.unknown_impacts[0]
    provider = _FakeProvider(
        '{"items":['
        f'{{"key":"{unknown.key}","explanation":"Needs runtime confirmation",'
        '"priority_hint":"high","confidence":"high","needs_runtime_verification":false},'
        '{"key":"invented:file","explanation":"fake","priority_hint":null,'
        '"confidence":"high","needs_runtime_verification":false}]}'
    )

    enriched = await enrich_impact_report(provider, model="fake-model", report=report, max_items_per_pack=20)
    enriched_unknown = enriched.unknown_impacts[0]

    assert enriched_unknown.explanation == "Needs runtime confirmation"
    assert enriched_unknown.confidence.value == "low"
    assert enriched_unknown.needs_runtime_verification is True
    assert all(item.key != "invented:file" for item in enriched.unknown_impacts)
    assert provider.calls
    assert "new.ts" in provider.calls[0].messages[-1].content


async def test_malformed_ai_output_falls_back_to_deterministic_report() -> None:
    report = _report()
    provider = _FakeProvider("not-json")
    enriched = await enrich_impact_report(provider, model="fake-model", report=report)
    assert enriched.model_dump() == report.model_dump()
