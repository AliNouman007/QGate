from __future__ import annotations

from collections import Counter

from .extractors import import_candidates
from .models import DependencyEdge, FileAnalysis


def build_dependency_graph(files: list[FileAnalysis]) -> list[DependencyEdge]:
    indexed_paths = {file.record.path for file in files}
    edges: list[DependencyEdge] = []
    seen: set[tuple[str, str, int]] = set()

    for file in files:
        for import_fact in file.imports:
            target = _resolve_target(
                source_path=file.record.path,
                module=import_fact.module,
                language=file.record.language,
                indexed_paths=indexed_paths,
            )
            if target is None:
                continue
            key = (file.record.path, target, import_fact.evidence.line)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                DependencyEdge(
                    source=file.record.path,
                    target=target,
                    module=import_fact.module,
                    evidence=import_fact.evidence,
                )
            )
    return edges


def reuse_counts(edges: list[DependencyEdge]) -> dict[str, int]:
    counts = Counter(edge.target for edge in edges)
    return dict(
        sorted(
            ((path, count) for path, count in counts.items() if count > 1),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _resolve_target(
    source_path: str,
    module: str,
    language: str | None,
    indexed_paths: set[str],
) -> str | None:
    for candidate in import_candidates(source_path, module, language):
        normalized = _normalize(candidate)
        if normalized in indexed_paths:
            return normalized
    return None


def _normalize(path: str) -> str:
    parts: list[str] = []
    for part in path.replace("\\", "/").split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)
