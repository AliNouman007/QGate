from __future__ import annotations

import contextlib
import http.server
import threading
from pathlib import Path

import pytest
from qgate_browser_execution.compiler import ScenarioCompiler
from qgate_browser_execution.executor import BrowserExecutor
from qgate_browser_execution.models import ExecutionConfig, ExecutionStatus, FailureCategory
from qgate_project_intelligence.models import Confidence
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


def _plan(expected_text: str) -> ScenarioPlan:
    scenario = Scenario(
        key="scn_checkout",
        title="Checkout label",
        kind=ScenarioKind.STATE_VARIANT,
        priority=ScenarioPriority.P0,
        confidence=Confidence.HIGH,
        routes=["/index.html"],
        targets=["checkout"],
        states=["guest"],
        steps=[
            ScenarioStep(
                action=f'Assert text "{expected_text}"',
                expected=expected_text,
                route="/index.html",
            )
        ],
        reason="checkout label changed",
        source_impact_keys=["impact:checkout"],
        readiness=AutomationReadiness.READY,
    )
    return ScenarioPlan(
        metadata=ScenarioPlanMetadata(
            project_source_id="local:/fixture",
            project_fingerprint="fixture-fingerprint",
            impact_change_source_id="diff:fixture",
        ),
        budget=GenerationBudget(),
        summary=ScenarioSummary(total=1, ready=1, p0=1),
        scenarios=[scenario],
    )


@contextlib.contextmanager
def _server(root: Path):
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *args, directory=str(root), **kwargs
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_real_browser_distinguishes_pass_assertion_failure_and_environment_failure(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        """<!doctype html><html><head><title>Checkout</title></head>
<body><main><h1>Checkout</h1><div id='pay-label'>Total</div>
<script>console.log('fixture-ready')</script></main></body></html>""",
        encoding="utf-8",
    )
    executor = BrowserExecutor()
    with _server(tmp_path) as base_url:
        pass_request = ScenarioCompiler().compile_plan(
            _plan("Checkout"),
            ExecutionConfig(base_url=base_url, artifact_dir=str(tmp_path / "artifacts-pass")),
        )
        passed = await executor.run(pass_request)
        assert passed.scenarios[0].status == ExecutionStatus.PASSED
        assert passed.scenarios[0].verified is True

        fail_request = ScenarioCompiler().compile_plan(
            _plan("You Pay"),
            ExecutionConfig(base_url=base_url, artifact_dir=str(tmp_path / "artifacts-fail")),
        )
        failed = await executor.run(fail_request)
        assert failed.scenarios[0].status == ExecutionStatus.FAILED
        assert failed.scenarios[0].failure_category == FailureCategory.ASSERTION_FAILURE
        assert failed.scenarios[0].steps[-1].evidence.artifacts

    dead_request = ScenarioCompiler().compile_plan(
        _plan("Checkout"),
        ExecutionConfig(base_url="http://127.0.0.1:9", artifact_dir=str(tmp_path / "artifacts-dead")),
    )
    dead = await executor.run(dead_request)
    assert dead.scenarios[0].status == ExecutionStatus.EXECUTION_ERROR
    assert dead.scenarios[0].failure_category in {
        FailureCategory.ENVIRONMENT_FAILURE,
        FailureCategory.NAVIGATION_FAILURE,
    }
