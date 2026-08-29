from __future__ import annotations

import subprocess
from pathlib import Path

from qgate_impact_analysis.engine import ImpactAnalyzer
from qgate_impact_analysis.source import LocalGitSource
from qgate_impact_analysis.store import JsonImpactStore
from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.source import LocalPathSource


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _write_frontend(repo: Path) -> None:
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
        "  return <article>{rating}</article>;\n"
        "}\n",
        encoding="utf-8",
    )
    (repo / "src/app/search/page.tsx").write_text(
        "import { Card } from '../../components/Card';\n"
        "export default function Search() { return <Card />; }\n",
        encoding="utf-8",
    )
    (repo / "src/app/category/page.tsx").write_text(
        "import { Card } from '../../components/Card';\n"
        "export default function Category() { return <Card rating={5} />; }\n",
        encoding="utf-8",
    )
    (repo / "src/app/admin/page.tsx").write_text(
        "export default function Admin() { return <main>Admin</main>; }\n",
        encoding="utf-8",
    )


def test_reused_react_component_change_produces_evidence_backed_blast_radius(tmp_path: Path) -> None:
    repo = tmp_path / "frontend"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "qgate@example.test")
    _git(repo, "config", "user.name", "QGate Test")
    _write_frontend(repo)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")

    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(repo))
    _git(repo, "checkout", "-b", "feature")
    (repo / "src/components/Card.tsx").write_text(
        "export interface CardProps { rating?: number }\n"
        "export function Card({ rating }: CardProps) {\n"
        "  if (!rating) return <article className='no-rating'>No rating</article>;\n"
        "  return <article>{rating}</article>;\n"
        "}\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "style no-rating card")

    change_set = LocalGitSource(repo, base_ref="main", head_ref="feature").load()
    report = ImpactAnalyzer(knowledge).analyze(change_set)

    assert [file.path for file in report.change_set.files] == ["src/components/Card.tsx"]
    assert any(symbol.symbol_name == "Card" for symbol in report.changed_symbols)
    assert {item.target for item in report.affected_routes} == {"/search", "/category"}
    assert "/admin" not in {item.target for item in report.affected_routes}
    assert {item.target for item in report.indirect_impacts} == {
        "src/app/search/page.tsx",
        "src/app/category/page.tsx",
    }
    assert report.shared_groups and report.shared_groups[0].reuse_count >= 2
    assert all(item.evidence for item in [*report.direct_impacts, *report.indirect_impacts, *report.affected_routes])

    store = JsonImpactStore(tmp_path / "impact-store")
    path = store.save(report)
    loaded = JsonImpactStore.load_path(path)
    assert loaded.metadata.project_fingerprint == knowledge.metadata.source_fingerprint
    assert {item.target for item in loaded.affected_routes} == {"/search", "/category"}
