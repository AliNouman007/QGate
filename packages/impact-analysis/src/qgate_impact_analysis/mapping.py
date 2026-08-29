from __future__ import annotations

from qgate_project_intelligence.models import Confidence, FileAnalysis, ProjectKnowledge

from .models import ChangedFile, ChangedSymbol

_SYMBOL_NEARBY_LINES = 3


def knowledge_by_path(knowledge: ProjectKnowledge) -> dict[str, FileAnalysis]:
    return {file.record.path: file for file in knowledge.files}


def map_changed_symbols(change: ChangedFile, analysis: FileAnalysis | None) -> list[ChangedSymbol]:
    if analysis is None or not analysis.symbols or not change.hunks:
        return []

    mapped: list[ChangedSymbol] = []
    seen: set[tuple[str, str]] = set()
    for symbol in analysis.symbols:
        for hunk in change.hunks:
            if _line_near_range(symbol.evidence.line, hunk.new_range.start, hunk.new_range.end) or _line_near_range(
                symbol.evidence.line, hunk.old_range.start, hunk.old_range.end
            ):
                key = (symbol.name, symbol.kind.value)
                if key not in seen:
                    seen.add(key)
                    mapped.append(
                        ChangedSymbol(
                            file_path=change.path,
                            symbol_name=symbol.name,
                            symbol_kind=symbol.kind.value,
                            confidence=Confidence.HIGH,
                            evidence=symbol.evidence,
                        )
                    )
                break
    return mapped


def _line_near_range(line: int, start: int, end: int) -> bool:
    if start == 0:
        return False
    return start - _SYMBOL_NEARBY_LINES <= line <= end + _SYMBOL_NEARBY_LINES
