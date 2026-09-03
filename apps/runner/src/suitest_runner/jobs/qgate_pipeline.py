"""QGate end-to-end pipeline runner for local supervisor and worker jobs."""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qgate_browser_execution.compiler import ScenarioCompiler
from qgate_browser_execution.executor import BrowserExecutor
from qgate_browser_execution.models import ExecutionConfig, ExecutionStatus
from qgate_browser_execution.store import JsonExecutionReportStore
from qgate_final_gate.judge import FinalGateJudge
from qgate_final_gate.models import GateInputBundle, GateVerdict
from qgate_final_gate.store import JsonGateReportStore
from qgate_impact_analysis.engine import ImpactAnalyzer
from qgate_impact_analysis.source import LocalGitSource
from qgate_impact_analysis.store import JsonImpactStore
from qgate_project_intelligence.analyzer import ProjectIntelligenceAnalyzer
from qgate_project_intelligence.source import LocalPathSource
from qgate_project_intelligence.store import JsonKnowledgeStore
from qgate_qa_memory.extraction import CandidateExtractor
from qgate_qa_memory.lifecycle import QAMemoryService
from qgate_qa_memory.recall import MemoryRecallEngine
from qgate_qa_memory.scenario_adapter import build_regression_hints
from qgate_qa_memory.store import JsonQAMemoryStore
from qgate_scenario_intelligence.generator import ScenarioGenerator
from qgate_scenario_intelligence.store import JsonScenarioPlanStore

from sqlalchemy import select
from suitest_db.models.case import TestCase
from suitest_db.models.project import Project, Suite
from suitest_db.models.run import Run, RunStep
from suitest_db.repositories.runs import RunRepo
from suitest_shared.domain.enums import RunStatus, StepOutcome

logger = logging.getLogger("suitest_runner.qgate_pipeline")


def resolve_project_path(project: Project) -> Path | None:
    """Resolve a project's local directory path on disk."""
    candidates = [
        project.name,
        getattr(project, "path", None),
        getattr(project, "slug", None),
    ]
    for c in candidates:
        if c and isinstance(c, str):
            p = Path(c)
            if p.is_dir():
                return p
    # Fallback to test shop default if name/slug mentions qgate-test-shop
    name_slug = f"{project.name} {project.slug}".lower()
    if "qgate-test-shop" in name_slug:
        p = Path(r"D:\QGate\qgate-test-shop")
        if p.is_dir():
            return p
    return None


