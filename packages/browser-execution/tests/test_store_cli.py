from datetime import UTC, datetime

from qgate_browser_execution.models import (
    ExecutionMetadata,
    ExecutionReport,
    ExecutionStatus,
    ExecutionSummary,
    ScenarioExecution,
)
from qgate_browser_execution.report import render_execution_report
from qgate_browser_execution.store import JsonExecutionReportStore


def _report() -> ExecutionReport:
    return ExecutionReport(
        metadata=ExecutionMetadata(
            run_id="run-1",
            scenario_plan_key="plan-1",
            project_source_id="local:/demo",
            project_fingerprint="fingerprint",
            impact_change_source_id="diff:1",
            config_fingerprint="config",
            started_at=datetime.now(UTC),
        ),
        summary=ExecutionSummary(selected=1, executed=1, passed=1),
        scenarios=[
            ScenarioExecution(
                scenario_key="scn-1",
                title="Smoke checkout",
                kind="smoke",
                priority="P0",
                status=ExecutionStatus.PASSED,
                verified=True,
            )
        ],
    )


def test_execution_report_round_trip(tmp_path) -> None:
    store = JsonExecutionReportStore(tmp_path)
    report = _report()
    path = store.save(report)
    assert path.exists()
    loaded = store.load_key(store.key_for(report))
    assert loaded is not None
    assert loaded.model_dump() == report.model_dump()
    assert store.latest() is not None


def test_human_report_keeps_execution_status_separate() -> None:
    rendered = render_execution_report(_report())
    assert "PASSED" in rendered
    assert "Browser Execution & Evidence" in rendered
