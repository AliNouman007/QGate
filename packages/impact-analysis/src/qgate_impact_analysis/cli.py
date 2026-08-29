from __future__ import annotations

import argparse
from pathlib import Path

from qgate_project_intelligence.models import ProjectKnowledge

from .engine import ImpactAnalyzer, TraversalLimits
from .report import render_impact_report
from .source import LocalGitSource, UnifiedDiffSource
from .store import JsonImpactStore

DEFAULT_STORE_DIR = "~/.qgate/impact-analysis"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze code-change blast radius with QGate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    git = subparsers.add_parser("git", help="Analyze a local Git ref comparison")
    git.add_argument("repo")
    git.add_argument("--base", default="main")
    git.add_argument("--head", default="HEAD")
    _common_args(git)

    patch = subparsers.add_parser("patch", help="Analyze a unified diff/patch file")
    patch.add_argument("patch")
    _common_args(patch)
    return parser


def _common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--knowledge", required=True, help="Path to ProjectKnowledge JSON")
    parser.add_argument("--store-dir", default=DEFAULT_STORE_DIR)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--max-nodes", type=int, default=500)


def main() -> int:
    args = build_parser().parse_args()
    knowledge_path = Path(args.knowledge).expanduser().resolve()
    if not knowledge_path.exists():
        raise SystemExit(f"ProjectKnowledge file does not exist: {knowledge_path}")
    knowledge = ProjectKnowledge.model_validate_json(knowledge_path.read_text(encoding="utf-8"))

    if args.command == "git":
        repo = Path(args.repo).expanduser().resolve()
        expected_source_id = f"local:{repo.as_posix()}"
        if knowledge.metadata.source_id != expected_source_id:
            raise SystemExit(
                "ProjectKnowledge source mismatch: analyze the same repository before running impact analysis. "
                f"expected {expected_source_id!r}, got {knowledge.metadata.source_id!r}"
            )
        change_set = LocalGitSource(repo, base_ref=args.base, head_ref=args.head).load()
    elif args.command == "patch":
        change_set = UnifiedDiffSource.from_file(args.patch).load()
    else:  # pragma: no cover - argparse enforces the command set
        raise RuntimeError("Unsupported command")

    analyzer = ImpactAnalyzer(
        knowledge,
        TraversalLimits(max_depth=args.max_depth, max_nodes=args.max_nodes),
    )
    report = analyzer.analyze(change_set)
    stored = JsonImpactStore(args.store_dir).save(report)
    print(f"Stored impact report: {stored}")
    print(report.model_dump_json(indent=2) if args.as_json else render_impact_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
