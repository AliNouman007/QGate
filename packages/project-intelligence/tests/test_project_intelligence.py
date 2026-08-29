from __future__ import annotations

import zipfile
from pathlib import Path

from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.models import (
    AnalysisBudget,
    BehaviorCategory,
    FileRole,
    ProjectKnowledge,
    SemanticStateKind,
)
from qgate_project_intelligence.report import render_project_map
from qgate_project_intelligence.semantic import HeuristicSemanticClassifier, build_evidence_packs
from qgate_project_intelligence.source import LocalPathSource, ZipProjectSource
from qgate_project_intelligence.store import JsonKnowledgeStore


def _write_project(root: Path) -> None:
    (root / "src/components").mkdir(parents=True)
    (root / "src/pages").mkdir(parents=True)
    (root / "src/lib").mkdir(parents=True)
    (root / "node_modules/pkg").mkdir(parents=True)
    (root / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")
    (root / "src/lib/auth.ts").write_text(
        "export const isLoggedIn = () => Boolean(localStorage.getItem('token'));\n",
        encoding="utf-8",
    )
    (root / "src/components/Card.tsx").write_text(
        "import { isLoggedIn } from '../lib/auth';\n"
        "export function Card({loading, items}) {\n"
        "  if (!items) return null;\n"
        "  if (loading) return <span>Loading</span>;\n"
        "  if (isLoggedIn()) return <button>Save</button>;\n"
        "  if (window.matchMedia('(max-width: 640px)').matches) return <div>Mobile</div>;\n"
        "  return <div>{items.length === 0 ? 'Empty' : 'Ready'}</div>;\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "src/pages/home.tsx").write_text(
        "import { Card } from '../components/Card';\nexport const Home = () => <Card items={[]} />;\n",
        encoding="utf-8",
    )
    (root / "src/pages/search.tsx").write_text(
        "import { Card } from '../components/Card';\nexport const Search = () => <Card items={[]} />;\n",
        encoding="utf-8",
    )
    (root / "node_modules/pkg/index.js").write_text("ignored", encoding="utf-8")


def test_analysis_builds_bounded_structural_and_behavioral_map(tmp_path: Path) -> None:
    _write_project(tmp_path)
    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))

    paths = {file.record.path: file for file in knowledge.files}
    assert "node_modules/pkg/index.js" not in paths
    assert paths["src/pages/home.tsx"].record.role == FileRole.ROUTE
    assert paths["src/components/Card.tsx"].record.role == FileRole.COMPONENT
    assert knowledge.summary.languages["typescript"] == 4
    assert knowledge.summary.reused_modules["src/components/Card.tsx"] == 2

    card = paths["src/components/Card.tsx"]
    categories = {fact.category for fact in card.behaviors if fact.meaningful}
    assert BehaviorCategory.LOADING in categories
    assert BehaviorCategory.AUTH in categories
    assert BehaviorCategory.RESPONSIVE in categories
    guards = [fact for fact in card.behaviors if fact.category == BehaviorCategory.TECHNICAL_GUARD]
    assert guards and guards[0].meaningful is False

    dependency_pairs = {(edge.source, edge.target) for edge in knowledge.dependencies}
    assert ("src/pages/home.tsx", "src/components/Card.tsx") in dependency_pairs
    assert ("src/components/Card.tsx", "src/lib/auth.ts") in dependency_pairs


def test_literal_user_mode_branches_become_concrete_semantic_states(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/shop-context.js").write_text(
        "export function payable(userMode, total) {\n"
        "  if (userMode === 'guest') return total;\n"
        "  if (userMode === 'logged_in') return total - 5;\n"
        "  if (userMode === 'wallet') return total - 15;\n"
        "  return total;\n"
        "}\n",
        encoding="utf-8",
    )

    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))
    concrete = {
        state.label: state
        for state in knowledge.semantic_states
        if state.evidence and state.evidence[0].path == "src/shop-context.js"
    }

    assert "Guest" in concrete
    assert "Logged In" in concrete
    assert "Wallet" in concrete
    assert concrete["Wallet"].kind == SemanticStateKind.USER_STATE
    assert concrete["Wallet"].confidence.value in {"medium", "high"}
    assert concrete["Wallet"].evidence[0].line == 4


def test_budget_records_coverage_gap_instead_of_unbounded_scan(tmp_path: Path) -> None:
    for index in range(5):
        (tmp_path / f"file{index}.py").write_text(f"VALUE = {index}\n", encoding="utf-8")

    budget = AnalysisBudget(max_files=2, max_total_bytes=10_000, max_file_bytes=10_000, max_depth=8)
    knowledge = ProjectIntelligenceAnalyzer(budget).analyze(LocalPathSource(tmp_path))

    assert len(knowledge.files) == 2
    assert any(gap.reason == "max_files_exceeded" for gap in knowledge.coverage_gaps)


def test_incremental_analysis_reuses_unchanged_files(tmp_path: Path) -> None:
    _write_project(tmp_path)
    analyzer = ProjectIntelligenceAnalyzer()
    first = analyzer.analyze(LocalPathSource(tmp_path))

    (tmp_path / "src/pages/home.tsx").write_text(
        "import { Card } from '../components/Card';\nexport const Home = () => <Card items={[1]} />;\n",
        encoding="utf-8",
    )
    second = analyzer.analyze(LocalPathSource(tmp_path), previous=first)

    assert second.metadata.source_fingerprint != first.metadata.source_fingerprint
    assert second.metadata.reused_files == len(first.files) - 1
    assert second.metadata.analyzed_files == 1


def test_zip_source_store_semantic_packs_and_report(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write_project(project)
    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path in project.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(project))

    with ZipProjectSource(archive) as source:
        knowledge = ProjectIntelligenceAnalyzer().analyze(source)

    packs = build_evidence_packs(knowledge.files, max_facts_per_pack=2, max_packs=3)
    assert packs
    assert len(packs) <= 3
    assert all(len(pack.facts) <= 2 for pack in packs)
    classification = HeuristicSemanticClassifier().classify(packs[0])
    assert classification.evidence

    store_root = tmp_path / "qgate-data"
    stored = JsonKnowledgeStore(store_root).save(knowledge)
    assert stored.is_relative_to(store_root)
    assert not stored.is_relative_to(project)
    loaded = ProjectKnowledge.model_validate_json(stored.read_text(encoding="utf-8"))
    assert loaded.metadata.source_fingerprint == knowledge.metadata.source_fingerprint

    report = render_project_map(knowledge)
    assert "QGate Project Map" in report
    assert "Shared/reused modules" in report
    assert "Behavioral states/signals" in report
