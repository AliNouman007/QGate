from __future__ import annotations

import hashlib
from collections import Counter

from .extractors import analyze_text_file
from .graph import build_dependency_graph, reuse_counts
from .models import (
    ANALYZER_VERSION,
    AnalysisBudget,
    AnalysisMetadata,
    BehaviorCategory,
    CoverageGap,
    FileAnalysis,
    FileRole,
    ProjectKnowledge,
    ProjectSummary,
)
from .scanner import ProjectScanner
from .source import ProjectSource


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
        previous_by_path = self._reusable_previous(previous)
        analyses: list[FileAnalysis] = []
        reused = 0
        analyzed = 0

        for record in records:
            old = previous_by_path.get(record.path)
            if old is not None and old.record.content_hash == record.content_hash:
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
            analyses.append(analyze_text_file(record, text))
            analyzed += 1

        dependencies = build_dependency_graph(analyses)
        summary = self._summary(analyses, dependencies)
        fingerprint = self._fingerprint(analyses)
        metadata = AnalysisMetadata(
            source_id=source.source_id,
            source_fingerprint=fingerprint,
            reused_files=reused,
            analyzed_files=analyzed,
        )
        return ProjectKnowledge(
            metadata=metadata,
            summary=summary,
            files=analyses,
            dependencies=dependencies,
            coverage_gaps=self._dedupe_gaps(gaps),
        )

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
    def _summary(files: list[FileAnalysis], dependencies: list) -> ProjectSummary:
        languages = Counter(file.record.language for file in files if file.record.language)
        roles = Counter(file.record.role.value for file in files)
        categories = Counter(
            behavior.category.value
            for file in files
            for behavior in file.behaviors
            if behavior.meaningful and behavior.category != BehaviorCategory.TECHNICAL_GUARD
        )
        return ProjectSummary(
            total_files=len(files),
            analyzed_files=sum(bool(file.imports or file.behaviors or file.record.role in {FileRole.CONFIG, FileRole.OTHER}) for file in files),
            total_source_bytes=sum(file.record.size_bytes for file in files),
            languages=dict(sorted(languages.items())),
            roles=dict(sorted(roles.items())),
            reused_modules=reuse_counts(dependencies),
            behavioral_categories=dict(sorted(categories.items())),
        )

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
