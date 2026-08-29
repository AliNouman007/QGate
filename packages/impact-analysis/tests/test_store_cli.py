from __future__ import annotations

from pathlib import Path

from qgate_impact_analysis.engine import ImpactAnalyzer
from qgate_impact_analysis.report import render_impact_report
from qgate_impact_analysis.source import UnifiedDiffSource
from qgate_impact_analysis.store import JsonImpactStore
from qgate_project_intelligence.models import AnalysisMetadata, ProjectKnowledge, ProjectSummary


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
    return ImpactAnalyzer(knowledge).analyze(UnifiedDiffSource(patch, source_id="patch:test").load())


def test_store_round_trip_and_latest(tmp_path: Path) -> None:
    report = _report()
    store = JsonImpactStore(tmp_path / "impact")
    path = store.save(report)

    assert path.is_relative_to(tmp_path / "impact")
    key = store.key_for(report)
    loaded = store.load_key(key)
    assert loaded is not None
    assert loaded.metadata.project_fingerprint == "fingerprint"
    assert store.latest() is not None
    assert store.list_reports()
    assert store.load_key("../bad") is None


def test_human_report_surfaces_unknown_and_runtime_attention() -> None:
    text = render_impact_report(_report())
    assert "QGate Impact Report" in text
    assert "Direct impact" in text
    assert "Unknown impact" in text
    assert "runtime verification" in text
