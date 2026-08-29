from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.models import FrameworkKind, SemanticStateKind, SymbolKind
from qgate_project_intelligence.semantic import build_evidence_packs
from qgate_project_intelligence.source import LocalPathSource
from qgate_project_intelligence.store import JsonKnowledgeStore


def _write_next_project(root: Path) -> None:
    (root / "src/app/products/[id]").mkdir(parents=True)
    (root / "src/components").mkdir(parents=True)
    (root / "src/pages").mkdir(parents=True)
    (root / "package.json").write_text(
        '{"dependencies":{"next":"15.0.0","react":"19.0.0"},"devDependencies":{"typescript":"5.7.0"}}',
        encoding="utf-8",
    )
    (root / "src/app/products/[id]/page.tsx").write_text(
        '"use client";\n'
        "import { useRouter, useSearchParams } from 'next/navigation';\n"
        "import { ProductCard } from '../../../components/ProductCard';\n"
        "export default function ProductPage() {\n"
        "  const router = useRouter();\n"
        "  const params = useSearchParams();\n"
        "  const loading = params.get('loading') === '1';\n"
        "  if (loading) return <div>Loading</div>;\n"
        "  return <ProductCard onOpen={() => router.push('/cart')} />;\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "src/components/ProductCard.tsx").write_text(
        "import { createContext, useMemo, useState } from 'react';\n"
        "export interface ProductCardProps { onOpen: () => void }\n"
        "export type ProductStatus = 'ready' | 'sold';\n"
        "export const ProductContext = createContext<string | null>(null);\n"
        "export function ProductCard({ onOpen }: ProductCardProps) {\n"
        "  const [selected, setSelected] = useState(false);\n"
        "  const label = useMemo(() => selected ? 'Selected' : 'Open', [selected]);\n"
        "  if (!onOpen) return null;\n"
        "  return <button onClick={() => { setSelected(true); onOpen(); }}>{label}</button>;\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "src/pages/account.tsx").write_text(
        "export default function Account() { return <div>Account</div>; }\n",
        encoding="utf-8",
    )


def test_react_next_and_typescript_facts_are_evidence_backed(tmp_path: Path) -> None:
    _write_next_project(tmp_path)
    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))
    by_path = {file.record.path: file for file in knowledge.files}

    page = by_path["src/app/products/[id]/page.tsx"]
    frameworks = {fact.framework for fact in page.frameworks}
    assert FrameworkKind.REACT in frameworks
    assert FrameworkKind.NEXTJS in frameworks
    assert FrameworkKind.TYPESCRIPT in frameworks
    assert any(fact.feature == "boundary" and fact.value == "client" for fact in page.frameworks)
    assert any(fact.feature == "runtime_api" and fact.value == "useRouter" for fact in page.frameworks)
    assert page.routes[0].route == "/products/:id"
    assert page.routes[0].router == "next_app"
    assert page.routes[0].dynamic is True

    component = by_path["src/components/ProductCard.tsx"]
    symbol_pairs = {(symbol.name, symbol.kind) for symbol in component.symbols}
    assert ("ProductCard", SymbolKind.COMPONENT) in symbol_pairs
    assert ("useState", SymbolKind.HOOK) in symbol_pairs
    assert ("ProductCardProps", SymbolKind.INTERFACE) in symbol_pairs
    assert ("ProductStatus", SymbolKind.TYPE_ALIAS) in symbol_pairs
    assert ("ProductContext", SymbolKind.CONTEXT) in symbol_pairs
    assert all(symbol.evidence.path for symbol in component.symbols)

    legacy_page = by_path["src/pages/account.tsx"]
    assert legacy_page.routes[0].route == "/account"
    assert legacy_page.routes[0].router == "next_pages"

    assert set(knowledge.summary.declared_frameworks) == {"nextjs", "react", "typescript"}
    assert knowledge.summary.frameworks["nextjs"] >= 1
    assert knowledge.summary.frameworks["react"] >= 1
    assert knowledge.summary.route_count == 2
    assert knowledge.summary.component_count >= 2
    assert knowledge.summary.hook_count >= 2


def test_pages_folder_without_next_evidence_is_not_promoted_to_nextjs(tmp_path: Path) -> None:
    (tmp_path / "src/pages").mkdir(parents=True)
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"react":"19.0.0"},"devDependencies":{"typescript":"5.7.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "src/pages/home.tsx").write_text(
        "export function Home() { return <main>Home</main>; }\n",
        encoding="utf-8",
    )

    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))
    page = next(file for file in knowledge.files if file.record.path == "src/pages/home.tsx")

    assert FrameworkKind.NEXTJS not in {fact.framework for fact in page.frameworks}
    assert page.routes == []
    assert "nextjs" not in knowledge.summary.declared_frameworks


def test_manifest_framework_change_invalidates_unchanged_frontend_analysis(tmp_path: Path) -> None:
    _write_next_project(tmp_path)
    analyzer = ProjectIntelligenceAnalyzer()
    first = analyzer.analyze(LocalPathSource(tmp_path))

    (tmp_path / "package.json").write_text(
        '{"dependencies":{"react":"19.0.0"},"devDependencies":{"typescript":"5.7.0"}}',
        encoding="utf-8",
    )
    second = analyzer.analyze(LocalPathSource(tmp_path), previous=first)
    by_path = {file.record.path: file for file in second.files}

    assert "nextjs" not in second.summary.declared_frameworks
    assert by_path["src/pages/account.tsx"].routes == []
    assert second.metadata.analyzed_files >= 4


def test_semantic_states_keep_evidence_and_framework_context(tmp_path: Path) -> None:
    _write_next_project(tmp_path)
    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))

    assert knowledge.semantic_states
    loading = next(state for state in knowledge.semantic_states if state.label == "Loading state")
    assert loading.kind == SemanticStateKind.DATA_STATE
    assert loading.evidence
    assert loading.confidence.value in {"high", "medium"}

    packs = build_evidence_packs(knowledge.files)
    page_pack = next(pack for pack in packs if pack.key.startswith("src/app/products/[id]/page.tsx"))
    assert any(fact.framework == FrameworkKind.NEXTJS for fact in page_pack.framework_context)


def test_store_lists_latest_and_loads_stable_key(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _write_next_project(first_root)
    _write_next_project(second_root)

    analyzer = ProjectIntelligenceAnalyzer()
    first = analyzer.analyze(LocalPathSource(first_root))
    second = analyzer.analyze(LocalPathSource(second_root))
    second.metadata.analyzed_at = first.metadata.analyzed_at + timedelta(microseconds=1)

    store = JsonKnowledgeStore(tmp_path / "knowledge")
    store.save(first)
    store.save(second)

    projects = store.list_projects()
    assert len(projects) == 2
    assert store.latest() is not None
    assert store.latest().metadata.source_id == second.metadata.source_id
    key = store.key_for(first.metadata.source_id)
    loaded = store.load_key(key)
    assert loaded is not None
    assert loaded.metadata.source_id == first.metadata.source_id
    assert store.load_key("../bad") is None
