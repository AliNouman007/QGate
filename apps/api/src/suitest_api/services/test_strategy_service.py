"""Risk-based strategy generation, enrichment, editing, and approval."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from suitest_agent.graphs._util import parse_json_object
from suitest_agent.providers.base import ChatMessage, ModelCall, ProviderError
from suitest_agent.providers.litellm_router import get_provider
from suitest_db.audit import write_audit
from suitest_db.models.project import Project
from suitest_db.models.test_strategy import TestStrategy
from suitest_db.repositories.agent_sessions import AgentSessionCreate, AgentSessionRepo
from suitest_db.repositories.llm_configs import LLMConfigRepo
from suitest_db.repositories.projects import ProjectRepo
from suitest_db.repositories.suites import SuiteRepo
from suitest_db.repositories.test_cases import TestCaseRepo
from suitest_db.repositories.test_strategies import TestStrategyRepository
from suitest_shared.domain.enums import (
    AgentSessionKind,
    TestingApproach,
    TestLevel,
    TestStrategyStatus,
)

from suitest_api.deps.scope import TenantContext
from suitest_api.schemas.test_strategy import (
    StrategyRisk,
    TestStrategyDocument,
    TestStrategyDraftRequest,
    TestStrategyPublic,
)
from suitest_api.services.prompt_resolver import resolve_and_pin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestStrategyNotFoundError(LookupError):
    pass


class TestStrategyStateError(ValueError):
    pass


class TestStrategyLlmError(RuntimeError):
    pass


class TestStrategyService:
    def __init__(self, session: AsyncSession, ctx: TenantContext) -> None:
        self._session = session
        self._ctx = ctx
        self._repo = TestStrategyRepository(session)

    async def _public(self, row: TestStrategy) -> TestStrategyPublic:
        await self._session.refresh(row)
        return TestStrategyPublic.model_validate(row)

    @staticmethod
    def _user_uuid(user_id: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(user_id)
        except ValueError:
            return None

    async def _project(self, project_id: str) -> Project:
        project = await ProjectRepo(self._session).get_active_by_id(project_id)
        if project is None or project.workspace_id != self._ctx.workspace_id:
            raise TestStrategyNotFoundError("project not found")
        return project

    async def list(self, project_id: str) -> list[TestStrategyPublic]:
        await self._project(project_id)
        return [
            TestStrategyPublic.model_validate(row)
            for row in await self._repo.list_for_project(project_id)
        ]

    @staticmethod
    def _approach(body: TestStrategyDraftRequest) -> tuple[TestingApproach, str]:
        if body.has_internal_test_provider:
            return (
                TestingApproach.WHITE_BOX,
                "Internal test targets and a coverage-capable provider are available.",
            )
        if body.has_repository or body.has_internal_observability:
            return (
                TestingApproach.GRAY_BOX,
                "Public behavior can be tested with privileged implementation context.",
            )
        return (
            TestingApproach.BLACK_BOX,
            "Only public behavior and contracts are available.",
        )

    @staticmethod
    def _risk_approach(preferred: TestingApproach, fallback: TestingApproach) -> TestingApproach:
        order = {
            TestingApproach.BLACK_BOX: 0,
            TestingApproach.GRAY_BOX: 1,
            TestingApproach.WHITE_BOX: 2,
        }
        return preferred if order[preferred] <= order[fallback] else fallback

    async def create_draft(
        self, project_id: str, body: TestStrategyDraftRequest
    ) -> TestStrategyPublic:
        project = await self._project(project_id)
        suites = list(await SuiteRepo(self._session).list_by_project(project_id))
        cases = list(await TestCaseRepo(self._session).list_by_project(project_id))
        approach, reason = self._approach(body)
        signals = [
            label
            for present, label in (
                (body.has_repository, "repository"),
                (body.has_internal_observability, "internal-observability"),
                (body.has_internal_test_provider, "internal-test-provider"),
            )
            if present
        ] or ["public-interface"]
        black_or_available = self._risk_approach(TestingApproach.BLACK_BOX, approach)
        gray_or_available = self._risk_approach(TestingApproach.GRAY_BOX, approach)
        white_or_available = self._risk_approach(TestingApproach.WHITE_BOX, approach)
        risks = [
            StrategyRisk(
                id="RISK-AUTH",
                title="Authorization and identity boundaries",
                impact="HIGH",
                likelihood="MEDIUM",
                failure_modes=[
                    "Unauthenticated access succeeds",
                    "Role or tenant boundary leaks data",
                    "Session lifecycle behaves inconsistently",
                ],
                recommended_approach=black_or_available,
                test_levels=[TestLevel.INTEGRATION, TestLevel.E2E],
            ),
            StrategyRisk(
                id="RISK-DATA",
                title="State and data integrity",
                impact="HIGH",
                likelihood="MEDIUM",
                failure_modes=[
                    "Partial writes survive a failed operation",
                    "Validation accepts invalid boundary values",
                    "Retry or concurrency duplicates state",
                ],
                recommended_approach=gray_or_available,
                test_levels=[TestLevel.INTEGRATION, TestLevel.SYSTEM],
            ),
            StrategyRisk(
                id="RISK-ERROR-PATH",
                title="Internal error and recovery paths",
                impact="HIGH",
                likelihood="MEDIUM",
                failure_modes=[
                    "Branches and exceptions remain untested",
                    "Dependency failure has no safe fallback",
                    "Cleanup is skipped after interruption",
                ],
                recommended_approach=white_or_available,
                test_levels=[TestLevel.UNIT, TestLevel.COMPONENT, TestLevel.INTEGRATION],
            ),
            StrategyRisk(
                id="RISK-USER",
                title="Critical user journey regression",
                impact="HIGH",
                likelihood="MEDIUM",
                failure_modes=[
                    "Primary workflow cannot complete",
                    "Error feedback is missing or misleading",
                    "Accessible interaction path regresses",
                ],
                recommended_approach=black_or_available,
                test_levels=[TestLevel.E2E],
            ),
        ]
        document = TestStrategyDocument(
            summary=(
                f"Risk-based strategy for {project.name}: {len(suites)} suite(s), "
                f"{len(cases)} existing case(s)."
            ),
            recommended_approach=approach,
            approach_reason=reason,
            access_signals=signals,
            risks=risks,
            assumptions=[
                "Test credentials and isolated mutable data are available.",
                "Public contracts and expected business outcomes are current.",
                "Destructive scenarios require explicit approval and cleanup.",
                *(["Additional context: " + body.context] if body.context else []),
            ],
            oracles=[
                "Published API or UI contract",
                "Persisted state and invariant checks",
                "Audit, log, and artifact evidence",
                "Configured source coverage threshold for white-box runs",
            ],
            coverage_dimensions=[
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
            qa_checks=[
                "Question unstated assumptions before generation.",
                "Prefer high-impact and likely failures over case-count volume.",
                "Define an observable oracle for every case.",
                "Reject duplicate, brittle, or implementation-free assertions.",
                "Record exclusions and remaining risks explicitly.",
            ],
            exclusions=(
                []
                if body.has_internal_test_provider
                else ["White-box execution requires a suitest.whitebox.v1 provider."]
            ),
        )
        row = TestStrategy(
            workspace_id=self._ctx.workspace_id,
            project_id=project_id,
            version=await self._repo.next_version(project_id),
            status=TestStrategyStatus.DRAFT,
            document=document.model_dump(mode="json"),
            created_by=self._user_uuid(self._ctx.user_id),
        )
        self._session.add(row)
        await self._session.flush()
        await write_audit(
            self._session,
            workspace_id=self._ctx.workspace_id,
            user_id=self._ctx.user_id,
            action="test_strategy.created",
            resource_type="test_strategy",
            resource_id=row.id,
            metadata={"projectId": project_id, "version": row.version},
        )
        return await self._public(row)

    async def _draft(self, strategy_id: str) -> TestStrategy:
        row = await self._repo.get(strategy_id)
        if row is None or row.workspace_id != self._ctx.workspace_id:
            raise TestStrategyNotFoundError("test strategy not found")
        if row.status is not TestStrategyStatus.DRAFT:
            raise TestStrategyStateError("only a draft strategy can be changed")
        return row

    async def update(self, strategy_id: str, document: TestStrategyDocument) -> TestStrategyPublic:
        row = await self._draft(strategy_id)
        row.document = document.model_dump(mode="json")
        await self._session.flush()
        await write_audit(
            self._session,
            workspace_id=self._ctx.workspace_id,
            user_id=self._ctx.user_id,
            action="test_strategy.updated",
            resource_type="test_strategy",
            resource_id=row.id,
            metadata={"version": row.version},
        )
        return await self._public(row)

    async def enrich(self, strategy_id: str) -> TestStrategyPublic:
        row = await self._draft(strategy_id)
        config = await LLMConfigRepo(self._session).get_active(self._ctx.workspace_id)
        if config is None:
            raise TestStrategyLlmError("no active LLM configured for this workspace")
        prompt, prompt_row = await resolve_and_pin(
            self._session,
            workspace_id=self._ctx.workspace_id,
            prompt_name="test-strategy",
        )
        sessions = AgentSessionRepo(self._session)
        agent_session = await sessions.create(
            AgentSessionCreate(
                workspace_id=self._ctx.workspace_id,
                kind=AgentSessionKind.STRATEGY,
                model_id=config.model,
                provider=config.provider,
                user_id=self._user_uuid(self._ctx.user_id),
                prompt_version_id=prompt_row.id,
                temperature=0.2,
                metadata_json={"strategyId": row.id},
            )
        )
        base_url_raw = config.config_json.get("base_url")
        base_url = base_url_raw if isinstance(base_url_raw, str) else None
        provider = get_provider(
            config.provider,
            api_key=config.api_key_encrypted,
            base_url=base_url,
        )
        try:
            result = await provider.complete(
                ModelCall(
                    model=config.model,
                    messages=[
                        ChatMessage(role="system", content=prompt),
                        ChatMessage(
                            role="user",
                            content=json.dumps(row.document, separators=(",", ":")),
                        ),
                    ],
                    temperature=0.2,
                )
            )
            parsed = parse_json_object(result.content)
            parsed["enrichment"] = "LLM"
            enriched = TestStrategyDocument.model_validate(parsed)
        except (ProviderError, ValueError) as exc:
            await sessions.complete(agent_session.id, status="failed")
            raise TestStrategyLlmError(str(exc)) from exc
        await sessions.complete(
            agent_session.id,
            cost_usd=Decimal(str(result.cost_usd)),
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )
        row.document = enriched.model_dump(mode="json")
        row.agent_session_id = agent_session.id
        await self._session.flush()
        await write_audit(
            self._session,
            workspace_id=self._ctx.workspace_id,
            user_id=self._ctx.user_id,
            action="test_strategy.enriched",
            resource_type="test_strategy",
            resource_id=row.id,
            metadata={"agentSessionId": agent_session.id},
        )
        return await self._public(row)

    async def approve(self, strategy_id: str) -> TestStrategyPublic:
        row = await self._draft(strategy_id)
        await self._repo.lock_project(row.project_id)
        existing = await self._repo.approved_for_project(row.project_id)
        if existing is not None:
            existing.status = TestStrategyStatus.SUPERSEDED
            await self._session.flush()
        row.status = TestStrategyStatus.APPROVED
        row.approved_by = self._user_uuid(self._ctx.user_id)
        row.approved_at = datetime.now(tz=UTC)
        await self._session.flush()
        await write_audit(
            self._session,
            workspace_id=self._ctx.workspace_id,
            user_id=self._ctx.user_id,
            action="test_strategy.approved",
            resource_type="test_strategy",
            resource_id=row.id,
            metadata={"projectId": row.project_id, "version": row.version},
        )
        return await self._public(row)
