from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from qgate_project_intelligence.models import Confidence, Evidence, FileAnalysis, ProjectKnowledge

from .classifier import classify_changed_file
from .mapping import knowledge_by_path, map_changed_symbols
from .models import (
    ChangeCategory,
    ChangeSet,
    ChangedFile,
    DependencyStep,
    ImpactCoverageGap,
    ImpactItem,
    ImpactLevel,
    ImpactMetadata,
    ImpactReport,
    ImpactSummary,
    ImpactTargetType,
    SharedImpactGroup,
)

_HUNK_NEARBY_LINES = 3


@dataclass(frozen=True)
class TraversalLimits:
    max_depth: int = 6
    max_nodes: int = 500


class ImpactAnalyzer:
    def __init__(
        self, project_knowledge: ProjectKnowledge, limits: TraversalLimits | None = None
    ) -> None:
        self.knowledge = project_knowledge
        self.limits = limits or TraversalLimits()
        self.by_path = knowledge_by_path(project_knowledge)

    def analyze(self, change_set: ChangeSet) -> ImpactReport:
        changed_symbols = []
        direct: list[ImpactItem] = []
        indirect: list[ImpactItem] = []
        possible: list[ImpactItem] = []
        unknown: list[ImpactItem] = []
        routes: list[ImpactItem] = []
        states: list[ImpactItem] = []
        shared: list[SharedImpactGroup] = []
        gaps = [
            ImpactCoverageGap(path=gap.path, reason=gap.reason, detail=gap.detail)
            for gap in change_set.gaps
        ]

        change_by_path = {file.path: file for file in change_set.files}
        changed_paths = set(change_by_path)
        categories_by_path: dict[str, list[ChangeCategory]] = {}

        for change in change_set.files:
            analysis = self.by_path.get(change.path)
            categories = classify_changed_file(change, analysis)
            if self.knowledge.summary.reused_modules.get(change.path, 0) >= 2:
                categories = sorted(
                    {*categories, ChangeCategory.SHARED}, key=lambda item: item.value
                )
            change.categories = categories
            categories_by_path[change.path] = categories
            symbols = map_changed_symbols(change, analysis)
            changed_symbols.extend(symbols)
            evidence = self._change_evidence(change, analysis)
            direct.append(
                ImpactItem(
                    key=f"file:{change.path}",
                    target_type=ImpactTargetType.FILE,
                    target=change.path,
                    level=ImpactLevel.DIRECT,
                    reason="This file is directly changed by the supplied diff.",
                    confidence=Confidence.HIGH,
                    evidence=evidence,
                    categories=categories,
                )
            )
            for symbol in symbols:
                direct.append(
                    ImpactItem(
                        key=f"symbol:{change.path}:{symbol.symbol_kind}:{symbol.symbol_name}",
                        target_type=(
                            ImpactTargetType.COMPONENT
                            if symbol.symbol_kind == "component"
                            else ImpactTargetType.SYMBOL
                        ),
                        target=symbol.symbol_name,
                        level=ImpactLevel.DIRECT,
                        reason=(
                            "Symbol evidence overlaps or is adjacent to a changed hunk in "
                            f"{change.path}."
                        ),
                        confidence=symbol.confidence,
                        evidence=[symbol.evidence],
                        categories=categories,
                    )
                )
            if analysis is None:
                unknown.append(
                    ImpactItem(
                        key=f"unknown-map:{change.path}",
                        target_type=ImpactTargetType.FILE,
                        target=change.path,
                        level=ImpactLevel.UNKNOWN,
                        reason=(
                            "Changed file is not present in the supplied ProjectKnowledge, so "
                            "structural blast radius cannot be proven."
                        ),
                        confidence=Confidence.LOW,
                        evidence=evidence,
                        categories=categories,
                        needs_runtime_verification=True,
                    )
                )

        paths, traversal_gaps = self._reverse_paths(changed_paths)
        gaps.extend(traversal_gaps)
        for affected_path, dependency_path in paths.items():
            if affected_path in changed_paths:
                continue
            analysis = self.by_path.get(affected_path)
            if analysis is None:
                continue
            source_categories = self._categories_for_dependency_path(
                dependency_path, categories_by_path
            )
            indirect.append(
                ImpactItem(
                    key=f"dependent:{affected_path}",
                    target_type=(
                        ImpactTargetType.COMPONENT
                        if analysis.record.role.value == "component"
                        else ImpactTargetType.MODULE
                    ),
                    target=affected_path,
                    level=ImpactLevel.INDIRECT,
                    reason=(
                        f"This file depends on changed code through {len(dependency_path)} "
                        "deterministic import edge(s)."
                    ),
                    confidence=Confidence.HIGH,
                    evidence=self._path_evidence(dependency_path),
                    dependency_path=dependency_path,
                    categories=source_categories,
                )
            )

        routes.extend(self._affected_routes(changed_paths, paths, categories_by_path))
        states.extend(
            self._affected_states(change_by_path, paths, categories_by_path)
        )
        shared.extend(self._shared_groups(changed_paths, paths, routes))

        impacted_paths = changed_paths | set(paths)
        for project_gap in self.knowledge.coverage_gaps:
            if project_gap.path is None or project_gap.path in impacted_paths:
                gaps.append(
                    ImpactCoverageGap(
                        path=project_gap.path,
                        reason=f"project_intelligence:{project_gap.reason}",
                        detail=project_gap.detail,
                    )
                )

        possible.extend(item for item in states if item.level == ImpactLevel.POSSIBLE)
        direct = _dedupe_items(direct)
        indirect = _dedupe_items(indirect)
        possible = _dedupe_items(possible)
        unknown = _dedupe_items(unknown)
        routes = _dedupe_items(routes)
        states = _dedupe_items(states)
        gaps = _dedupe_gaps(gaps)

        all_items = _dedupe_items(
            [*direct, *indirect, *possible, *unknown, *routes, *states]
        )
        runtime_count = sum(
            1 for item in all_items if item.needs_runtime_verification
        ) + len(gaps)
        summary = ImpactSummary(
            changed_files=len(change_set.files),
            changed_symbols=len(changed_symbols),
            direct_impacts=len(direct),
            indirect_impacts=len(indirect),
            possible_impacts=len(possible),
            unknown_impacts=len(unknown),
            affected_routes=len(routes),
            affected_states=len(states),
            runtime_verification_items=runtime_count,
        )
        return ImpactReport(
            metadata=ImpactMetadata(
                project_source_id=self.knowledge.metadata.source_id,
                project_fingerprint=self.knowledge.metadata.source_fingerprint,
                change_source_id=change_set.source_id,
            ),
            change_set=change_set,
            summary=summary,
            changed_symbols=changed_symbols,
            direct_impacts=direct,
            indirect_impacts=indirect,
            possible_impacts=possible,
            unknown_impacts=unknown,
            affected_routes=routes,
            affected_states=states,
            shared_groups=shared,
            coverage_gaps=gaps,
        )

    def _reverse_paths(
        self, changed_paths: set[str]
    ) -> tuple[dict[str, list[DependencyStep]], list[ImpactCoverageGap]]:
        reverse: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge in self.knowledge.dependencies:
            reverse[edge.target].append((edge.source, edge.module))

        queue: deque[tuple[str, list[DependencyStep], int]] = deque(
            (path, [], 0) for path in sorted(changed_paths)
        )
        result: dict[str, list[DependencyStep]] = {}
        visited = set(changed_paths)
        gaps: list[ImpactCoverageGap] = []
        while queue:
            target, path, depth = queue.popleft()
            if depth >= self.limits.max_depth:
                if reverse.get(target):
                    gaps.append(
                        ImpactCoverageGap(
                            path=target,
                            reason="traversal_depth_limit",
                            detail=(
                                "Reverse dependency traversal stopped at depth "
                                f"{self.limits.max_depth}."
                            ),
                        )
                    )
                continue
            for source, module in reverse.get(target, []):
                step = DependencyStep(source=source, target=target, module=module)
                new_path = [step, *path]
                if source not in result or len(new_path) < len(result[source]):
                    result[source] = new_path
                if source in visited:
                    continue
                if len(visited) >= self.limits.max_nodes:
                    gaps.append(
                        ImpactCoverageGap(
                            path=source,
                            reason="traversal_node_limit",
                            detail=(
                                "Reverse dependency traversal exceeded "
                                f"{self.limits.max_nodes} nodes."
                            ),
                        )
                    )
                    return result, gaps
                visited.add(source)
                queue.append((source, new_path, depth + 1))
        return result, gaps

    def _affected_routes(
        self,
        changed_paths: set[str],
        paths: dict[str, list[DependencyStep]],
        categories_by_path: dict[str, list[ChangeCategory]],
    ) -> list[ImpactItem]:
        items: list[ImpactItem] = []
        for path in sorted(changed_paths | set(paths)):
            analysis = self.by_path.get(path)
            if analysis is None:
                continue
            for route in analysis.routes:
                direct = path in changed_paths
                dependency_path = [] if direct else paths[path]
                items.append(
                    ImpactItem(
                        key=f"route:{route.route}:{path}",
                        target_type=ImpactTargetType.ROUTE,
                        target=route.route,
                        level=ImpactLevel.DIRECT if direct else ImpactLevel.INDIRECT,
                        reason=(
                            f"Route is declared in directly changed file {path}."
                            if direct
                            else (
                                f"Route-owning file {path} depends on changed code through "
                                "a deterministic dependency path."
                            )
                        ),
                        confidence=Confidence.HIGH,
                        evidence=[route.evidence],
                        dependency_path=dependency_path,
                        categories=self._categories_for_dependency_path(
                            dependency_path, categories_by_path
                        ),
                    )
                )
        return items

    def _affected_states(
        self,
        change_by_path: dict[str, ChangedFile],
        paths: dict[str, list[DependencyStep]],
        categories_by_path: dict[str, list[ChangeCategory]],
    ) -> list[ImpactItem]:
        items: list[ImpactItem] = []
        changed_paths = set(change_by_path)
        impacted_paths = changed_paths | set(paths)
        for state in self.knowledge.semantic_states:
            evidence_paths = {evidence.path for evidence in state.evidence}
            relevant = evidence_paths & impacted_paths
            if not relevant:
                continue

            exact_change = any(
                evidence.path in change_by_path
                and self._evidence_overlaps_change(
                    evidence, change_by_path[evidence.path]
                )
                for evidence in state.evidence
            )
            if exact_change:
                level = ImpactLevel.DIRECT
                confidence = state.confidence
                dependency_path: list[DependencyStep] = []
                reason = "State evidence overlaps or is adjacent to a directly changed hunk."
                runtime = state.needs_runtime_verification
            else:
                level = ImpactLevel.POSSIBLE
                confidence = (
                    Confidence.MEDIUM
                    if state.confidence == Confidence.HIGH
                    else state.confidence
                )
                dependent_paths = sorted(relevant - changed_paths)
                dependency_path = paths.get(dependent_paths[0], []) if dependent_paths else []
                reason = (
                    "State is associated with changed or deterministically dependent code, but "
                    "the changed hunk does not directly overlap its evidence; runtime relevance "
                    "must be verified."
                )
                runtime = True
            items.append(
                ImpactItem(
                    key=f"state:{state.key}",
                    target_type=ImpactTargetType.STATE,
                    target=state.label,
                    level=level,
                    reason=reason,
                    confidence=confidence,
                    evidence=state.evidence,
                    dependency_path=dependency_path,
                    categories=self._categories_for_dependency_path(
                        dependency_path, categories_by_path
                    ),
                    needs_runtime_verification=runtime,
                    explanation=state.explanation,
                )
            )
        return items

    def _shared_groups(
        self,
        changed_paths: set[str],
        paths: dict[str, list[DependencyStep]],
        routes: list[ImpactItem],
    ) -> list[SharedImpactGroup]:
        groups: list[SharedImpactGroup] = []
        for changed in sorted(changed_paths):
            reuse_count = self.knowledge.summary.reused_modules.get(changed, 0)
            if reuse_count < 2:
                continue
            affected_files = sorted(
                path
                for path, dependency_path in paths.items()
                if dependency_path and dependency_path[-1].target == changed
            )
            affected_routes = sorted(
                {
                    item.target
                    for item in routes
                    if any(step.target == changed for step in item.dependency_path)
                }
            )
            groups.append(
                SharedImpactGroup(
                    changed_target=changed,
                    reuse_count=reuse_count,
                    affected_files=affected_files,
                    affected_routes=affected_routes,
                )
            )
        return groups

    def _change_evidence(
        self, change: ChangedFile, analysis: FileAnalysis | None
    ) -> list[Evidence]:
        if change.hunks:
            hunk = change.hunks[0]
            line = hunk.new_range.start or hunk.old_range.start or 1
            return [
                Evidence(
                    path=change.path,
                    line=max(line, 1),
                    excerpt=hunk.excerpt[:240] or hunk.header,
                    kind="diff_hunk",
                )
            ]
        if analysis is not None and analysis.symbols:
            return [analysis.symbols[0].evidence]
        return [
            Evidence(
                path=change.path,
                line=1,
                excerpt="File changed; no parsed hunk evidence available.",
                kind="change",
            )
        ]

    def _path_evidence(self, path: list[DependencyStep]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for step in path:
            for edge in self.knowledge.dependencies:
                if (
                    edge.source == step.source
                    and edge.target == step.target
                    and edge.module == step.module
                ):
                    evidence.append(edge.evidence)
                    break
        return evidence

    @staticmethod
    def _evidence_overlaps_change(evidence: Evidence, change: ChangedFile) -> bool:
        for hunk in change.hunks:
            ranges = (hunk.old_range, hunk.new_range)
            for line_range in ranges:
                if line_range.start == 0:
                    continue
                if (
                    line_range.start - _HUNK_NEARBY_LINES
                    <= evidence.line
                    <= line_range.end + _HUNK_NEARBY_LINES
                ):
                    return True
        return False

    @staticmethod
    def _categories_for_dependency_path(
        path: list[DependencyStep], categories_by_path: dict[str, list[ChangeCategory]]
    ) -> list[ChangeCategory]:
        if not path:
            merged = {
                category
                for categories in categories_by_path.values()
                for category in categories
            }
        else:
            changed_target = path[-1].target
            merged = set(categories_by_path.get(changed_target, []))
        return sorted(merged or {ChangeCategory.GENERAL}, key=lambda item: item.value)


def _dedupe_items(items: list[ImpactItem]) -> list[ImpactItem]:
    seen: set[str] = set()
    result: list[ImpactItem] = []
    for item in items:
        if item.key not in seen:
            seen.add(item.key)
            result.append(item)
    return result


def _dedupe_gaps(gaps: list[ImpactCoverageGap]) -> list[ImpactCoverageGap]:
    seen: set[tuple[str | None, str, str | None]] = set()
    result: list[ImpactCoverageGap] = []
    for gap in gaps:
        key = (gap.path, gap.reason, gap.detail)
        if key not in seen:
            seen.add(key)
            result.append(gap)
    return result
