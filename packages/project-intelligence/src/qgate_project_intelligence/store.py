from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ProjectKnowledge


class JsonKnowledgeStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def path_for(self, source_id: str) -> Path:
        key = hashlib.sha256(source_id.encode()).hexdigest()[:24]
        return self.root / f"{key}.json"

    def save(self, knowledge: ProjectKnowledge) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(knowledge.metadata.source_id)
        path.write_text(knowledge.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, source_id: str) -> ProjectKnowledge | None:
        path = self.path_for(source_id)
        if not path.exists():
            return None
        return ProjectKnowledge.model_validate_json(path.read_text(encoding="utf-8"))

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
