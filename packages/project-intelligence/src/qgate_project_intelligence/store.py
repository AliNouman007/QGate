from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import ProjectKnowledge

_KEY_RE = re.compile(r"^[0-9a-f]{24}$")


class JsonKnowledgeStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def key_for(source_id: str) -> str:
        return hashlib.sha256(source_id.encode()).hexdigest()[:24]

    def path_for(self, source_id: str) -> Path:
        return self.root / f"{self.key_for(source_id)}.json"

    def save(self, knowledge: ProjectKnowledge) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(knowledge.metadata.source_id)
        path.write_text(knowledge.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, source_id: str) -> ProjectKnowledge | None:
        path = self.path_for(source_id)
        if not path.exists():
            return None
        return self.load_path(path)

    def load_key(self, key: str) -> ProjectKnowledge | None:
        if not _KEY_RE.fullmatch(key):
            return None
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        return self.load_path(path)

    def list_projects(self) -> list[ProjectKnowledge]:
        if not self.root.exists():
            return []
        projects: list[ProjectKnowledge] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                projects.append(self.load_path(path))
            except (OSError, ValueError):
                continue
        return sorted(projects, key=lambda item: item.metadata.analyzed_at, reverse=True)

    def latest(self) -> ProjectKnowledge | None:
        projects = self.list_projects()
        return projects[0] if projects else None

    @staticmethod
    def load_path(path: str | Path) -> ProjectKnowledge:
        file_path = Path(path).expanduser().resolve()
        return ProjectKnowledge.model_validate_json(file_path.read_text(encoding="utf-8"))
