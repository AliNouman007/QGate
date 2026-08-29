from __future__ import annotations

import argparse
from pathlib import Path

from qgate_impact_analysis.store import JsonImpactStore
from qgate_project_intelligence.store import JsonKnowledgeStore

from .generator import ScenarioGenerator
from .report import render_scenario_plan
from .store import JsonScenarioPlanStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="qgate-scenario-intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--knowledge", required=True)
    generate.add_argument("--impact", required=True)
    generate.add_argument("--store", default="~/.qgate/scenario-intelligence")
    generate.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "generate":
        knowledge = JsonKnowledgeStore.load_path(Path(args.knowledge))
        impact = JsonImpactStore.load_path(Path(args.impact))
        plan = ScenarioGenerator().generate(knowledge, impact)
        JsonScenarioPlanStore(args.store).save(plan)
        print(plan.model_dump_json(indent=2) if args.json else render_scenario_plan(plan), end="")


if __name__ == "__main__":
    main()
