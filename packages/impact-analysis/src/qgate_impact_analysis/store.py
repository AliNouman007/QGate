from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import ImpactReport

_KEY_RE = re.compile(r"^[0-9a-f]{24}$")


class JsonImpactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def key_for(report: ImpactReport) -> str:
        identity = (
            f"{report.metadata.project_source_id}\0{report.metadata.project_fingerprint}\0"
            f"{report.metadata.change_source_id}"
        )
        return hashlib.sha256(identity.encode()).hexdigest()[:24]

    def path_for(self, report: ImpactReport) -> Path:
        return self.root / f"{self.key_for(report)}.json"

    def save(self, report: ImpactReport) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(report)
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_key(self, key: str) -> ImpactReport | None:
        if not _KEY_RE.fullmatch(key):
            return None
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        return self.load_path(path)

    def list_reports(self) -> list[ImpactReport]:
        if not self.root.exists():
            return []
        reports: list[ImpactReport] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                reports.append(self.load_path(path))
            except (OSError, ValueError):
                continue
        return sorted(reports, key=lambda item: item.metadata.analyzed_at, reverse=True)

    def latest(self) -> ImpactReport | None:
        reports = self.list_reports()
        return reports[0] if reports else None

    @staticmethod
    def load_path(path: str | Path) -> ImpactReport:
        file_path = Path(path).expanduser().resolve()
        return ImpactReport.model_validate_json(file_path.read_text(encoding="utf-8"))
