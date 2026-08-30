from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from suitest_lifecycle.frontend_runtime import ensure_browser

if TYPE_CHECKING:
    from playwright.async_api import Browser, Locator, Page

from .classification import assertion_failure, classify_exception
from .evidence import capture_page_evidence
from .models import (
    AttemptRecord,
    CompiledScenario,
    CompiledStep,
    ConsoleEvidence,
    ExecutionCoverageGap,
    ExecutionMetadata,
    ExecutionReport,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionSummary,
    FailureCategory,
    NetworkEvidence,
    OperationKind,
    ScenarioExecution,
    StepEvidence,
    StepExecution,
)
from .redaction import redact_url
from .resolver import resolve_target


class BrowserExecutor:
    async def run(self, request: ExecutionRequest) -> ExecutionReport:
        started = datetime.now(UTC)
        run_id = uuid.uuid4().hex
        report = ExecutionReport(
            metadata=ExecutionMetadata(
                run_id=run_id,
                scenario_plan_key=request.scenario_plan_key,
                project_source_id=request.project_source_id,
                project_fingerprint=request.project_fingerprint,
                impact_change_source_id=request.impact_change_source_id,
                config_fingerprint=self._config_fingerprint(request),
                started_at=started,
            ),
            summary=ExecutionSummary(selected=len(request.scenarios) + len(request.preclassified)),
        )
        for item in request.preclassified:
            report.scenarios.append(
                ScenarioExecution(
                    scenario_key=item.scenario_key,
                    title=item.title,
                    kind="preclassified",
                    priority="",
                    status=item.status,
                    verified=False,
                    detail=item.reason,
                )
            )

        browser_status = ensure_browser(auto_install=True)
        if not browser_status.ready:
            for scenario in request.scenarios:
                report.scenarios.append(
                    self._browser_failure(scenario, f"Browser unavailable: {browser_status.detail}")
                )
            report.coverage_gaps.append(
                ExecutionCoverageGap(reason="browser_unavailable", detail=browser_status.detail)
            )
            return self._finish(report)

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser_type = getattr(playwright, request.config.browser, playwright.chromium)
                browser = await browser_type.launch(headless=not request.config.headed)
                try:
                    for scenario in request.scenarios:
                        report.scenarios.append(
                            await self._run_scenario(browser, request, scenario, run_id)
                        )
                finally:
                    await browser.close()
        except Exception as exc:
            existing = {item.scenario_key for item in report.scenarios}
            for scenario in request.scenarios:
                if scenario.scenario_key not in existing:
                    report.scenarios.append(self._browser_failure(scenario, str(exc)))
            report.coverage_gaps.append(
                ExecutionCoverageGap(reason="browser_runtime_failure", detail=str(exc))
            )
        return self._finish(report)

    async def _run_scenario(
        self,
        browser: Browser,
        request: ExecutionRequest,
        scenario: CompiledScenario,
        run_id: str,
    ) -> ScenarioExecution:
        start_clock = time.perf_counter()
        started = datetime.now(UTC)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(request.config.step_timeout_ms)
        console: list[ConsoleEvidence] = []
        network: list[NetworkEvidence] = []

        if request.config.capture_console:
            page.on(
                "console",
                lambda msg: console.append(ConsoleEvidence(level=msg.type, message=msg.text[:2000])),
            )
        if request.config.capture_network:
            page.on(
                "response",
                lambda response: network.append(
                    NetworkEvidence(
                        method=response.request.method,
                        url=redact_url(response.url),
                        resource_type=response.request.resource_type,
                        status=response.status,
                    )
                ),
            )
            page.on(
                "requestfailed",
                lambda req: network.append(
                    NetworkEvidence(
                        method=req.method,
                        url=redact_url(req.url),
                        resource_type=req.resource_type,
                        failure=(req.failure or "request failed")[:500],
                    )
                ),
            )

        execution = ScenarioExecution(
            scenario_key=scenario.scenario_key,
            title=scenario.title,
            kind=scenario.kind,
            priority=scenario.priority,
            status=ExecutionStatus.PASSED,
            verified=False,
            target_route=scenario.route,
            started_at=started,
            source_impact_keys=scenario.source_impact_keys,
        )
        artifact_root = self._artifact_root(
            request.config.artifact_dir, run_id, scenario.scenario_key
        )
        try:
            for step in scenario.steps:
                result = await self._run_step(
                    page,
                    request,
                    step,
                    artifact_root=artifact_root,
                    console=console,
                    network=network,
                )
                execution.steps.append(result)
                if result.status != ExecutionStatus.PASSED:
                    execution.status = result.status
                    execution.failure_category = result.failure_category
                    execution.detail = result.detail
                    break
            execution.verified = execution.status in {ExecutionStatus.PASSED, ExecutionStatus.FAILED}
            execution.attempts.append(
                AttemptRecord(
                    attempt=1,
                    status=execution.status,
                    failure_category=execution.failure_category,
                    reason=execution.detail,
                )
            )
        finally:
            await context.close()
        execution.completed_at = datetime.now(UTC)
        execution.duration_ms = (time.perf_counter() - start_clock) * 1000
        return execution

    async def _run_step(
        self,
        page: Page,
        request: ExecutionRequest,
        step: CompiledStep,
        *,
        artifact_root: Path,
        console: list[ConsoleEvidence],
        network: list[NetworkEvidence],
    ) -> StepExecution:
        started = datetime.now(UTC)
        start_clock = time.perf_counter()
        result = StepExecution(
            index=step.index,
            operation=step.operation,
            source_action=step.source_action,
            source_expected=step.source_expected,
            status=ExecutionStatus.PASSED,
            expected=step.expected,
            started_at=started,
        )
        locator = None
        locator_description = None
        try:
            if step.operation == OperationKind.NAVIGATE:
                if not step.route:
                    result.status = ExecutionStatus.UNVERIFIED
                    result.failure_category = FailureCategory.TEST_DEFINITION_ERROR
                    result.detail = "navigate operation missing route"
                else:
                    url = urljoin(
                        request.config.base_url.rstrip("/") + "/", step.route.lstrip("/")
                    )
                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=request.config.global_timeout_ms,
                    )
                    if response is not None and response.status >= 500:
                        result.status = ExecutionStatus.EXECUTION_ERROR
                        result.failure_category = FailureCategory.ENVIRONMENT_FAILURE
                        result.detail = f"navigation returned HTTP {response.status}"
                    else:
                        result.actual = page.url
            elif step.operation == OperationKind.CAPTURE:
                pass
            elif step.operation == OperationKind.ASSERT_URL:
                actual = page.url
                result.actual = actual
                if step.expected and step.expected not in actual:
                    result.status, result.failure_category = assertion_failure()
                    result.detail = (
                        f"expected URL containing {step.expected!r}, observed {actual!r}"
                    )
            else:
                if step.target is None:
                    result.status = ExecutionStatus.UNVERIFIED
                    result.failure_category = FailureCategory.TEST_DEFINITION_ERROR
                    result.detail = "operation requires target metadata"
                else:
                    resolution = await resolve_target(
                        page, step.target, timeout_ms=request.config.step_timeout_ms
                    )
                    if not resolution.resolved or resolution.locator is None:
                        result.status = ExecutionStatus.UNVERIFIED
                        result.failure_category = resolution.failure_category
                        result.detail = resolution.detail
                    else:
                        locator = resolution.locator
                        locator_description = resolution.description
                        await self._apply_target_operation(locator, step, result)
        except Exception as exc:
            result.status, result.failure_category = classify_exception(step.operation, exc)
            result.detail = str(exc)[:2000]

        if step.state_setup and result.status != ExecutionStatus.PASSED:
            infrastructure = {
                FailureCategory.ENVIRONMENT_FAILURE,
                FailureCategory.BROWSER_FAILURE,
                FailureCategory.NETWORK_INFRA_FAILURE,
                FailureCategory.NAVIGATION_FAILURE,
            }
            if result.failure_category not in infrastructure:
                result.failure_category = FailureCategory.STATE_SETUP_FAILURE

        screenshot = None
        if request.config.screenshot_on_failure and result.status != ExecutionStatus.PASSED:
            screenshot = artifact_root / f"step-{step.index}-failure.png"
        try:
            result.evidence = await capture_page_evidence(
                page,
                requested_route=step.route,
                locator=locator,
                locator_description=locator_description,
                screenshot_path=screenshot,
            )
        except Exception as exc:
            result.evidence = StepEvidence(requested_route=step.route, final_url=page.url)
            if result.detail is None:
                result.detail = f"evidence capture failed: {exc}"
        result.evidence.console = list(console[-50:])
        result.evidence.network = list(network[-100:])
        result.completed_at = datetime.now(UTC)
        result.duration_ms = (time.perf_counter() - start_clock) * 1000
        return result

    async def _apply_target_operation(
        self, locator: Locator, step: CompiledStep, result: StepExecution
    ) -> None:
        if step.operation == OperationKind.CLICK:
            await locator.click()
        elif step.operation == OperationKind.FILL:
            await locator.fill(step.value or "")
        elif step.operation == OperationKind.SELECT:
            await locator.select_option(step.value or "")
        elif step.operation == OperationKind.ASSERT_VISIBLE:
            is_visible = await locator.is_visible()
            result.actual = str(is_visible)
            if not is_visible:
                result.status, result.failure_category = assertion_failure()
                result.detail = "expected target to be visible"
        elif step.operation == OperationKind.ASSERT_HIDDEN:
            is_visible = await locator.is_visible()
            result.actual = str(is_visible)
            if is_visible:
                result.status, result.failure_category = assertion_failure()
                result.detail = "expected target to be hidden"
        elif step.operation == OperationKind.ASSERT_TEXT:
            actual_text = (await locator.inner_text()).strip()
            expected_text = step.expected or ""
            result.actual = actual_text
            if expected_text not in actual_text:
                result.status, result.failure_category = assertion_failure()
                result.detail = (
                    f"expected text containing {expected_text!r}, observed {actual_text!r}"
                )
        elif step.operation == OperationKind.ASSERT_VALUE:
            actual_val = await locator.input_value()
            expected_val = step.expected or ""
            result.actual = actual_val
            if actual_val != expected_val:
                result.status, result.failure_category = assertion_failure()
        else:
            result.status = ExecutionStatus.UNVERIFIED
            result.failure_category = FailureCategory.TEST_DEFINITION_ERROR
            result.detail = f"operation {step.operation.value} is not executable in V1"

    @staticmethod
    def _artifact_root(artifact_dir: str, run_id: str, scenario_key: str) -> Path:
        return Path(artifact_dir).expanduser() / run_id / scenario_key

    @staticmethod
    def _browser_failure(scenario: CompiledScenario, detail: str) -> ScenarioExecution:
        return ScenarioExecution(
            scenario_key=scenario.scenario_key,
            title=scenario.title,
            kind=scenario.kind,
            priority=scenario.priority,
            status=ExecutionStatus.EXECUTION_ERROR,
            failure_category=FailureCategory.BROWSER_FAILURE,
            verified=False,
            target_route=scenario.route,
            detail=detail[:2000],
            source_impact_keys=scenario.source_impact_keys,
            attempts=[
                AttemptRecord(
                    attempt=1,
                    status=ExecutionStatus.EXECUTION_ERROR,
                    failure_category=FailureCategory.BROWSER_FAILURE,
                    reason=detail[:1000],
                )
            ],
        )

    @staticmethod
    def _config_fingerprint(request: ExecutionRequest) -> str:
        safe = request.config.model_dump(exclude={"artifact_dir"})
        return hashlib.sha256(json.dumps(safe, sort_keys=True).encode()).hexdigest()[:24]

    @staticmethod
    def _finish(report: ExecutionReport) -> ExecutionReport:
        report.metadata.completed_at = datetime.now(UTC)
        report.summary.executed = sum(
            item.status
            in {ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.EXECUTION_ERROR}
            for item in report.scenarios
        )
        report.summary.passed = sum(
            item.status == ExecutionStatus.PASSED for item in report.scenarios
        )
        report.summary.failed = sum(
            item.status == ExecutionStatus.FAILED for item in report.scenarios
        )
        report.summary.execution_error = sum(
            item.status == ExecutionStatus.EXECUTION_ERROR for item in report.scenarios
        )
        report.summary.unverified = sum(
            item.status == ExecutionStatus.UNVERIFIED for item in report.scenarios
        )
        report.summary.skipped_manual = sum(
            item.status == ExecutionStatus.SKIPPED_MANUAL for item in report.scenarios
        )
        report.summary.blocked = sum(
            item.status == ExecutionStatus.BLOCKED for item in report.scenarios
        )
        return report
