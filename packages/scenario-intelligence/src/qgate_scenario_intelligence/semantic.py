from __future__ import annotations

from pydantic import BaseModel, Field

from .models import Scenario, ScenarioPlan


class ScenarioEvidencePack(BaseModel):
    key: str
    scenarios: list[Scenario] = Field(default_factory=list)


def build_scenario_evidence_packs(
    plan: ScenarioPlan,
    *,
    max_scenarios_per_pack: int = 4,
    max_packs: int = 20,
) -> list[ScenarioEvidencePack]:
    if max_scenarios_per_pack < 1 or max_packs < 1:
        raise ValueError("Scenario evidence-pack limits must be positive")
    packs: list[ScenarioEvidencePack] = []
    for start in range(0, len(plan.scenarios), max_scenarios_per_pack):
        if len(packs) >= max_packs:
            break
        chunk = plan.scenarios[start : start + max_scenarios_per_pack]
        if chunk:
            packs.append(ScenarioEvidencePack(key=f"scenario-pack-{len(packs) + 1}", scenarios=chunk))
    return packs
