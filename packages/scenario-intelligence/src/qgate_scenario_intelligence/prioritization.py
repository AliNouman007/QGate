from __future__ import annotations

from qgate_impact_analysis.models import ImpactItem, ImpactLevel
from qgate_project_intelligence.models import Confidence

from .models import AutomationReadiness, ScenarioPriority

_PRIORITY_ORDER = {
    ScenarioPriority.P0: 0,
    ScenarioPriority.P1: 1,
    ScenarioPriority.P2: 2,
    ScenarioPriority.P3: 3,
}

_READINESS_ORDER = {
    AutomationReadiness.BLOCKED_BY_GAP: 0,
    AutomationReadiness.MANUAL_ONLY: 1,
    AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED: 2,
    AutomationReadiness.READY: 3,
}


def priority_for_impact(item: ImpactItem, *, shared_breadth: int = 0) -> ScenarioPriority:
    if item.level == ImpactLevel.DIRECT and item.confidence == Confidence.HIGH:
        return ScenarioPriority.P0 if shared_breadth >= 3 else ScenarioPriority.P1
    if item.level == ImpactLevel.INDIRECT and item.confidence != Confidence.LOW:
        return ScenarioPriority.P2
    return ScenarioPriority.P3


def readiness_for_impact(item: ImpactItem, *, has_route: bool, has_steps: bool = True) -> AutomationReadiness:
    if item.level == ImpactLevel.UNKNOWN:
        return AutomationReadiness.BLOCKED_BY_GAP
    if item.needs_runtime_verification or item.level == ImpactLevel.POSSIBLE:
        return AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED
    if not has_route or not has_steps:
        return AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED
    return AutomationReadiness.READY


def stronger_priority(left: ScenarioPriority, right: ScenarioPriority) -> ScenarioPriority:
    return left if _PRIORITY_ORDER[left] <= _PRIORITY_ORDER[right] else right


def stricter_readiness(left: AutomationReadiness, right: AutomationReadiness) -> AutomationReadiness:
    return left if _READINESS_ORDER[left] <= _READINESS_ORDER[right] else right


def priority_sort_key(priority: ScenarioPriority) -> int:
    return _PRIORITY_ORDER[priority]
