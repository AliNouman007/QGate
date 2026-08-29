from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import ScenarioPlan

_KEY_RE = re.compile(r"^[0-9a-f]{24}$")


class JsonScenarioPlanStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def key_for(plan: ScenarioPlan) -> str:
        identity = (
            f"{plan.metadata.project_source_id}\0{plan.metadata.project_fingerprint}\0"
            f"{plan.metadata.impact_change_source_id}\0"
            + "\0".join(scenario.key for scenario in plan.scenarios)
        )
        return hashlib.sha256(identity.encode()).hexdigest()[:24]

    def path_for(self, plan: ScenarioPlan) -> Path:
        return self.root / f"{self.key_for(plan)}.json"

    def save(self, plan: ScenarioPlan) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(plan)
        path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_key(self, key: str) -> ScenarioPlan | None:
        if not _KEY_RE.fullmatch(key):
            return None
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        return self.load_path(path)

    def list_plans(self) -> list[ScenarioPlan]:
        if not self.root.exists():
            return []
        plans: list[ScenarioPlan] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                plans.append(self.load_path(path))
            except (OSError, ValueError):
                continue
        return sorted(plans, key=lambda item: item.metadata.generated_at, reverse=True)

    def latest(self) -> ScenarioPlan | None:
        plans = self.list_plans()
        return plans[0] if plans else None

    @staticmethod
    def load_path(path: str | Path) -> ScenarioPlan:
        file_path = Path(path).expanduser().resolve()
        return ScenarioPlan.model_validate_json(file_path.read_text(encoding="utf-8"))
