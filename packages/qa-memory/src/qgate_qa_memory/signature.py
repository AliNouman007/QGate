from __future__ import annotations

import hashlib
import re

from .models import MemoryCandidate



def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _norm_list(values: list[str]) -> list[str]:
    return sorted({_norm(value) for value in values if value.strip()})


def candidate_signature(candidate: MemoryCandidate) -> str:
    parts = [
        _norm(candidate.project_source_id),
        candidate.kind.value,
        ",".join(_norm_list(candidate.routes)),
        ",".join(_norm_list(candidate.components)),
        ",".join(_norm_list(candidate.symbols)),
        ",".join(_norm_list(candidate.states)),
        _norm(candidate.invariant),
        _norm(candidate.source_scenario_key or ""),
    ]
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()[:24]


def semantic_signature(*, project_source_id: str, invariant: str, routes: list[str], components: list[str], symbols: list[str], states: list[str]) -> str:
    parts = [
        _norm(project_source_id),
        _norm(invariant),
        ",".join(_norm_list(routes)),
        ",".join(_norm_list(components)),
        ",".join(_norm_list(symbols)),
        ",".join(_norm_list(states)),
    ]
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()[:24]
