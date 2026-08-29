from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from .models import AnalysisBudget, CoverageGap, FileRecord, FileRole

if TYPE_CHECKING:
    from pathlib import Path

    from .source import ProjectSource

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "vendor",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".svelte": "svelte",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}

CONFIG_NAMES = {
    "package.json",
    "pyproject.toml",
    "tsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "webpack.config.js",
    "requirements.txt",
    "docker-compose.yml",
    "docker-compose.yaml",
}


class ProjectScanner:
    def __init__(self, budget: AnalysisBudget | None = None) -> None:
        self.budget = budget or AnalysisBudget()

    def scan_inventory(self, source: ProjectSource) -> tuple[list[FileRecord], list[CoverageGap]]:
        records: list[FileRecord] = []
        gaps: list[CoverageGap] = []
        total_bytes = 0

        for path in sorted(source.iter_files()):
            relative = path.relative_to(source.root)
            if self._ignored(relative):
                continue
            if len(relative.parts) > self.budget.max_depth:
                gaps.append(CoverageGap(path=relative.as_posix(), reason="max_depth_exceeded"))
                continue
            if len(records) >= self.budget.max_files:
                gaps.append(
                    CoverageGap(reason="max_files_exceeded", detail=str(self.budget.max_files))
                )
                break
            try:
                size = path.stat().st_size
            except OSError as exc:
                gaps.append(
                    CoverageGap(path=relative.as_posix(), reason="stat_failed", detail=str(exc))
                )
                continue
            if size > self.budget.max_file_bytes:
                gaps.append(
                    CoverageGap(
                        path=relative.as_posix(),
                        reason="file_too_large",
                        detail=f"{size}>{self.budget.max_file_bytes}",
                    )
                )
                continue
            if total_bytes + size > self.budget.max_total_bytes:
                gaps.append(
                    CoverageGap(
                        reason="max_total_bytes_exceeded", detail=str(self.budget.max_total_bytes)
                    )
                )
                break
            try:
                content = path.read_bytes()
            except OSError as exc:
                gaps.append(
                    CoverageGap(path=relative.as_posix(), reason="read_failed", detail=str(exc))
                )
                continue
            if b"\x00" in content[:4096]:
                gaps.append(CoverageGap(path=relative.as_posix(), reason="binary_file_skipped"))
                continue
            total_bytes += size
            records.append(
                FileRecord(
                    path=relative.as_posix(),
                    size_bytes=size,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    language=self._language(path),
                    role=self._role(relative),
                )
            )
        return records, gaps

    @staticmethod
    def read_text(
        source: ProjectSource, record: FileRecord
    ) -> tuple[str | None, CoverageGap | None]:
        path = source.root / record.path
        try:
            return path.read_text(encoding="utf-8"), None
        except UnicodeDecodeError:
            return None, CoverageGap(path=record.path, reason="unsupported_text_encoding")
        except OSError as exc:
            return None, CoverageGap(path=record.path, reason="read_failed", detail=str(exc))

    @staticmethod
    def _ignored(relative: Path) -> bool:
        return any(part in IGNORED_DIRS for part in relative.parts)

    @staticmethod
    def _language(path: Path) -> str | None:
        return LANGUAGE_BY_SUFFIX.get(path.suffix.lower())

    @staticmethod
    def _role(relative: Path) -> FileRole:
        lower_parts = [part.lower() for part in relative.parts]
        name = relative.name.lower()
        stem = relative.stem.lower()
        if name in CONFIG_NAMES or (
            name.startswith(".") and relative.suffix in {".json", ".yaml", ".yml"}
        ):
            return FileRole.CONFIG
        if "test" in stem or "tests" in lower_parts or "__tests__" in lower_parts or "spec" in stem:
            return FileRole.TEST
        if any(part in {"routes", "pages", "app"} for part in lower_parts[:-1]):
            return FileRole.ROUTE
        if any(
            part in {"components", "component"} for part in lower_parts[:-1]
        ) or relative.suffix in {".jsx", ".tsx", ".vue", ".svelte"}:
            return FileRole.COMPONENT
        if any(part in {"services", "service", "api", "clients"} for part in lower_parts[:-1]):
            return FileRole.SERVICE
        if any(
            part in {"store", "stores", "state", "reducers", "contexts"}
            for part in lower_parts[:-1]
        ):
            return FileRole.STATE
        if relative.suffix.lower() in LANGUAGE_BY_SUFFIX:
            return FileRole.SOURCE
        return FileRole.OTHER
