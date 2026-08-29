from __future__ import annotations

import hashlib

from .models import Scenario
from .prioritization import stricter_readiness, stronger_priority


def scenario_signature(scenario: Scenario) -> str:
    normalized = "|".join(
        [
            scenario.kind.value,
            ",".join(sorted(scenario.routes)),
            ",".join(sorted(scenario.states)),
            ";".join(step.action.strip().lower() for step in scenario.steps),
            ";".join(step.expected.strip().lower() for step in scenario.steps),
        ]
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:20]


def merge_scenarios(existing: Scenario, incoming: Scenario) -> Scenario:
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    confidence = (
        existing.confidence
        if confidence_rank[existing.confidence.value] >= confidence_rank[incoming.confidence.value]
        else incoming.confidence
    )
    evidence_by_key = {
        (item.path, item.line, item.kind, item.excerpt): item
        for item in [*existing.evidence, *incoming.evidence]
    }
    return existing.model_copy(
        update={
            "priority": stronger_priority(existing.priority, incoming.priority),
            "readiness": stricter_readiness(existing.readiness, incoming.readiness),
            "confidence": confidence,
            "source_impact_keys": sorted(set(existing.source_impact_keys + incoming.source_impact_keys)),
            "evidence": list(evidence_by_key.values()),
            "targets": sorted(set(existing.targets + incoming.targets)),
            "needs_runtime_discovery": existing.needs_runtime_discovery or incoming.needs_runtime_discovery,
            "manual_reason": existing.manual_reason or incoming.manual_reason,
        }
    )
