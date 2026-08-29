from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from qgate_scenario_intelligence.store import JsonScenarioPlanStore

from .compiler import ScenarioCompiler
from .executor import BrowserExecutor
from .models import ExecutionConfig
from .report import render_execution_report
from .store import JsonExecutionReportStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qgate-browser-execution")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--scenario-plan", required=True)
    run.add_argument("--base-url", required=True)
    run.add_argument("--scenario", action="append", default=[])
    run.add_argument("--priority", action="append", default=[])
    run.add_argument("--store-dir", default="~/.qgate/browser-execution")
    run.add_argument("--artifact-dir", default="~/.qgate/browser-execution/artifacts")
    run.add_argument("--timeout-ms", type=int, default=45_000)
    run.add_argument("--step-timeout-ms", type=int, default=10_000)
    run.add_argument("--retry-budget", type=int, choices=(0, 1), default=1)
    run.add_argument("--headed", action="store_true")
    run.add_argument("--json", action="store_true", dest="json_output")
    return parser


async def _run(args: argparse.Namespace) -> int:
    plan = JsonScenarioPlanStore.load_path(Path(args.scenario_plan))
    config = ExecutionConfig(
        base_url=args.base_url,
        headed=bool(args.headed),
        global_timeout_ms=args.timeout_ms,
        step_timeout_ms=args.step_timeout_ms,
        retry_budget=args.retry_budget,
        artifact_dir=args.artifact_dir,
    )
    request = ScenarioCompiler().compile_plan(
        plan,
        config,
        scenario_keys=set(args.scenario) if args.scenario else None,
        priorities=set(args.priority) if args.priority else None,
    )
    report = await BrowserExecutor().run(request)
    path = JsonExecutionReportStore(args.store_dir).save(report)
    if args.json_output:
        print(report.model_dump_json(indent=2))
    else:
        print(render_execution_report(report))
        print(f"\nSaved: {path}")
    return 0


def main() -> None:
    args = _parser().parse_args()
    if args.command == "run":
        raise SystemExit(asyncio.run(_run(args)))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
