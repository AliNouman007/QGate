from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qgate_browser_execution.models import ExecutionReport
from qgate_impact_analysis.models import ImpactReport
from qgate_project_intelligence.models import ProjectKnowledge

from .extraction import CandidateExtractor
from .lifecycle import QAMemoryService
from .models import CandidateKind, MemoryCandidate, MemorySeverity
from .recall import MemoryRecallEngine
from .report import render_recall
from .signature import candidate_signature
from .store import JsonQAMemoryStore


def _store(path: str) -> JsonQAMemoryStore:
    return JsonQAMemoryStore(path)


def main() -> None:
    parser = argparse.ArgumentParser(prog="qgate-qa-memory")
    parser.add_argument("--store", default="~/.qgate/qa-memory")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest-execution")
    ingest.add_argument("--report", required=True)

    human = sub.add_parser("add-human")
    human.add_argument("--project-source-id", required=True)
    human.add_argument("--title", required=True)
    human.add_argument("--invariant", required=True)
    human.add_argument("--route", action="append", default=[])
    human.add_argument("--state", action="append", default=[])

    listing = sub.add_parser("list")
    listing.add_argument("--kind", choices=["candidates", "memories", "rules"], required=True)
    listing.add_argument("--json", action="store_true")

    confirm = sub.add_parser("confirm")
    confirm.add_argument("key")
    confirm.add_argument("--reviewer", required=True)
    confirm.add_argument("--note")

    reject = sub.add_parser("reject")
    reject.add_argument("key")
    reject.add_argument("--reviewer", required=True)
    reject.add_argument("--note")

    recall = sub.add_parser("recall")
    recall.add_argument("--knowledge", required=True)
    recall.add_argument("--impact", required=True)
    recall.add_argument("--json", action="store_true")

    args = parser.parse_args()
    store = _store(args.store)
    service = QAMemoryService(store)

    if args.command == "ingest-execution":
        report = ExecutionReport.model_validate_json(Path(args.report).read_text(encoding="utf-8"))
        items = [service.ingest_candidate(item) for item in CandidateExtractor().extract(report)]
        print(json.dumps([item.model_dump(mode="json") for item in items], indent=2))
        return

    if args.command == "add-human":
        candidate = MemoryCandidate(
            key="human_pending",
            project_source_id=args.project_source_id,
            title=args.title,
            invariant=args.invariant,
            kind=CandidateKind.HUMAN_REPORTED,
            severity=MemorySeverity.UNKNOWN,
            routes=args.route,
            states=args.state,
            dedupe_signature="pending",
        )
        candidate.dedupe_signature = candidate_signature(candidate)
        candidate.key = f"human_{candidate.dedupe_signature[:18]}"
        saved = service.ingest_candidate(candidate, actor="human-cli")
        print(saved.model_dump_json(indent=2))
        return

    if args.command == "list":
        records: list[Any]
        if args.kind == "candidates":
            records = store.list_candidates()
        elif args.kind == "memories":
            records = store.list_memories()
        else:
            records = store.list_rules()
        if args.json:
            print(json.dumps([item.model_dump(mode="json") for item in records], indent=2))
        else:
            for item in records:
                title = getattr(item, "title", item.key)
                status = getattr(item, "status", "active")
                print(f"{item.key}\t{status}\t{title}")
        return

    if args.command == "confirm":
        candidate, memory, rule = service.confirm_candidate(
            args.key, reviewer=args.reviewer, note=args.note
        )
        print(
            json.dumps(
                {
                    "candidate": candidate.model_dump(mode="json"),
                    "memory": memory.model_dump(mode="json"),
                    "rule": rule.model_dump(mode="json") if rule else None,
                },
                indent=2,
            )
        )
        return

    if args.command == "reject":
        print(service.reject_candidate(args.key, reviewer=args.reviewer, note=args.note).model_dump_json(indent=2))
        return

    if args.command == "recall":
        knowledge = ProjectKnowledge.model_validate_json(Path(args.knowledge).read_text(encoding="utf-8"))
        impact = ImpactReport.model_validate_json(Path(args.impact).read_text(encoding="utf-8"))
        result = MemoryRecallEngine().recall(
            knowledge,
            impact,
            store.list_memories(project_source_id=knowledge.metadata.source_id),
            store.list_rules(project_source_id=knowledge.metadata.source_id),
        )
        print(result.model_dump_json(indent=2) if args.json else render_recall(result))
