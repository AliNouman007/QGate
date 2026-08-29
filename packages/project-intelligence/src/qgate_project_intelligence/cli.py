from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import ProjectIntelligenceAnalyzer
from .models import AnalysisBudget
from .report import render_project_map
from .source import LocalPathSource, ZipProjectSource
from .store import JsonKnowledgeStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze a project with QGate Project Intelligence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a local directory or ZIP project")
    analyze.add_argument("path")
    analyze.add_argument("--store-dir")
    analyze.add_argument("--previous")
    analyze.add_argument("--json", action="store_true", dest="as_json")
    analyze.add_argument("--max-files", type=int, default=10_000)
    analyze.add_argument("--max-file-bytes", type=int, default=512_000)
    analyze.add_argument("--max-total-bytes", type=int, default=100_000_000)
    analyze.add_argument("--max-depth", type=int, default=32)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command != "analyze":
        raise RuntimeError("Unsupported command")

    project_path = Path(args.path).expanduser().resolve()
    previous = JsonKnowledgeStore.load_path(args.previous) if args.previous else None
    budget = AnalysisBudget(
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        max_depth=args.max_depth,
    )
    analyzer = ProjectIntelligenceAnalyzer(budget)

    if project_path.suffix.lower() == ".zip":
        with ZipProjectSource(project_path) as source:
            knowledge = analyzer.analyze(source, previous=previous)
    else:
        source = LocalPathSource(project_path)
        knowledge = analyzer.analyze(source, previous=previous)

    if args.store_dir:
        stored_path = JsonKnowledgeStore(args.store_dir).save(knowledge)
        print(f"Stored knowledge: {stored_path}")

    print(knowledge.model_dump_json(indent=2) if args.as_json else render_project_map(knowledge))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
