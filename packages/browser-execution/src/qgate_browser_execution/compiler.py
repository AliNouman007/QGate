from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from qgate_scenario_intelligence.models import AutomationReadiness, StateSetupMechanism

from .models import (
    CompiledScenario,
    CompiledStep,
    ExecutionConfig,
    ExecutionRequest,
    ExecutionStatus,
    OperationKind,
    PreclassifiedScenario,
    TargetHint,
)

if TYPE_CHECKING:
    from qgate_scenario_intelligence.models import (
        Scenario,
        ScenarioPlan,
        ScenarioStep,
        StateSetupHint,
    )


class ScenarioCompiler:
    def compile_plan(
        self,
        plan: ScenarioPlan,
        config: ExecutionConfig,
        *,
        scenario_keys: set[str] | None = None,
        priorities: set[str] | None = None,
    ) -> ExecutionRequest:
        compiled: list[CompiledScenario] = []
        preclassified: list[PreclassifiedScenario] = []
        for scenario in plan.scenarios:
            if scenario_keys is not None and scenario.key not in scenario_keys:
                continue
            if priorities is not None and scenario.priority.value not in priorities:
                continue
            if scenario.readiness != AutomationReadiness.READY:
                preclassified.append(self._preclassify(scenario))
                continue
            result = self._compile_scenario(scenario)
            if isinstance(result, PreclassifiedScenario):
                preclassified.append(result)
            elif isinstance(result, list):
                compiled.extend(result)
            else:
                compiled.append(result)
        return ExecutionRequest(
            scenario_plan_key=self.plan_key(plan),
            project_source_id=plan.metadata.project_source_id,
            project_fingerprint=plan.metadata.project_fingerprint,
            impact_change_source_id=plan.metadata.impact_change_source_id,
            config=config,
            scenarios=compiled,
            preclassified=preclassified,
        )

    @staticmethod
    def plan_key(plan: ScenarioPlan) -> str:
        identity = (
            f"{plan.metadata.project_source_id}\0{plan.metadata.project_fingerprint}\0"
            f"{plan.metadata.impact_change_source_id}\0"
            + "\0".join(sorted(scenario.key for scenario in plan.scenarios))
        )
        return hashlib.sha256(identity.encode()).hexdigest()[:24]

    def _compile_scenario(
        self, scenario: Scenario
    ) -> CompiledScenario | list[CompiledScenario] | PreclassifiedScenario:
        if scenario.states and scenario.preconditions and not scenario.state_setup_hints:
            return PreclassifiedScenario(
                scenario_key=scenario.key,
                title=scenario.title,
                status=ExecutionStatus.UNVERIFIED,
                reason=(
                    "Scenario requires semantic state setup but no deterministic setup hint "
                    "is available."
                ),
            )
        if scenario.preconditions and not scenario.state_setup_hints:
            return PreclassifiedScenario(
                scenario_key=scenario.key,
                title=scenario.title,
                status=ExecutionStatus.UNVERIFIED,
                reason=(
                    "Scenario requires runtime preconditions that Browser Execution cannot establish "
                    "safely without an explicit setup profile or state setup hint."
                ),
            )

        if len(scenario.state_setup_hints) > 1:
            passes: list[CompiledScenario] = []
            for idx, hint in enumerate(scenario.state_setup_hints):
                pass_res = self._compile_single_state_scenario(scenario, hint=hint, pass_index=idx)
                if isinstance(pass_res, PreclassifiedScenario):
                    return pass_res
                passes.append(pass_res)
            return passes

        hint = scenario.state_setup_hints[0] if scenario.state_setup_hints else None
        return self._compile_single_state_scenario(scenario, hint=hint, pass_index=0)

    def _compile_single_state_scenario(
        self,
        scenario: Scenario,
        *,
        hint: StateSetupHint | None,
        pass_index: int,
    ) -> CompiledScenario | PreclassifiedScenario:
        route = scenario.routes[0] if scenario.routes else None
        steps: list[CompiledStep] = []
        if route:
            steps.append(
                CompiledStep(
                    index=0,
                    operation=OperationKind.NAVIGATE,
                    source_action=f"Navigate to {route}",
                    source_expected="The route loads successfully.",
                    route=route,
                    expected=route,
                )
            )

        if hint:
            setup_steps = self._compile_state_setup(hint, len(steps), route)
            if setup_steps is None:
                return PreclassifiedScenario(
                    scenario_key=scenario.key,
                    title=scenario.title,
                    status=ExecutionStatus.UNVERIFIED,
                    reason=f"Unsupported deterministic state setup mechanism: {hint.mechanism.value}",
                )
            steps.extend(setup_steps)

        for source_step in scenario.steps:
            parsed = self._compile_step(source_step, len(steps), route)
            if parsed is None:
                return PreclassifiedScenario(
                    scenario_key=scenario.key,
                    title=scenario.title,
                    status=ExecutionStatus.UNVERIFIED,
                    reason=f"Unsupported deterministic browser step: {source_step.action}",
                )
            if (
                parsed.operation == OperationKind.NAVIGATE
                and steps
                and steps[-1].operation == OperationKind.NAVIGATE
                and steps[-1].route == parsed.route
            ):
                continue
            if parsed.operation == OperationKind.NAVIGATE and any(
                item.state_setup for item in steps
            ):
                continue
            steps.append(parsed)

        if not steps:
            return PreclassifiedScenario(
                scenario_key=scenario.key,
                title=scenario.title,
                status=ExecutionStatus.UNVERIFIED,
                reason="READY scenario contains no safely compilable browser operation.",
            )
        if all(step.operation == OperationKind.NAVIGATE for step in steps):
            steps.append(
                CompiledStep(
                    index=len(steps),
                    operation=OperationKind.CAPTURE,
                    source_action="Capture deterministic browser evidence",
                    source_expected="Relevant page evidence is captured.",
                    route=route,
                )
            )
        pass_key = f"{scenario.key}:pass:{pass_index}" if hint else None
        state_key = hint.state_key if hint else None
        state_label = hint.state_label if hint else None
        title = f"{scenario.title} ({hint.state_label})" if hint and len(scenario.state_setup_hints) > 1 else scenario.title
        return CompiledScenario(
            scenario_key=scenario.key,
            pass_key=pass_key,
            state_key=state_key,
            state_label=state_label,
            title=title,
            kind=scenario.kind.value,
            priority=scenario.priority.value,
            route=route,
            steps=steps,
            preconditions=[hint.state_label] if hint else scenario.preconditions,
            source_impact_keys=scenario.source_impact_keys,
        )

    @staticmethod
    def _compile_state_setup(
        hint: StateSetupHint, index: int, route: str | None
    ) -> list[CompiledStep] | None:
        if hint.mechanism != StateSetupMechanism.UI_CONTROL:
            return None
        target = TargetHint(
            name=hint.target_label,
            text=hint.target_label,
            label=hint.target_label,
        )
        return [
            CompiledStep(
                index=index,
                operation=OperationKind.CLICK,
                source_action=f'Activate state "{hint.state_label}"',
                source_expected=(
                    f'State "{hint.state_label}" can be selected through the evidence-backed '
                    "UI control."
                ),
                route=route,
                target=target,
                state_setup=True,
            ),
            CompiledStep(
                index=index + 1,
                operation=OperationKind.ASSERT_VISIBLE,
                source_action=(
                    f'Verify state control "{hint.state_label}" remains available after activation'
                ),
                source_expected=(
                    f'State "{hint.state_label}" is established without losing the selected control.'
                ),
                route=route,
                target=target,
                state_setup=True,
            ),
        ]

    def _compile_step(
        self, step: ScenarioStep, index: int, default_route: str | None
    ) -> CompiledStep | None:
        action = " ".join(step.action.strip().split())
        lower = action.lower()
        route = step.route or default_route

        if lower.startswith("open ") or lower.startswith("navigate "):
            if route is None:
                return None
            return CompiledStep(
                index=index,
                operation=OperationKind.NAVIGATE,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
                expected=route,
            )
        if lower.startswith("capture"):
            return CompiledStep(
                index=index,
                operation=OperationKind.CAPTURE,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
            )

        text_match = re.fullmatch(r'assert text\s+"([^"]+)"', action, flags=re.IGNORECASE)
        if text_match:
            value = text_match.group(1)
            return CompiledStep(
                index=index,
                operation=OperationKind.ASSERT_TEXT,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
                target=TargetHint(selector="body"),
                expected=value,
            )
        visible_match = re.fullmatch(r'assert visible\s+"([^"]+)"', action, flags=re.IGNORECASE)
        if visible_match:
            label = visible_match.group(1)
            return CompiledStep(
                index=index,
                operation=OperationKind.ASSERT_VISIBLE,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
                target=TargetHint(text=label, name=label),
            )
        hidden_match = re.fullmatch(r'assert hidden\s+"([^"]+)"', action, flags=re.IGNORECASE)
        if hidden_match:
            label = hidden_match.group(1)
            return CompiledStep(
                index=index,
                operation=OperationKind.ASSERT_HIDDEN,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
                target=TargetHint(text=label, name=label),
            )
        click_match = re.fullmatch(r'click\s+"([^"]+)"', action, flags=re.IGNORECASE)
        if click_match:
            label = click_match.group(1)
            return CompiledStep(
                index=index,
                operation=OperationKind.CLICK,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
                target=TargetHint(name=label, text=label),
            )
        fill_match = re.fullmatch(
            r'fill\s+"([^"]+)"\s+with\s+"([^"]*)"', action, flags=re.IGNORECASE
        )
        if fill_match:
            return CompiledStep(
                index=index,
                operation=OperationKind.FILL,
                source_action=step.action,
                source_expected=step.expected,
                route=route,
                target=TargetHint(label=fill_match.group(1), name=fill_match.group(1)),
                value=fill_match.group(2),
            )
        return None

    @staticmethod
    def _preclassify(scenario: Scenario) -> PreclassifiedScenario:
        if scenario.readiness == AutomationReadiness.MANUAL_ONLY:
            status = ExecutionStatus.SKIPPED_MANUAL
        elif scenario.readiness == AutomationReadiness.BLOCKED_BY_GAP:
            status = ExecutionStatus.BLOCKED
        else:
            status = ExecutionStatus.UNVERIFIED
        return PreclassifiedScenario(
            scenario_key=scenario.key,
            title=scenario.title,
            status=status,
            reason=scenario.manual_reason or f"Scenario readiness is {scenario.readiness.value}.",
        )
