from __future__ import annotations

from qgate_impact_analysis.engine import ImpactAnalyzer, TraversalLimits
from qgate_impact_analysis.models import ImpactLevel, ImpactTargetType
from qgate_impact_analysis.source import UnifiedDiffSource
from qgate_project_intelligence.models import (
    AnalysisMetadata,
    Confidence,
    DependencyEdge,
    Evidence,
    FileAnalysis,
    FileRecord,
    FileRole,
    ProjectKnowledge,
    ProjectSummary,
    RouteFact,
    SemanticState,
    SemanticStateKind,
    SymbolFact,
    SymbolKind,
)


def _file(path: str, role: FileRole, *, symbols: list[SymbolFact] | None = None, routes: list[RouteFact] | None = None) -> FileAnalysis:
    return FileAnalysis(
        record=FileRecord(path=path, size_bytes=100, content_hash=path, language="typescript", role=role),
        symbols=symbols or [],
        routes=routes or [],
    )


def _evidence(path: str, line: int, excerpt: str = "code") -> Evidence:
    return Evidence(path=path, line=line, excerpt=excerpt, kind="test")


def _knowledge() -> ProjectKnowledge:
    card = _file(
        "src/components/Card.tsx",
        FileRole.COMPONENT,
        symbols=[SymbolFact(name="Card", kind=SymbolKind.COMPONENT, exported=True, evidence=_evidence("src/components/Card.tsx", 5))],
    )
    search = _file(
        "src/app/search/page.tsx",
        FileRole.ROUTE,
        routes=[RouteFact(route="/search", router="next_app", kind="page", evidence=_evidence("src/app/search/page.tsx", 1))],
    )
    category = _file(
        "src/app/category/page.tsx",
        FileRole.ROUTE,
        routes=[RouteFact(route="/category", router="next_app", kind="page", evidence=_evidence("src/app/category/page.tsx", 1))],
    )
    unrelated = _file(
        "src/app/admin/page.tsx",
        FileRole.ROUTE,
        routes=[RouteFact(route="/admin", router="next_app", kind="page", evidence=_evidence("src/app/admin/page.tsx", 1))],
    )
    edges = [
        DependencyEdge(source=search.record.path, target=card.record.path, module="../../../components/Card", evidence=_evidence(search.record.path, 2, "import Card")),
        DependencyEdge(source=category.record.path, target=card.record.path, module="../../components/Card", evidence=_evidence(category.record.path, 2, "import Card")),
    ]
    state = SemanticState(
        key="card:no-rating",
        label="No rating state",
        kind=SemanticStateKind.DATA_STATE,
        explanation="Card can render without rating data.",
        confidence=Confidence.HIGH,
        evidence=[_evidence(card.record.path, 6, "if (!rating)")],
    )
    return ProjectKnowledge(
        metadata=AnalysisMetadata(source_id="local:/demo", source_fingerprint="abc123"),
        summary=ProjectSummary(total_files=4, reused_modules={card.record.path: 2}, route_count=3, component_count=1),
        files=[card, search, category, unrelated],
        dependencies=edges,
        semantic_states=[state],
    )


def test_shared_component_change_traces_dependents_routes_and_state_without_unrelated_route() -> None:
    patch = """diff --git a/src/components/Card.tsx b/src/components/Card.tsx
--- a/src/components/Card.tsx
+++ b/src/components/Card.tsx
@@ -5,2 +5,2 @@
-export function Card() { return null }
+export function Card() { return <div /> }
"""
    report = ImpactAnalyzer(_knowledge()).analyze(UnifiedDiffSource(patch).load())

    assert any(item.target == "Card" and item.level == ImpactLevel.DIRECT for item in report.direct_impacts)
    assert {item.target for item in report.indirect_impacts} == {
        "src/app/search/page.tsx",
        "src/app/category/page.tsx",
    }
    assert {item.target for item in report.affected_routes} == {"/search", "/category"}
    assert "/admin" not in {item.target for item in report.affected_routes}
    assert any(item.target == "No rating state" for item in report.affected_states)
    assert report.shared_groups[0].reuse_count == 2


def test_added_file_missing_from_knowledge_is_direct_change_plus_unknown_mapping() -> None:
    patch = """diff --git a/src/new.tsx b/src/new.tsx
new file mode 100644
--- /dev/null
+++ b/src/new.tsx
@@ -0,0 +1 @@
+export const New = () => <div />;
"""
    report = ImpactAnalyzer(_knowledge()).analyze(UnifiedDiffSource(patch).load())

    assert any(item.target == "src/new.tsx" and item.level == ImpactLevel.DIRECT for item in report.direct_impacts)
    assert any(item.target_type == ImpactTargetType.FILE and item.level == ImpactLevel.UNKNOWN for item in report.unknown_impacts)
    assert report.summary.runtime_verification_items >= 1


def test_reverse_traversal_is_cycle_safe_and_records_limit_gap() -> None:
    knowledge = _knowledge()
    knowledge.dependencies.append(
        DependencyEdge(source="src/components/Card.tsx", target="src/app/search/page.tsx", module="cycle", evidence=_evidence("src/components/Card.tsx", 1))
    )
    patch = """diff --git a/src/components/Card.tsx b/src/components/Card.tsx
--- a/src/components/Card.tsx
+++ b/src/components/Card.tsx
@@ -5 +5 @@
-old
+new
"""
    report = ImpactAnalyzer(knowledge, TraversalLimits(max_depth=1, max_nodes=20)).analyze(UnifiedDiffSource(patch).load())

    assert len(report.indirect_impacts) <= 2
    assert any(gap.reason == "traversal_depth_limit" for gap in report.coverage_gaps)
