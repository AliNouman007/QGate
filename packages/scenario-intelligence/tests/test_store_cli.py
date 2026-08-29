from __future__ import annotations

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
from qgate_scenario_intelligence.report import render_scenario_plan
from qgate_scenario_intelligence.store import JsonScenarioPlanStore


def _plan() -> ScenarioPlan:
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/demo",
            project_fingerprint="fp",
            impact_change_source_id="git:main...feature",
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=1, ready=1, p1=1),
        scenarios=[
            Scenario(
                key="scn_1",
                title="Verify /search",
                kind=ScenarioKind.SMOKE,
                priority=ScenarioPriority.P1,
                confidence=Confidence.HIGH,
                routes=["/search"],
                targets=["/search"],
                steps=[ScenarioStep(action="Open /search", expected="Search loads", route="/search")],
                reason="Direct impacted route",
                source_impact_keys=["route:/search"],
                evidence=[Evidence(path="src/app/search/page.tsx", line=1, excerpt="page", kind="route")],
                readiness=AutomationReadiness.READY,
            )
        ],
    )


def test_store_round_trip_and_stable_key(tmp_path) -> None:
    store = JsonScenarioPlanStore(tmp_path)
    plan = _plan()
    key = store.key_for(plan)
    store.save(plan)
    assert store.latest() == plan
    assert store.load_key(key) == plan
    assert store.key_for(plan) == key


def test_human_report_contains_priority_readiness_and_expectation() -> None:
    text = render_scenario_plan(_plan())
    assert "[P1] Verify /search" in text
    assert "Readiness: ready" in text
    assert "Expect: Search loads" in text
