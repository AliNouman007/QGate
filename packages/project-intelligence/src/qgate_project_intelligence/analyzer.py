from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from .extractors import analyze_text_file
from .frameworks import detect_declared_frontend_frameworks, extract_framework_knowledge
from .graph import build_dependency_graph, reuse_counts
from .models import (
    ANALYZER_VERSION,
    AnalysisBudget,
    AnalysisMetadata,
    BehaviorCategory,
    CoverageGap,
    DependencyEdge,
    FileAnalysis,
    FileRecord,
    FrameworkKind,
    ProjectKnowledge,
    ProjectSummary,
    SemanticState,
    SymbolKind,
)
from .scanner import ProjectScanner
from .semantic import (
    build_evidence_packs,
    classify_evidence_packs,
    derive_concrete_branch_states,
)

if TYPE_CHECKING:
    from .source import ProjectSource

_FRONTEND_LANGUAGES = {"javascript", "typescript", "vue", "svelte"}


class ProjectIntelligenceAnalyzer:
    def __init__(self, budget: AnalysisBudget | None = None) -> None:
        self.scanner = ProjectScanner(budget)

    def analyze(
        self,
        source: ProjectSource,
        *,
        previous: ProjectKnowledge | None = None,
    ) -> ProjectKnowledge:
        records, gaps = self.scanner.scan_inventory(source)
        declared_frameworks = self._declared_frameworks(source, records, gaps)
        previous_by_path = self._reusable_previous(previous)
        previous_declared = set(previous.summary.declared_frameworks) if previous is not None else set()
        current_declared = {framework.value for framework in declared_frameworks}
        frontend_context_changed = previous is not None and previous_declared != current_declared
        analyses: list[FileAnalysis] = []
        reused = 0
        analyzed = 0

        for record in records:
            old = previous_by_path.get(record.path)
            can_reuse = not (frontend_context_changed and record.language in _FRONTEND_LANGUAGES)
            if old is not None and old.record.content_hash == record.content_hash and can_reuse:
                analyses.append(old)
                reused += 1
                continue
            text, gap = self.scanner.read_text(source, record)
            if gap is not None:
                gaps.append(gap)
                analyses.append(FileAnalysis(record=record))
                continue
            if text is None:
                analyses.append(FileAnalysis(record=record))
                continue
            analysis = analyze_text_file(record, text)
            frameworks, routes, symbols = extract_framework_knowledge(
                record,
                text,
                declared_frameworks,
            )
            analyses.append(
                analysis.model_copy(
                    update={"frameworks": frameworks, "routes": routes, "symbols": symbols}
                )
            )
            analyzed += 1

        dependencies = build_dependency_graph(analyses)
        summary = self._summary(analyses, dependencies, declared_frameworks)
        metadata = AnalysisMetadata(
            source_id=source.source_id,
            source_fingerprint=self._fingerprint(analyses),
            reused_files=reused,
            analyzed_files=analyzed,
        )
        generic_states = classify_evidence_packs(build_evidence_packs(analyses))
        concrete_states = derive_concrete_branch_states(analyses)
        semantic_states = self._dedupe_states([*concrete_states, *generic_states])
        return ProjectKnowledge(
            metadata=metadata,
            summary=summary,
            files=analyses,
            dependencies=dependencies,
            semantic_states=semantic_states,
            coverage_gaps=self._dedupe_gaps(gaps),
        )

    def _declared_frameworks(
        self,
        source: ProjectSource,
        records: list[FileRecord],
        gaps: list[CoverageGap],
    ) -> set[FrameworkKind]:
        manifest_texts: list[str] = []
        for record in records:
            if PurePosixPath(record.path).name != "package.json":
                continue
            text, gap = self.scanner.read_text(source, record)
            if gap is not None:
                gaps.append(gap)
                continue
            if text is not None:
                manifest_texts.append(text)
        return detect_declared_frontend_frameworks(manifest_texts)

    @staticmethod
    def _reusable_previous(previous: ProjectKnowledge | None) -> dict[str, FileAnalysis]:
        if previous is None or previous.metadata.analyzer_version != ANALYZER_VERSION:
            return {}
        return {file.record.path: file for file in previous.files}

    @staticmethod
    def _fingerprint(files: list[FileAnalysis]) -> str:
        digest = hashlib.sha256()
        for file in sorted(files, key=lambda item: item.record.path):
            digest.update(file.record.path.encode())
            digest.update(b"\0")
            digest.update(file.record.content_hash.encode())
            digest.update(b"\n")
        return digest.hexdigest()

    @staticmethod
    def _summary(
        files: list[FileAnalysis],
        dependencies: list[DependencyEdge],
        declared_frameworks: set[FrameworkKind],
    ) -> ProjectSummary:
        languages = Counter(file.record.language for file in files if file.record.language)
        frameworks = Counter(
            fact.framework.value
            for file in files
            for fact in file.frameworks
            if fact.feature in {"react_module", "next_module", "typed_module"}
        )
        roles = Counter(file.record.role.value for file in files)
        categories = Counter(
            behavior.category.value
            for file in files
            for behavior in file.behaviors
            if behavior.meaningful and behavior.category != BehaviorCategory.TECHNICAL_GUARD
        )
        return ProjectSummary(
            total_files=len(files),
            analyzed_files=len(files),
            total_source_bytes=sum(file.record.size_bytes for file in files),
            languages=dict(sorted(languages.items())),
            frameworks=dict(sorted(frameworks.items())),
            declared_frameworks=sorted(framework.value for framework in declared_frameworks),
            roles=dict(sorted(roles.items())),
            reused_modules=reuse_counts(dependencies),
            behavioral_categories=dict(sorted(categories.items())),
            route_count=sum(len(file.routes) for file in files),
            component_count=sum(
                1
                for file in files
                for symbol in file.symbols
                if symbol.kind == SymbolKind.COMPONENT
            ),
            hook_count=sum(
                1 for file in files for symbol in file.symbols if symbol.kind == SymbolKind.HOOK
            ),
        )

    @staticmethod
    def _dedupe_states(states: list[SemanticState]) -> list[SemanticState]:
        seen: set[tuple[str, str]] = set()
        result: list[SemanticState] = []
        for state in states:
            key = (state.key, state.label)
            if key in seen:
                continue
            seen.add(key)
            result.append(state)
        return result

    @staticmethod
    def _dedupe_gaps(gaps: list[CoverageGap]) -> list[CoverageGap]:
        seen: set[tuple[str | None, str, str | None]] = set()
        result: list[CoverageGap] = []
        for gap in gaps:
            key = (gap.path, gap.reason, gap.detail)
            if key in seen:
                continue
            seen.add(key)
            result.append(gap)
        return result
