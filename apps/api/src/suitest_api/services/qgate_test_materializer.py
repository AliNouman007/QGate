"""Project executable QGate scenarios into existing Suitest test cases.

QGate ScenarioPlan JSON remains the canonical reasoning artifact. This service
creates or updates a user-visible Suitest case for each exactly identified,
executable scenario so the normal Tests UI can inspect the concrete steps.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field
from qgate_scenario_intelligence.models import (
    AutomationReadiness,
    Scenario,
    ScenarioPlan,
    StateSetupMechanism,
)
from suitest_db.models.case import TestCase
from suitest_db.repositories.projects import ProjectRepo
from suitest_db.repositories.suites import SuiteRepo
from suitest_db.repositories.test_cases import TestCaseRepo
from suitest_shared.domain.enums import (
    CaseSource,
    CaseStatus,
    Priority,
    TargetKind,
    TestingApproach,
    TestLevel,
)

from suitest_api.deps.scope import TenantContext
from suitest_api.schemas.test_case import StepCreate, TestCaseCreate, TestCaseUpdate
from suitest_api.services.test_case_service import TestCaseService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_QGATE_MANAGED = "qgate-managed"
_PLAYWRIGHT_MCP = "playwright-mcp"
_TAG_MAX = 64


class MaterializedCase(BaseModel):
    scenario_key: str
    status: Literal["created", "updated", "skipped"]
    case_id: str | None = None
    public_id: str | None = None
    reason: str | None = None


class MaterializeResult(BaseModel):
    suite_id: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    cases: list[MaterializedCase] = Field(default_factory=list)


class QGateTestMaterializer:
    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = TestCaseRepo(session)
        self._service = TestCaseService(
            ctx,
            self._repo,
            SuiteRepo(session),
            ProjectRepo(session),
        )

    async def materialize(self, plan: ScenarioPlan, *, suite_id: str) -> MaterializeResult:
        result = MaterializeResult(suite_id=suite_id)
        for scenario in plan.scenarios:
            steps = self._steps_for(scenario)
            if steps is None:
                result.skipped += 1
                result.cases.append(
                    MaterializedCase(
                        scenario_key=scenario.key,
                        status="skipped",
                        reason=(
                            "Scenario is unresolved or cannot be represented as a safe "
                            "executable Suitest case."
                        ),
                    )
                )
                continue

            tags = self._identity_tags(plan, scenario)
            existing = await self._find_exact_existing(suite_id, tags)
            if existing is None:
                created = await self._service.create(
                    TestCaseCreate(
                        suite_id=suite_id,
                        name=scenario.title[:255],
                        description=scenario.reason,
                        preconditions="\n".join(scenario.preconditions) or None,
                        priority=Priority(scenario.priority.value),
                        status=CaseStatus.ACTIVE,
                        source=CaseSource.AI,
                        testing_approach=TestingApproach.GRAY_BOX,
                        test_level=TestLevel.E2E,
                        framework="qgate",
                        steps=steps,
                        tags=tags,
                    )
                )
                if created is None:
                    raise ValueError("selected suite is not in the current workspace")
                result.created += 1
                result.cases.append(
                    MaterializedCase(
                        scenario_key=scenario.key,
                        status="created",
                        case_id=created.detail.id,
                        public_id=created.detail.public_id,
                    )
                )
                continue

            updated = await self._service.update(
                existing.id,
                TestCaseUpdate(
                    name=scenario.title[:255],
                    description=scenario.reason,
                    preconditions="\n".join(scenario.preconditions) or None,
                    priority=Priority(scenario.priority.value),
                    status=CaseStatus.ACTIVE,
                    testing_approach=TestingApproach.GRAY_BOX,
                    test_level=TestLevel.E2E,
                    framework="qgate",
                    tags=tags,
                ),
                if_unmodified_since=None,
            )
            if updated is None:
                raise ValueError("existing QGate-managed case is no longer in workspace scope")
            replaced = await self._service.replace_steps(
                existing.id, steps, if_unmodified_since=None
            )
            if replaced is None:
                raise ValueError("existing QGate-managed case disappeared during materialization")
            result.updated += 1
            result.cases.append(
                MaterializedCase(
                    scenario_key=scenario.key,
                    status="updated",
                    case_id=replaced.detail.id,
                    public_id=replaced.detail.public_id,
                )
            )
        return result

    async def _find_exact_existing(self, suite_id: str, tags: list[str]) -> TestCase | None:
        scenario_tag = next(tag for tag in tags if tag.startswith("qgate-scenario:"))
        rows, _ = await self._repo.list_by_suite_filtered(suite_id, tag=scenario_tag, limit=100)
        required = set(tags)
        for row in rows:
            existing_tags = set(await self._repo.get_tags(row.id))
            if required.issubset(existing_tags):
                return row
        return None

    @classmethod
    def _bounded_tag(cls, prefix: str, raw: str) -> str:
        candidate = f"{prefix}:{raw}"
        if len(candidate) <= _TAG_MAX:
            return candidate
        digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
        return f"{prefix}:sha256-{digest}"

    @classmethod
    def _identity_tags(cls, plan: ScenarioPlan, scenario: Scenario) -> list[str]:
        return [
            _QGATE_MANAGED,
            cls._bounded_tag("qgate-scenario", scenario.key),
            cls._bounded_tag("qgate-change", plan.metadata.impact_change_source_id),
            cls._bounded_tag("qgate-project", plan.metadata.project_fingerprint),
        ]

    @staticmethod
    def _steps_for(scenario: Scenario) -> list[StepCreate] | None:
        if scenario.readiness != AutomationReadiness.READY:
            return None
        if scenario.states and len(scenario.state_setup_hints) != 1:
            return None
        if len(scenario.state_setup_hints) > 1:
            return None

        steps: list[StepCreate] = []
        route = scenario.routes[0] if scenario.routes else None
        if route:
            steps.append(
                StepCreate(
                    action=f"Navigate to {route}",
                    expected="The route loads successfully.",
                    mcp_provider=_PLAYWRIGHT_MCP,
                    target_kind=TargetKind.FE_WEB,
                )
            )

        for hint in scenario.state_setup_hints:
            if hint.mechanism != StateSetupMechanism.UI_CONTROL:
                return None
            steps.append(
                StepCreate(
                    action=(
                        f'Click the accessible control named "{hint.target_label}" to activate '
                        f'state "{hint.state_label}".'
                    ),
                    expected=f'The "{hint.state_label}" state is selected successfully.',
                    mcp_provider=_PLAYWRIGHT_MCP,
                    target_kind=TargetKind.FE_WEB,
                )
            )
            steps.append(
                StepCreate(
                    action=(
                        f'Verify the control named "{hint.target_label}" remains visible after '
                        "activation."
                    ),
                    expected=(
                        f'The page remains in the "{hint.state_label}" state and the selected '
                        "control remains available."
                    ),
                    mcp_provider=_PLAYWRIGHT_MCP,
                    target_kind=TargetKind.FE_WEB,
                )
            )

        for source_step in scenario.steps:
            normalized = source_step.action.strip().lower()
            if route and (normalized.startswith("open ") or normalized.startswith("navigate ")):
                continue
            steps.append(
                StepCreate(
                    action=source_step.action,
                    expected=source_step.expected,
                    data={"dataHint": source_step.data_hint} if source_step.data_hint else None,
                    mcp_provider=_PLAYWRIGHT_MCP,
                    target_kind=TargetKind.FE_WEB,
                )
            )

        return steps or None
