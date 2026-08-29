from __future__ import annotations

import re
from pathlib import Path

from .models import GateReport

_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


class JsonGateReportStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.reports_dir = self.root / "reports"

    @staticmethod
    def _safe_key(key: str) -> bool:
        return bool(_KEY_RE.fullmatch(key))

    def save(self, report: GateReport) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.reports_dir / f"{report.metadata.report_key}.json"
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_key(self, key: str) -> GateReport | None:
        if not self._safe_key(key):
            return None
        path = self.reports_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            return GateReport.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def list_reports(self, *, project_source_id: str | None = None) -> list[GateReport]:
        if not self.reports_dir.exists():
            return []
        reports: list[GateReport] = []
        for path in sorted(self.reports_dir.glob("*.json")):
            try:
                report = GateReport.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_source_id is None or report.metadata.project_source_id == project_source_id:
                reports.append(report)
        reports.sort(key=lambda item: item.metadata.generated_at, reverse=True)
        return reports

    def latest(self, *, project_source_id: str | None = None) -> GateReport | None:
        reports = self.list_reports(project_source_id=project_source_id)
        return reports[0] if reports else None
