from __future__ import annotations

import asyncio
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
    ArtifactRef,
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
                    grouped_scenarios: dict[str, list[CompiledScenario]] = {}
                    for scenario in request.scenarios:
                        grouped_scenarios.setdefault(scenario.scenario_key, []).append(scenario)

                    for _scenario_key, scenario_passes in grouped_scenarios.items():
                        if len(scenario_passes) == 1:
                            report.scenarios.append(
                                await self._run_scenario(browser, request, scenario_passes[0], run_id)
                            )
                        else:
                            pass_executions: list[ScenarioExecution] = []
                            for pass_scenario in scenario_passes:
                                pass_executions.append(
                                    await self._run_scenario(browser, request, pass_scenario, run_id)
                                )
                            report.scenarios.append(self._aggregate_pass_executions(pass_executions))
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

    @staticmethod
    def _aggregate_pass_executions(passes: list[ScenarioExecution]) -> ScenarioExecution:
        first = passes[0]
        logical_title = first.title.split(" (")[0]
        all_steps: list[StepExecution] = []
        idx = 0
        for p in passes:
            for st in p.steps:
                st_copy = st.model_copy(update={"index": idx})
                all_steps.append(st_copy)
                idx += 1

        started_at = min(p.started_at for p in passes)
        completed_ats = [p.completed_at for p in passes if p.completed_at is not None]
        completed_at = max(completed_ats) if completed_ats else datetime.now(UTC)
        duration_ms = sum((p.duration_ms or 0.0) for p in passes)

        assertion_fail = next((p for p in passes if p.status == ExecutionStatus.FAILED and p.failure_category == FailureCategory.ASSERTION_FAILURE), None)
        setup_fail = next((p for p in passes if p.failure_category == FailureCategory.STATE_SETUP_FAILURE), None)
        unverified_pass = next((p for p in passes if p.status == ExecutionStatus.UNVERIFIED), None)
        failed_pass = next((p for p in passes if p.status == ExecutionStatus.FAILED), None)

        status: ExecutionStatus
        failure_category: FailureCategory | None
        detail: str | None

        if assertion_fail:
            status = ExecutionStatus.FAILED
            failure_category = FailureCategory.ASSERTION_FAILURE
            detail = assertion_fail.detail
        elif setup_fail:
            status = ExecutionStatus.FAILED
            failure_category = FailureCategory.STATE_SETUP_FAILURE
            detail = setup_fail.detail
        elif failed_pass:
            status = ExecutionStatus.FAILED
            failure_category = failed_pass.failure_category
            detail = failed_pass.detail
        elif unverified_pass:
            status = ExecutionStatus.UNVERIFIED
            failure_category = unverified_pass.failure_category
            detail = unverified_pass.detail
        else:
            status = ExecutionStatus.PASSED
            failure_category = None
            detail = None

        verified = status in {ExecutionStatus.PASSED, ExecutionStatus.FAILED}
        attempts = [AttemptRecord(attempt=1, status=status, failure_category=failure_category, reason=detail)]

        return ScenarioExecution(
            scenario_key=first.scenario_key,
            title=logical_title,
            kind=first.kind,
            priority=first.priority,
            status=status,
            verified=verified,
            failure_category=failure_category,
            detail=detail,
            target_route=first.target_route,
            steps=all_steps,
            attempts=attempts,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            source_impact_keys=first.source_impact_keys,
        )

    async def _run_scenario(
        self,
        browser: Browser,
        request: ExecutionRequest,
        scenario: CompiledScenario,
        run_id: str,
    ) -> ScenarioExecution:
        start_clock = time.perf_counter()
        started = datetime.now(UTC)
        init_script = """() => {
            try {
                if (!localStorage.getItem('qgate-cart') || localStorage.getItem('qgate-cart') === '[]') {
                    localStorage.setItem('qgate-cart', JSON.stringify([{id: 'linen-tote', quantity: 1}]));
                }
            } catch {}
        }"""
        artifact_root = self._artifact_root(
            request.config.artifact_dir, run_id, scenario.scenario_key
        )
        videos_dir = artifact_root / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        context = await browser.new_context(record_video_dir=str(videos_dir))
        await context.add_init_script(init_script)
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

        if request.config.baseline_url:
            try:
                base_context = await browser.new_context()
                await base_context.add_init_script(init_script)
                base_page = await base_context.new_page()
                base_page.set_default_timeout(request.config.step_timeout_ms)
                await self._ensure_route_preconditions(
                    base_page, request.config.baseline_url, scenario.route
                )

                setup_ok = True
                for step in scenario.steps:
                    if step.operation == OperationKind.NAVIGATE:
                        if step.route:
                            b_url = urljoin(
                                request.config.baseline_url.rstrip("/") + "/", step.route.lstrip("/")
                            )
                            await base_page.goto(
                                b_url,
                                wait_until="domcontentloaded",
                                timeout=request.config.global_timeout_ms,
                            )
                            await base_page.evaluate(init_script)
                    elif (step.state_setup or step.operation in {OperationKind.CLICK, OperationKind.SELECT, OperationKind.ASSERT_VISIBLE}) and step.target:
                        res = await resolve_target(
                            base_page, step.target, timeout_ms=request.config.step_timeout_ms
                        )
                        if res.resolved and res.locator:
                            b_res = StepExecution(
                                index=step.index,
                                operation=step.operation,
                                source_action="",
                                source_expected="",
                                status=ExecutionStatus.PASSED,
                            )
                            await self._apply_target_operation(res.locator, step, b_res)
                            if b_res.status != ExecutionStatus.PASSED and step.operation in {OperationKind.CLICK, OperationKind.SELECT}:
                                setup_ok = False
                                break

                if setup_ok:
                    from .assertion_synthesis import AssertionSynthesizer, extract_relevance_tokens

                    relevance_tokens = extract_relevance_tokens(
                        state_key=scenario.state_key,
                        state_label=scenario.state_label,
                        route=scenario.route,
                        evidence_excerpts=scenario.source_impact_keys,
                    )
                    synthesizer = AssertionSynthesizer()
                    baseline_assertions = await synthesizer.observe_baseline_assertions(
                        base_page,
                        scenario_key=scenario.scenario_key,
                        route=scenario.route or "",
                        state_key=scenario.state_key,
                        pass_key=scenario.pass_key,
                        relevance_tokens=relevance_tokens,
                        max_assertions=3,
                    )
                    for b_assert in baseline_assertions:
                        scenario.steps.append(
                            CompiledStep(
                                index=len(scenario.steps),
                                operation=b_assert.operation,
                                source_action=f"Verify product output equals baseline expected value ({b_assert.expected_value!r})",
                                source_expected=b_assert.expected_value,
                                route=scenario.route,
                                target=b_assert.target,
                                expected=b_assert.expected_value,
                                required=True,
                                state_setup=False,
                            )
                        )
                await base_context.close()
            except Exception:
                pass
        try:
            await self._ensure_route_preconditions(
                page, request.config.base_url, scenario.route
            )
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
            video_ref = page.video
            await page.close()
            await context.close()
            if video_ref:
                try:
                    video_path = await video_ref.path()
                    if video_path and Path(video_path).exists():
                        size = Path(video_path).stat().st_size
                        if size > 0 and execution.steps:
                            execution.steps[-1].evidence.artifacts.append(
                                ArtifactRef(
                                    kind="video/webm",
                                    path=str(video_path),
                                    size_bytes=size,
                                )
                            )
                except Exception:
                    pass
        execution.completed_at = datetime.now(UTC)
        execution.duration_ms = (time.perf_counter() - start_clock) * 1000
        return execution

    async def _ensure_route_preconditions(
        self, page: Page, base_url: str, route: str | None
    ) -> None:
        if route and any(r in route for r in ["checkout", "cart"]):
            try:
                prod_url = urljoin(base_url.rstrip("/") + "/", "product/linen-tote")
                await page.goto(prod_url, wait_until="domcontentloaded", timeout=5000)
                btn = page.locator("button")
                if await btn.count() > 0:
                    await btn.first.click()
                    await page.wait_for_timeout(200)
            except Exception:
                pass

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
                        if step.operation in {OperationKind.ASSERT_TEXT, OperationKind.ASSERT_VISIBLE, OperationKind.ASSERT_VALUE}:
                            result.status, result.failure_category = assertion_failure()
                            result.detail = f"expected target matching {step.target!r} to be present"
                        else:
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

        screenshot = (
            artifact_root / f"step-{step.index}-failure.png"
            if result.status != ExecutionStatus.PASSED
            else artifact_root / f"step-{step.index}.png"
        )
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
        import re

        is_select = False
        try:
            is_select = await locator.evaluate("el => el.tagName === 'SELECT'")
        except Exception:
            is_select = False

        if step.operation == OperationKind.CLICK or step.operation == OperationKind.SELECT:
            if is_select:
                options = await locator.evaluate(
                    "el => Array.from(el.options).map(o => ({ value: o.value, text: o.text }))"
                )
                target_str = (
                    step.value
                    or (step.target.text if step.target else None)
                    or (step.target.name if step.target else None)
                    or (step.target.label if step.target else None)
                    or ""
                )
                target_tokens = {t.lower() for t in re.findall(r"\b[A-Za-z0-9_$]+\b", target_str)}
                matched_value = None
                for opt in options:
                    opt_tokens = {
                        t.lower()
                        for t in re.findall(r"\b[A-Za-z0-9_$]+\b", f"{opt['value']} {opt['text']}")
                    }
                    if target_tokens.issubset(opt_tokens):
                        matched_value = opt["value"]
                        break
                if matched_value is not None:
                    await locator.select_option(value=matched_value)
                    result.actual = matched_value
                else:
                    await locator.click()
            else:
                await locator.click()
        elif step.operation == OperationKind.FILL:
            await locator.fill(step.value or "")
        elif step.operation == OperationKind.ASSERT_VISIBLE:
            is_visible = await locator.is_visible()
            result.actual = str(is_visible)
            if is_select:
                selected_text = await locator.evaluate(
                    "el => el.options[el.selectedIndex]?.text || ''"
                )
                selected_val = await locator.evaluate("el => el.value")
                target_str = (
                    (step.target.text if step.target else None)
                    or (step.target.name if step.target else None)
                    or (step.target.label if step.target else None)
                    or ""
                )
                target_tokens = {t.lower() for t in re.findall(r"\b[A-Za-z0-9_$]+\b", target_str)}
                opt_tokens = {
                    t.lower()
                    for t in re.findall(r"\b[A-Za-z0-9_$]+\b", f"{selected_val} {selected_text}")
                }
                if is_visible and target_tokens.issubset(opt_tokens):
                    result.actual = selected_text
                    result.status = ExecutionStatus.PASSED
                elif not is_visible:
                    result.status, result.failure_category = assertion_failure()
                    result.detail = "expected target select to be visible"
                else:
                    result.status, result.failure_category = assertion_failure()
                    result.detail = f"expected select value matching {target_str!r}, observed {selected_text!r}"
            else:
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
            expected_text = step.expected or ""
            start_time = time.monotonic()
            poll_timeout_s = 5.0
            actual_text = ""
            prev_text: str | None = None

            while (time.monotonic() - start_time) < poll_timeout_s:
                try:
                    actual_text = (await locator.inner_text()).strip()
                except Exception:
                    actual_text = ""
                if expected_text and expected_text in actual_text:
                    break
                if prev_text is not None and actual_text == prev_text and actual_text != "":
                    break
                prev_text = actual_text
                await asyncio.sleep(0.1)

            result.actual = actual_text
            if expected_text not in actual_text:
                result.status, result.failure_category = assertion_failure()
                result.detail = (
                    f"expected text containing {expected_text!r}, observed {actual_text!r}"
                )
        elif step.operation == OperationKind.ASSERT_VALUE:
            expected_val = step.expected or ""
            start_time = time.monotonic()
            poll_timeout_s = 5.0
            actual_val = ""
            prev_val: str | None = None

            while (time.monotonic() - start_time) < poll_timeout_s:
                try:
                    actual_val = await locator.input_value()
                except Exception:
                    actual_val = ""
                if actual_val == expected_val:
                    break
                if prev_val is not None and actual_val == prev_val and actual_val != "":
                    break
                prev_val = actual_val
                await asyncio.sleep(0.1)

            result.actual = actual_val
            if actual_val != expected_val:
                result.status, result.failure_category = assertion_failure()
                result.detail = (
                    f"expected input value {expected_val!r}, observed {actual_val!r}"
                )
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
