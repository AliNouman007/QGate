"""Deterministic QA strategy baseline shared by every lifecycle approach."""

from __future__ import annotations

from typing import TYPE_CHECKING

from suitest_lifecycle.models import TestingApproach

if TYPE_CHECKING:
    from suitest_lifecycle.config import Config
    from suitest_lifecycle.models import CodeSummary, PlanCase


def resolve_approach(config: Config) -> TestingApproach:
    explicit = {
        "black-box": TestingApproach.BLACK_BOX,
        "gray-box": TestingApproach.GRAY_BOX,
        "white-box": TestingApproach.WHITE_BOX,
    }.get(config.testing.approach)
    if explicit is not None:
        return explicit
    return (
        TestingApproach.GRAY_BOX if config.analysis_source == "repo" else TestingApproach.BLACK_BOX
    )


def build_strategy(
    config: Config, summary: CodeSummary, cases: list[PlanCase]
) -> dict[str, object]:
    approach = resolve_approach(config)
    source_count = len(summary.endpoints) if summary.endpoints else len(summary.pages)
    risks = [
        {
            "id": "RISK-AUTH",
            "title": "Authorization and identity boundaries",
            "impact": "HIGH",
            "failureModes": [
                "Unauthenticated access succeeds",
                "Role or tenant boundary leaks data",
                "Session lifecycle becomes inconsistent",
            ],
            "recommendedApproach": (
                TestingApproach.BLACK_BOX.value
                if approach is TestingApproach.BLACK_BOX
                else TestingApproach.GRAY_BOX.value
            ),
        },
        {
            "id": "RISK-DATA",
            "title": "State and data integrity",
            "impact": "HIGH",
            "failureModes": [
                "Validation accepts invalid boundaries",
                "Partial writes survive failure",
                "Retry or concurrency duplicates state",
            ],
            "recommendedApproach": approach.value,
        },
        {
            "id": "RISK-RECOVERY",
            "title": "Error and recovery paths",
            "impact": "HIGH",
            "failureModes": [
                "Dependency failure has no safe fallback",
                "Cleanup is skipped after interruption",
                "Unhandled branches remain invisible",
            ],
            "recommendedApproach": approach.value,
        },
    ]
    return {
        "schemaVersion": "1",
        "status": "DRAFT",
        "summary": (
            f"{config.project_name}: {source_count} discovered target(s), "
            f"{len(cases)} planned case(s)."
        ),
        "recommendedApproach": approach.value,
        "approachReason": (
            "Repository context informs public behavior tests."
            if approach is TestingApproach.GRAY_BOX
            else (
                "Internal targets and coverage are explicitly requested."
                if approach is TestingApproach.WHITE_BOX
                else "Only public behavior or contracts are used."
            )
        ),
        "risks": risks,
        "assumptions": [
            "Test credentials and isolated mutable data are available.",
            "Public contracts and expected outcomes are current.",
            "Destructive scenarios require explicit approval and cleanup.",
        ],
        "oracles": [
            "Published UI or API behavior",
            "Persisted state and invariant checks",
            "Logs and evidence artifacts",
            "Repository coverage threshold for white-box runs",
        ],
        "coverageDimensions": [
            "positive",
            "negative",
            "boundary",
            "permissions",
            "state-transition",
            "concurrency",
            "dependency-failure",
            "recovery",
            "accessibility",
        ],
        "qaChecks": [
            "Question unstated assumptions.",
            "Prioritize impact and likelihood over case count.",
            "Require an observable oracle for every case.",
            "Reject duplicate or brittle assertions.",
            "Record exclusions and remaining risk.",
        ],
        "exclusions": (
            []
            if approach is TestingApproach.WHITE_BOX
            else ["Internal branch coverage is outside this lifecycle approach."]
        ),
    }


def apply_strategy(
    config: Config, summary: CodeSummary, cases: list[PlanCase]
) -> dict[str, object]:
    strategy = build_strategy(config, summary, cases)
    approach = resolve_approach(config)
    default_framework = config.testing.framework or (
        "playwright" if config.mode.value == "frontend" else "requests"
    )
    strategy_ref = f"suitest_{config.mode.value}_test_strategy.json"
    for case in cases:
        case.testing_approach = approach
        case.test_level = config.testing.level
        case.framework = default_framework
        case.strategy_ref = strategy_ref
    return strategy


__all__ = ["apply_strategy", "build_strategy", "resolve_approach"]
