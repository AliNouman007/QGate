from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from qgate_project_intelligence.models import ProjectKnowledge, SemanticState


@dataclass(frozen=True)
class StateFamily:
    key: str
    states: tuple[SemanticState, ...]
    surface_paths: tuple[str, ...]


_PAIR_TOKENS: tuple[tuple[str, str], ...] = (
    ("authenticated", "unauthenticated"),
    ("logged in", "logged out"),
    ("enabled", "disabled"),
    ("on", "off"),
    ("present", "absent"),
    ("available", "missing"),
    ("loaded", "loading"),
    ("success", "error"),
    ("allowed", "denied"),
    ("desktop", "mobile"),
    ("with ", "without "),
)


def state_families(knowledge: ProjectKnowledge, *, max_variants_per_surface: int) -> list[StateFamily]:
    by_surface_kind: dict[tuple[str, str], list[SemanticState]] = defaultdict(list)
    for state in knowledge.semantic_states:
        paths = sorted({item.path for item in state.evidence})
        for path in paths:
            by_surface_kind[(path, state.kind.value)].append(state)

    families: list[StateFamily] = []
    for (path, kind), states in sorted(by_surface_kind.items()):
        unique = _dedupe_states(states)[:max_variants_per_surface]
        if not unique:
            continue
        families.append(StateFamily(key=f"{path}:{kind}", states=tuple(unique), surface_paths=(path,)))
    return families


def related_state_pair(states: tuple[SemanticState, ...]) -> tuple[SemanticState, SemanticState] | None:
    if len(states) < 2:
        return None
    for index, left in enumerate(states):
        left_text = f"{left.key} {left.label} {left.explanation}".lower()
        for right in states[index + 1 :]:
            right_text = f"{right.key} {right.label} {right.explanation}".lower()
            if _looks_complementary(left_text, right_text):
                return left, right
    return states[0], states[1]


def _looks_complementary(left: str, right: str) -> bool:
    return any((a in left and b in right) or (b in left and a in right) for a, b in _PAIR_TOKENS)


def _dedupe_states(states: list[SemanticState]) -> list[SemanticState]:
    result: list[SemanticState] = []
    seen: set[str] = set()
    for state in states:
        if state.key in seen:
            continue
        seen.add(state.key)
        result.append(state)
    return result
