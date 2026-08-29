from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pydantic import TypeAdapter
from qgate_browser_execution.models import ExecutionReport
from qgate_impact_analysis.models import ImpactReport
from qgate_project_intelligence.models import ProjectKnowledge
from qgate_qa_memory.models import MemoryRecallResult, RegressionScenarioHint
from qgate_scenario_intelligence.models import ScenarioPlan

from .judge import FinalGateJudge
from .models import GateInputBundle
from .report import render_gate_report
from .store import JsonGateReportStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qgate-final-gate")
    parser.add_argument(
        "--store-dir",
        default=os.environ.get("SUITEST_FINAL_GATE_DIR", "~/.qgate/final-gate"),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--project", required=True)
    evaluate.add_argument("--impact", required=True)
    evaluate.add_argument("--scenario-plan", required=True)
    evaluate.add_argument("--scenario-plan-key", required=True)
    evaluate.add_argument("--execution", required=True)
    evaluate.add_argument("--memory-recall")
    evaluate.add_argument("--regression-hints")
    evaluate.add_argument("--json", action="store_true")

    show = sub.add_parser("show")
    show.add_argument("--report", required=True)
    show.add_argument("--json", action="store_true")

    listing = sub.add_parser("list")
    listing.add_argument("--project-source-id")
    listing.add_argument("--json", action="store_true")
    return parser


def _read(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def main() -> None:
    args = _parser().parse_args()
    store = JsonGateReportStore(args.store_dir)

    if args.command == "evaluate":
        project = ProjectKnowledge.model_validate_json(_read(args.project))
        impact = ImpactReport.model_validate_json(_read(args.impact))
        scenario_plan = ScenarioPlan.model_validate_json(_read(args.scenario_plan))
        execution = ExecutionReport.model_validate_json(_read(args.execution))
        recall = (
            MemoryRecallResult.model_validate_json(_read(args.memory_recall))
            if args.memory_recall
            else None
        )
        hints: list[RegressionScenarioHint] = []
        if args.regression_hints:
            raw = json.loads(_read(args.regression_hints))
            hints = TypeAdapter(list[RegressionScenarioHint]).validate_python(raw)
        report = FinalGateJudge().evaluate(
            GateInputBundle(
                project=project,
                impact=impact,
                scenario_plan=scenario_plan,
                scenario_plan_key=args.scenario_plan_key,
                execution=execution,
                memory_recall=recall,
                regression_hints=hints,
            )
        )
        store.save(report)
        print(report.model_dump_json(indent=2) if args.json else render_gate_report(report))
        return

    if args.command == "show":
        report = store.load_key(args.report)
        if report is None:
            raise SystemExit(f"Gate report not found: {args.report}")
        print(report.model_dump_json(indent=2) if args.json else render_gate_report(report))
        return

    reports = store.list_reports(project_source_id=args.project_source_id)
    if args.json:
        print(json.dumps([item.model_dump(mode="json") for item in reports], indent=2))
        return
    for report in reports:
        print(
            f"{report.metadata.report_key}\t{report.verdict.value}\t"
            f"{report.metadata.project_source_id}\t{report.headline}"
        )


if __name__ == "__main__":
    main()
