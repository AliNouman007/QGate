from __future__ import annotations

from pathlib import Path

from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.source import LocalPathSource


def test_directive_prefixed_same_line_imports_build_dependency_edges(tmp_path: Path) -> None:
    app = tmp_path / "app"
    checkout = app / "checkout"
    checkout.mkdir(parents=True)

    (app / "shop-context.js").write_text(
        "export function useShop() { return {}; }\n",
        encoding="utf-8",
    )
    (app / "components.js").write_text(
        "export function Money() { return null; }\n",
        encoding="utf-8",
    )
    (checkout / "page.js").write_text(
        "'use client';import Link from'next/link';import{useShop}from'../shop-context';"
        "import{Money}from'../components';export default function Checkout(){return null;}\n",
        encoding="utf-8",
    )

    knowledge = ProjectIntelligenceAnalyzer().analyze(LocalPathSource(tmp_path))

    checkout_analysis = next(
        file for file in knowledge.files if file.record.path == "app/checkout/page.js"
    )
    assert {fact.module for fact in checkout_analysis.imports} >= {
        "next/link",
        "../shop-context",
        "../components",
    }

    dependency_pairs = {(edge.source, edge.target) for edge in knowledge.dependencies}
    assert ("app/checkout/page.js", "app/shop-context.js") in dependency_pairs
    assert ("app/checkout/page.js", "app/components.js") in dependency_pairs
