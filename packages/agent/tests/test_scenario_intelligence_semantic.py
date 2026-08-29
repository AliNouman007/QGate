from __future__ import annotations

import pytest
from qgate_project_intelligence.models import Confidence, Evidence
from qgate_scenario_intelligence.models import (
    AutomationReadiness,
    GenerationBudget,
    Scenario,
    ScenarioKind,
    ScenarioPlan,
    ScenarioPlanMetadata,
    ScenarioPriority,
    ScenarioStep,
    ScenarioSummary,
)
from suitest_agent.providers.base import CompletionResult, ModelCall
from suitest_agent.scenario_intelligence_semantic import enrich_scenario_plan


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


def _plan() -> ScenarioPlan:
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/demo",
            project_fingerprint="fp",
            impact_change_source_id="git:main...feature",
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=1, runtime_discovery=1, p3=1),
        scenarios=[
            Scenario(
                key="scn_runtime",
                title="Discover dynamic state",
                kind=ScenarioKind.RUNTIME_DISCOVERY,
                priority=ScenarioPriority.P3,
                confidence=Confidence.LOW,
                states=["dynamic"],
                steps=[ScenarioStep(action="Discover setup", expected="Concrete setup exists")],
                reason="Static reachability unknown",
                source_impact_keys=["unknown:dynamic"],
                evidence=[Evidence(path="src/x.tsx", line=4, excerpt="dynamic", kind="state")],
                readiness=AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED,
                needs_runtime_discovery=True,
            )
        ],
    )


@pytest.mark.asyncio
async def test_ai_cannot_invent_scenario_or_promote_runtime_scenario_to_ready() -> None:
    provider = _FakeProvider(
        '{"scenarios":['
        '{"key":"scn_runtime","title":"Clearer dynamic-state check","explanation":"Needs runtime setup",'
        '"priority_hint":"later","confidence":"high","readiness":"ready","needs_runtime_discovery":false},'
        '{"key":"invented","title":"Fake","explanation":"Fake","priority_hint":null,'
        '"confidence":"high","readiness":"ready","needs_runtime_discovery":false}]}'
    )
    enriched = await enrich_scenario_plan(provider, model="fake-model", plan=_plan())
    item = enriched.scenarios[0]
    assert item.title == "Clearer dynamic-state check"
    assert item.confidence == Confidence.LOW
    assert item.readiness == AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED
    assert item.needs_runtime_discovery is True
    assert len(enriched.scenarios) == 1
    assert provider.calls
    assert "src/x.tsx" in provider.calls[0].messages[-1].content


@pytest.mark.asyncio
async def test_malformed_ai_output_preserves_deterministic_plan() -> None:
    plan = _plan()
    enriched = await enrich_scenario_plan(_FakeProvider("not-json"), model="fake-model", plan=plan)
    assert enriched.model_dump() == plan.model_dump()
