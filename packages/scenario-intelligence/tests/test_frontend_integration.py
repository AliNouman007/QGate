from __future__ import annotations

import subprocess
from pathlib import Path

from qgate_impact_analysis.engine import ImpactAnalyzer
from qgate_impact_analysis.source import LocalGitSource
from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.source import LocalPathSource
from qgate_scenario_intelligence.generator import ScenarioGenerator
from qgate_scenario_intelligence.models import ScenarioKind
from qgate_scenario_intelligence.store import JsonScenarioPlanStore


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_real_project_knowledge_impact_to_scenario_plan_pipeline(tmp_path: Path) -> None:
    repo = tmp_path / "frontend"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "qgate@example.test")
    _git(repo, "config", "user.name", "QGate Test")
    (repo / "src/components").mkdir(parents=True)
    (repo / "src/app/search").mkdir(parents=True)
    (repo / "src/app/category").mkdir(parents=True)
    (repo / "src/app/admin").mkdir(parents=True)
    (repo / "package.json").write_text(
        '{"dependencies":{"next":"15.0.0","react":"19.0.0"},"devDependencies":{"typescript":"5.7.0"}}',
        encoding="utf-8",
    )
    (repo / "src/components/Card.tsx").write_text(
        "export interface CardProps { rating?: number }\n"
        "export function Card({ rating }: CardProps) {\n"
        "  if (!rating) return <article>No rating</article>;\n"
        "  return <article>Rating: {rating}</article>;\n"
        "}\n",
        encoding="utf-8",
    )
    (repo / "src/app/search/page.tsx").write_text(
        "import { Card } from '../../components/Card';\nexport default function Search() { return <Card />; }\n",
        encoding="utf-8",
    )
    (repo / "src/app/category/page.tsx").write_text(
        "import { Card } from '../../components/Card';\nexport default function Category() { return <Card rating={5} />; }\n",
        encoding="utf-8",
    )
    (repo / "src/app/admin/page.tsx").write_text(
        "export default function Admin() { return <main>Admin</main>; }\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")

    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(repo))
    _git(repo, "checkout", "-b", "feature")
    (repo / "src/components/Card.tsx").write_text(
        "export interface CardProps { rating?: number }\n"
        "export function Card({ rating }: CardProps) {\n"
        "  if (!rating) return <article className='no-rating'>No rating</article>;\n"
        "  return <article className='has-rating'>Rating: {rating}</article>;\n"
        "}\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "change card state styling")

    impact = ImpactAnalyzer(knowledge).analyze(LocalGitSource(repo, base_ref="main", head_ref="feature").load())
    plan = ScenarioGenerator().generate(knowledge, impact)

    scenario_routes = {route for scenario in plan.scenarios for route in scenario.routes}
    assert "/search" in scenario_routes
    assert "/category" in scenario_routes
    assert "/admin" not in scenario_routes
    assert all(scenario.reason and scenario.evidence for scenario in plan.scenarios)
    assert any(scenario.kind in {ScenarioKind.ROUTE_REGRESSION, ScenarioKind.SMOKE} for scenario in plan.scenarios)

    store = JsonScenarioPlanStore(tmp_path / "plans")
    path = store.save(plan)
    loaded = JsonScenarioPlanStore.load_path(path)
    assert loaded.metadata.project_fingerprint == knowledge.metadata.source_fingerprint
    assert [scenario.key for scenario in loaded.scenarios] == [scenario.key for scenario in plan.scenarios]