async def execute_qgate_pipeline(
    factory: Any,
    run_id: str,
    project: Project,
    project_path: Path,
    base_url: str = "http://localhost:3001",
) -> dict[str, Any]:
    """Execute the full 6-stage QGate pipeline against a target project."""
    t0 = time.perf_counter()
    logger.info("qgate.pipeline.start", run_id=run_id, project_path=str(project_path))

    # Storage paths
    pi_dir = os.environ.get("SUITEST_PROJECT_INTELLIGENCE_DIR", "~/.qgate/project-intelligence")
    ia_dir = os.environ.get("SUITEST_IMPACT_ANALYSIS_DIR", "~/.qgate/impact-analysis")
    si_dir = os.environ.get("SUITEST_SCENARIO_INTELLIGENCE_DIR", "~/.qgate/scenario-intelligence")
    be_dir = os.environ.get("SUITEST_BROWSER_EXECUTION_DIR", "~/.qgate/browser-execution")
    qm_dir = os.environ.get("SUITEST_QA_MEMORY_DIR", "~/.qgate/qa-memory")
    fg_dir = os.environ.get("SUITEST_FINAL_GATE_DIR", "~/.qgate/final-gate")

    # STAGE 1: Project Intelligence
    logger.info("qgate.pipeline.stage1.project_intelligence")
    source = LocalPathSource(project_path)
    knowledge = ProjectIntelligenceAnalyzer().analyze(source)
    JsonKnowledgeStore(pi_dir).save(knowledge)

    # STAGE 2: Impact Analysis
    logger.info("qgate.pipeline.stage2.impact_analysis")
    git_source = LocalGitSource(project_path, base_ref="HEAD~1", head_ref="HEAD")
    try:
        change_set = git_source.load()
    except Exception as e:
        logger.warning(f"LocalGitSource fallback: {e}")
        git_source = LocalGitSource(project_path)
        change_set = git_source.load()

    impact = ImpactAnalyzer(knowledge).analyze(change_set)
    JsonImpactStore(ia_dir).save(impact)

    # STAGE 3: Scenario Intelligence
    logger.info("qgate.pipeline.stage3.scenario_intelligence")
    qa_store = JsonQAMemoryStore(qm_dir)
    memories = qa_store.list_memories()
    rules = qa_store.list_rules()
    recall = MemoryRecallEngine().recall(knowledge, impact, memories, rules)

    plan = ScenarioGenerator().generate(knowledge, impact)
    JsonScenarioPlanStore(si_dir).save(plan)

    # STAGE 4: Browser Execution
    logger.info("qgate.pipeline.stage4.browser_execution", base_url=base_url)
    config = ExecutionConfig(
        base_url=base_url,
        headed=False,
        global_timeout_ms=30000,
        step_timeout_ms=8000,
        retry_budget=0,
        artifact_dir=os.path.join(os.path.expanduser(be_dir), "artifacts"),
    )
    request = ScenarioCompiler().compile_plan(plan, config)
    execution = await BrowserExecutor().run(request)
    JsonExecutionReportStore(be_dir).save(execution)

    # STAGE 5: QA Memory
    logger.info("qgate.pipeline.stage5.qa_memory")
    service = QAMemoryService(qa_store)
    candidates = CandidateExtractor().extract(execution)
    for c in candidates:
        service.ingest_candidate(c)

    hints = build_regression_hints(recall, memories, rules)

    # STAGE 6: Final Gate
    logger.info("qgate.pipeline.stage6.final_gate")
    bundle = GateInputBundle(
        project=knowledge,
        impact=impact,
        scenario_plan=plan,
        scenario_plan_key=request.scenario_plan_key,
        execution=execution,
        memory_recall=recall,
        regression_hints=hints,
    )
    gate_report = FinalGateJudge().evaluate(bundle)
    JsonGateReportStore(fg_dir).save(gate_report)

    # Map verdict to RunStatus
    if gate_report.verdict == GateVerdict.PASS:
        final_status = RunStatus.PASS
    else:
        final_status = RunStatus.FAIL

    duration_ms = int((time.perf_counter() - t0) * 1000)
    total_steps = len(execution.scenarios)
    passed_steps = execution.summary.passed
    failed_steps = execution.summary.failed + execution.summary.unverified

    # Persist in DB
    async with factory() as session:
        run_repo = RunRepo(session)
        run_obj = await run_repo.get_by_id(run_id)
        if run_obj is not None:
            metadata = dict(run_obj.metadata_json or {})
            metadata["final_gate"] = {
                "verdict": gate_report.verdict.value,
                "headline": gate_report.headline,
                "report_key": gate_report.metadata.report_key,
                "confidence": gate_report.confidence.value,
            }
            metadata["stages"] = {
                "project_intelligence": "completed",
                "impact_analysis": "completed",
                "scenario_intelligence": "completed",
                "browser_execution": "completed",
                "qa_memory": "completed",
                "final_gate": "completed",
            }
            metadata["summary_stats"] = {
                "scenarios_total": total_steps,
                "scenarios_passed": passed_steps,
                "scenarios_failed": failed_steps,
                "duration_ms": duration_ms,
            }
            run_obj.metadata_json = metadata

            # Find or get a test case to associate steps with
            cases_stmt = (
                select(TestCase.id)
                .join(Suite, Suite.id == TestCase.suite_id)
                .where(Suite.project_id == project.id)
            )
            case_ids = [c for (c,) in (await session.execute(cases_stmt)).all()]
            fallback_case_id = case_ids[0] if case_ids else None

            # Create RunSteps for visibility in UI
            if fallback_case_id:
                for idx, scn in enumerate(execution.scenarios[:15]):
                    step_outcome = (
                        StepOutcome.PASS
                        if scn.status == ExecutionStatus.PASSED
                        else StepOutcome.FAIL
                        if scn.status == ExecutionStatus.FAILED
                        else StepOutcome.SKIP
                    )
                    run_step = RunStep(
                        run_id=run_id,
                        case_id=fallback_case_id,
                        step_order=idx,
                        outcome=step_outcome,
                        started_at=datetime.now(UTC),
                        completed_at=datetime.now(UTC),
                        duration_ms=100,
                        stdout=f"{scn.title} ({scn.scenario_key})",
                        error_message=scn.detail if scn.failure_category else None,
                    )
                    session.add(run_step)

            await run_repo.update_status(
                run_id,
                final_status,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
                total_steps=total_steps,
                passed_steps=passed_steps,
                failed_steps=failed_steps,
            )
            await session.commit()

    logger.info(
        "qgate.pipeline.complete",
        run_id=run_id,
        verdict=gate_report.verdict.value,
        duration_ms=duration_ms,
    )
    return {
        "status": final_status.value,
        "verdict": gate_report.verdict.value,
        "headline": gate_report.headline,
        "duration_ms": duration_ms,
        "total_steps": total_steps,
        "passed_steps": passed_steps,
        "failed_steps": failed_steps,
    }
