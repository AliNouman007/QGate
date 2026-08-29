from __future__ import annotations

import re
from pathlib import Path

from .models import ConfirmedMemory, MemoryAuditEvent, MemoryCandidate, RegressionRule

_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


class JsonQAMemoryStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.candidates_dir = self.root / "candidates"
        self.memories_dir = self.root / "memories"
        self.rules_dir = self.root / "rules"
        self.audit_dir = self.root / "audit"

    @staticmethod
    def _safe_key(key: str) -> bool:
        return bool(_KEY_RE.fullmatch(key))

    @staticmethod
    def _paths(directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(directory.glob("*.json"))

    def save_candidate(self, candidate: MemoryCandidate) -> Path:
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        path = self.candidates_dir / f"{candidate.key}.json"
        path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_candidate(self, key: str) -> MemoryCandidate | None:
        if not self._safe_key(key):
            return None
        path = self.candidates_dir / f"{key}.json"
        if not path.exists():
            return None
        return MemoryCandidate.model_validate_json(path.read_text(encoding="utf-8"))

    def list_candidates(self, *, project_source_id: str | None = None) -> list[MemoryCandidate]:
        items: list[MemoryCandidate] = []
        for path in self._paths(self.candidates_dir):
            try:
                item = MemoryCandidate.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_source_id is None or item.project_source_id == project_source_id:
                items.append(item)
        return items

    def save_memory(self, memory: ConfirmedMemory) -> Path:
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        path = self.memories_dir / f"{memory.key}.json"
        path.write_text(memory.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_memory(self, key: str) -> ConfirmedMemory | None:
        if not self._safe_key(key):
            return None
        path = self.memories_dir / f"{key}.json"
        if not path.exists():
            return None
        return ConfirmedMemory.model_validate_json(path.read_text(encoding="utf-8"))

    def list_memories(self, *, project_source_id: str | None = None) -> list[ConfirmedMemory]:
        items: list[ConfirmedMemory] = []
        for path in self._paths(self.memories_dir):
            try:
                item = ConfirmedMemory.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_source_id is None or item.project_source_id == project_source_id:
                items.append(item)
        return items

    def save_rule(self, rule: RegressionRule) -> Path:
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        path = self.rules_dir / f"{rule.key}.json"
        path.write_text(rule.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_rule(self, key: str) -> RegressionRule | None:
        if not self._safe_key(key):
            return None
        path = self.rules_dir / f"{key}.json"
        if not path.exists():
            return None
        return RegressionRule.model_validate_json(path.read_text(encoding="utf-8"))

    def list_rules(self, *, project_source_id: str | None = None) -> list[RegressionRule]:
        items: list[RegressionRule] = []
        for path in self._paths(self.rules_dir):
            try:
                item = RegressionRule.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if project_source_id is None or item.project_source_id == project_source_id:
                items.append(item)
        return items

    def append_audit(self, event: MemoryAuditEvent) -> Path:
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        path = self.audit_dir / f"{event.occurred_at.timestamp():.6f}-{event.key}.json"
        path.write_text(event.model_dump_json(indent=2), encoding="utf-8")
        return path

    def list_audit(self) -> list[MemoryAuditEvent]:
        events: list[MemoryAuditEvent] = []
        for path in self._paths(self.audit_dir):
            try:
                events.append(MemoryAuditEvent.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return events
