from __future__ import annotations

import hashlib
import re

from qgate_impact_analysis.models import ChangeCategory, ImpactItem, ImpactLevel, ImpactReport
from qgate_project_intelligence.models import (
    Confidence,
    ProjectKnowledge,
    SemanticState,
    SemanticStateKind,
)

from .models import (
    AutomationReadiness,
    CrossStateGroup,
    GenerationBudget,
    Scenario,
    ScenarioCoverageGap,
    ScenarioKind,
    ScenarioPlan,
    ScenarioPlanMetadata,
    ScenarioPriority,
    ScenarioStep,
    ScenarioSummary,
    StateSetupHint,
    StateSetupMechanism,
)
from .prioritization import priority_for_impact, priority_sort_key, readiness_for_impact
from .signature import merge_scenarios, scenario_signature
from .state_expansion import related_state_pair, state_families


class ScenarioInputMismatchError(ValueError):
    pass


class ScenarioGenerator:
    def __init__(self, budget: GenerationBudget | None = None) -> None:
        self.budget = budget or GenerationBudget()

    def generate(self, knowledge: ProjectKnowledge, impact: ImpactReport) -> ScenarioPlan:
        self._validate_inputs(knowledge, impact)
        candidates: list[Scenario] = []
        gaps: list[ScenarioCoverageGap] = [
            ScenarioCoverageGap(reason=f"impact:{gap.reason}", detail=gap.detail)
            for gap in impact.coverage_gaps
        ]

        route_items = impact.affected_routes
        shared_by_route = self._shared_breadth_by_route(impact)
        for item in route_items:
            kind = ScenarioKind.SMOKE if item.level == ImpactLevel.DIRECT else ScenarioKind.ROUTE_REGRESSION
            candidates.append(self._route_scenario(item, kind, shared_by_route.get(item.target, 0)))

        state_lookup = {state.key: state for state in knowledge.semantic_states}
        state_by_label = {state.label: state for state in knowledge.semantic_states}
        default_routes = [item.target for item in route_items]
        for item in impact.affected_states:
            state = state_lookup.get(item.target) or state_by_label.get(item.target)
            route = self._best_route_for_state(state, route_items, impact, knowledge=knowledge)
            candidates.append(
                self._state_scenario(
                    item,
                    state,
                    route or (default_routes[0] if len(default_routes) == 1 else None),
                )
            )

        for item in [*impact.possible_impacts, *impact.unknown_impacts]:
            if item.target_type.value in {"route", "state"}:
                candidates.append(self._discovery_scenario(item))

        cross_groups: list[CrossStateGroup] = []
        if self._cross_state_relevant(impact):
            for family in state_families(
                knowledge, max_variants_per_surface=self.budget.max_state_variants_per_surface
            ):
                if len(cross_groups) >= self.budget.max_cross_state_groups:
                    gaps.append(
                        ScenarioCoverageGap(
                            reason="cross_state_budget_reached",
                            detail=f"Limited to {self.budget.max_cross_state_groups} cross-state groups.",
                        )
                    )
                    break
                pair = related_state_pair(family.states)
                if pair is None or not self._family_relevant(pair, impact):
                    continue
                route = self._route_for_family(pair, route_items, impact, knowledge=knowledge)
                if route is None:
                    continue
                scenario = self._cross_state_scenario(route, pair, impact)
                candidates.append(scenario)
                cross_groups.append(
                    CrossStateGroup(
                        key=scenario.cross_state_group or scenario.key,
                        route=route,
                        state_labels=[pair[0].label, pair[1].label],
                        scenario_keys=[scenario.key],
                        comparison_goal="Compare the same impacted surface across both evidence-backed states and verify expected structure/behavior remains consistent.",
                    )
                )

        deduped = self._dedupe(candidates)
        deduped.sort(key=lambda item: (priority_sort_key(item.priority), item.title.lower(), item.key))
        if len(deduped) > self.budget.max_scenarios:
            omitted = len(deduped) - self.budget.max_scenarios
            deduped = deduped[: self.budget.max_scenarios]
            gaps.append(
                ScenarioCoverageGap(
                    reason="scenario_budget_reached",
                    detail=f"Omitted {omitted} lower-priority candidate(s); max_scenarios={self.budget.max_scenarios}.",
                )
            )

        if not deduped:
            gaps.append(
                ScenarioCoverageGap(
                    reason="no_actionable_scenario",
                    detail="Impact exists but no evidence-backed executable surface could be derived statically.",
                )
            )

        keys = {scenario.key for scenario in deduped}
        cross_groups = [
            group.model_copy(update={"scenario_keys": [key for key in group.scenario_keys if key in keys]})
            for group in cross_groups
            if any(key in keys for key in group.scenario_keys)
        ]
        return ScenarioPlan(
            metadata=ScenarioPlanMetadata(
                project_source_id=knowledge.metadata.source_id,
                project_fingerprint=knowledge.metadata.source_fingerprint,
                impact_change_source_id=impact.metadata.change_source_id,
            ),
            budget=self.budget,
            summary=self._summary(deduped),
            scenarios=deduped,
            cross_state_groups=cross_groups,
            coverage_gaps=gaps,
        )

    @staticmethod
    def _validate_inputs(knowledge: ProjectKnowledge, impact: ImpactReport) -> None:
        if knowledge.metadata.source_id != impact.metadata.project_source_id:
            raise ScenarioInputMismatchError("Project source id does not match ImpactReport")
        if knowledge.metadata.source_fingerprint != impact.metadata.project_fingerprint:
            raise ScenarioInputMismatchError("Project fingerprint does not match ImpactReport")

    def _route_scenario(self, item: ImpactItem, kind: ScenarioKind, shared_breadth: int) -> Scenario:
        readiness = readiness_for_impact(item, has_route=bool(item.target))
        priority = priority_for_impact(item, shared_breadth=shared_breadth)
        return self._scenario(
            kind=kind,
            title=("Verify changed route" if kind == ScenarioKind.SMOKE else "Regression-check affected route") + f" {item.target}",
            priority=priority,
            confidence=item.confidence,
            routes=[item.target],
            targets=[item.target],
            states=[],
            state_setup_hints=[],
            preconditions=[],
            steps=[
                ScenarioStep(
                    action=f"Open the impacted route {item.target} in the intended test environment.",
                    expected="The affected surface loads and the impacted behavior remains available without a visible or functional regression.",
                    route=item.target,
                )
            ],
            reason=item.reason,
            source_impact_keys=[item.key],
            evidence=item.evidence,
            readiness=readiness,
            needs_runtime_discovery=readiness != AutomationReadiness.READY,
        )

    def _state_scenario(self, item: ImpactItem, state: SemanticState | None, route: str | None) -> Scenario:
        setup_hints = self._state_setup_hints(state)
        runtime = (
            item.needs_runtime_verification
            or state is None
            or route is None
            or not setup_hints
        )
        readiness = (
            AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED if runtime else AutomationReadiness.READY
        )
        label = state.label if state is not None else item.target
        kind = self._state_kind(state)
        evidence = state.evidence if state is not None else item.evidence
        preconditions = [f"Establish the evidence-backed state: {label}."]
        return self._scenario(
            kind=kind,
            title=f"Verify {label}" + (f" on {route}" if route else ""),
            priority=priority_for_impact(item),
            confidence=item.confidence,
            routes=[route] if route else [],
            targets=[item.target],
            states=[state.key if state is not None else item.target],
            state_setup_hints=setup_hints,
            preconditions=preconditions,
            steps=[
                ScenarioStep(
                    action=(f"Open {route} with the required state established." if route else "Discover a safe runtime path that reaches this impacted state."),
                    expected=f"The impacted behavior for state '{label}' matches the code-backed expectation without regression.",
                    route=route,
                    data_hint=state.explanation if state is not None else None,
                )
            ],
            reason=item.reason,
            source_impact_keys=[item.key],
            evidence=evidence,
            readiness=readiness,
            needs_runtime_discovery=runtime,
            manual_reason=(
                "Static evidence does not prove a deterministic way to establish/reach this state."
                if runtime
                else None
            ),
        )

    def _discovery_scenario(self, item: ImpactItem) -> Scenario:
        return self._scenario(
            kind=ScenarioKind.RUNTIME_DISCOVERY,
            title=f"Discover runtime coverage for {item.target}",
            priority=ScenarioPriority.P3,
            confidence=item.confidence,
            routes=[item.target] if item.target_type.value == "route" else [],
            targets=[item.target],
            states=[item.target] if item.target_type.value == "state" else [],
            state_setup_hints=[],
            preconditions=[],
            steps=[
                ScenarioStep(
                    action="Discover a reachable runtime setup for this possible/unknown impact.",
                    expected="A concrete route, state setup and assertion can be established before execution is allowed.",
                )
            ],
            reason=item.reason,
            source_impact_keys=[item.key],
            evidence=item.evidence,
            readiness=AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED,
            needs_runtime_discovery=True,
            manual_reason="Impact evidence is possible/unknown and cannot safely be promoted to READY statically.",
        )

    def _cross_state_scenario(
        self,
        route: str,
        pair: tuple[SemanticState, SemanticState],
        impact: ImpactReport,
    ) -> Scenario:
        left, right = pair
        key = self._stable_key("cross", route, left.key, right.key)
        impact_keys = sorted(
            {
                item.key
                for item in impact.affected_states
                if self._state_item_matches(item, left) or self._state_item_matches(item, right)
            }
        )
        evidence = self._dedupe_evidence([*left.evidence, *right.evidence])
        confidence = self._lower_confidence(left.confidence, right.confidence)
        setup_hints = [*self._state_setup_hints(left), *self._state_setup_hints(right)]
        ready = len(setup_hints) == 2
        return Scenario(
            key=key,
            title=f"Compare {left.label} vs {right.label} on {route}",
            kind=ScenarioKind.CROSS_STATE_COMPARISON,
            priority=ScenarioPriority.P1,
            confidence=confidence,
            routes=[route],
            targets=[route],
            states=[left.key, right.key],
            state_setup_hints=setup_hints,
            preconditions=[f"State A: {left.label}", f"State B: {right.label}"],
            steps=[
                ScenarioStep(
                    action=f"Exercise {route} once in '{left.label}' and once in '{right.label}'.",
                    expected="Compare the impacted content/visibility/layout relationship across both states; differences must match the evidence-backed state behavior without unintended drift.",
                    route=route,
                )
            ],
            reason="The same impacted UI/state-sensitive surface has two related evidence-backed states, so comparison can reveal regressions that independent smoke checks miss.",
            source_impact_keys=impact_keys,
            evidence=evidence,
            readiness=(AutomationReadiness.READY if ready else AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED),
            needs_runtime_discovery=not ready,
            manual_reason=(None if ready else "Static evidence does not prove deterministic setup controls for both compared states."),
            cross_state_group=f"cross:{route}:{left.kind.value}",
        )

    @staticmethod
    def _state_setup_hints(state: SemanticState | None) -> list[StateSetupHint]:
        if state is None or state.confidence == Confidence.LOW or not state.evidence:
            return []
        if state.needs_runtime_verification:
            return []
        if state.kind not in {
            SemanticStateKind.USER_STATE,
            SemanticStateKind.ACCESS_STATE,
            SemanticStateKind.FEATURE_STATE,
        }:
            return []
        label = state.label.strip()
        if not label:
            return []
        return [
            StateSetupHint(
                state_key=state.key,
                state_label=label,
                mechanism=StateSetupMechanism.UI_CONTROL,
                target_label=label,
                verification_text=label,
                confidence=state.confidence,
                evidence=state.evidence,
            )
        ]

    @staticmethod
    def _state_kind(state: SemanticState | None) -> ScenarioKind:
        if state is None:
            return ScenarioKind.RUNTIME_DISCOVERY
        text = f"{state.key} {state.label} {state.explanation}".lower()
        if any(token in text for token in ("denied", "error", "empty", "missing", "absent", "unauth", "disabled")):
            return ScenarioKind.NEGATIVE_STATE
        return ScenarioKind.STATE_VARIANT

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "of", "to", "in", "for", "on", "with", "at", "by", "from", "up", "about",
            "into", "over", "after", "state", "user", "page", "app", "js", "ts", "jsx",
            "tsx", "component", "components", "context", "provider", "src", "route",
            "const", "let", "var", "function", "export", "default", "import", "return",
            "null", "true", "false", "style", "styles", "module", "css", "next", "react", "link",
        }
        raw_tokens = re.findall(r"\b[A-Za-z_$][\w.$-]*\b", text)
        tokens: set[str] = set()
        for tok in raw_tokens:
            clean = tok.lower().strip(".-_")
            if len(clean) >= 3 and clean not in stop_words:
                tokens.add(clean)
        return tokens

    @staticmethod
    def _best_route_for_state(
        state: SemanticState | None,
        routes: list[ImpactItem],
        impact: ImpactReport,
        knowledge: ProjectKnowledge | None = None,
    ) -> str | None:
        if not routes:
            return None
        if state is None:
            return routes[0].target if len(routes) == 1 else None

        state_key_label_tokens: set[str] = set()
        if state.key:
            state_key_label_tokens.update(ScenarioGenerator._tokenize(state.key))
        if state.label:
            state_key_label_tokens.update(ScenarioGenerator._tokenize(state.label))

        state_tokens: set[str] = set()
        state_tokens.update(state_key_label_tokens)
        if state.explanation:
            state_tokens.update(ScenarioGenerator._tokenize(state.explanation))
        for ev in state.evidence:
            if hasattr(ev, "excerpt") and ev.excerpt:
                state_tokens.update(ScenarioGenerator._tokenize(ev.excerpt))

        state_evidence_paths = {item.path for item in state.evidence}

        file_lookup = {}
        if knowledge and hasattr(knowledge, "files"):
            for f in knowledge.files:
                file_lookup[f.record.path] = f

        scored_routes: list[tuple[int, int, int, str]] = []
        for idx, route in enumerate(routes):
            route_paths = {item.path for item in route.evidence}
            route_paths.update(step.source for step in route.dependency_path)
            route_paths.update(step.target for step in route.dependency_path)

            dep_match = 1 if (state_evidence_paths & route_paths) else 0

            route_tokens: set[str] = set()
            for ev in route.evidence:
                if hasattr(ev, "excerpt") and ev.excerpt:
                    route_tokens.update(ScenarioGenerator._tokenize(ev.excerpt))
                if hasattr(ev, "path") and ev.path:
                    route_tokens.update(ScenarioGenerator._tokenize(ev.path))
            if route.target:
                route_tokens.update(ScenarioGenerator._tokenize(route.target))

            for r_ev in route.evidence:
                f_analysis = file_lookup.get(r_ev.path)
                if f_analysis:
                    for imp in f_analysis.imports:
                        route_tokens.update(ScenarioGenerator._tokenize(imp.module))
                    for beh in f_analysis.behaviors:
                        route_tokens.update(ScenarioGenerator._tokenize(beh.expression))

            key_label_hits = len(state_key_label_tokens & route_tokens)
            direct_hits = (10 * key_label_hits) + len(state_tokens & route_tokens)
            scored_routes.append((direct_hits, dep_match, -idx, route.target))

        scored_routes.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        best = scored_routes[0]
        if best[0] > 0 or best[1] > 0:
            return best[3]

        for group in impact.shared_groups:
            if state_evidence_paths & set(group.affected_files) and group.affected_routes:
                return group.affected_routes[0]
        return routes[0].target

    def _route_for_family(
        self,
        pair: tuple[SemanticState, SemanticState],
        routes: list[ImpactItem],
        impact: ImpactReport,
        knowledge: ProjectKnowledge | None = None,
    ) -> str | None:
        best_route: str | None = None
        max_hits = -1
        for state in pair:
            state_tokens: set[str] = set()
            if state.key:
                state_tokens.update(ScenarioGenerator._tokenize(state.key))
            if state.label:
                state_tokens.update(ScenarioGenerator._tokenize(state.label))
            if state.explanation:
                state_tokens.update(ScenarioGenerator._tokenize(state.explanation))
            for ev in state.evidence:
                if hasattr(ev, "excerpt") and ev.excerpt:
                    state_tokens.update(ScenarioGenerator._tokenize(ev.excerpt))

            for route in routes:
                route_tokens: set[str] = set()
                for ev in route.evidence:
                    if hasattr(ev, "excerpt") and ev.excerpt:
                        route_tokens.update(ScenarioGenerator._tokenize(ev.excerpt))
                    if hasattr(ev, "path") and ev.path:
                        route_tokens.update(ScenarioGenerator._tokenize(ev.path))
                if route.target:
                    route_tokens.update(ScenarioGenerator._tokenize(route.target))

                if knowledge and hasattr(knowledge, "files"):
                    for r_path in {item.path for item in route.evidence}:
                        for f in knowledge.files:
                            if f.record.path == r_path:
                                for imp in f.imports:
                                    route_tokens.update(ScenarioGenerator._tokenize(imp.module))
                                for beh in f.behaviors:
                                    route_tokens.update(ScenarioGenerator._tokenize(beh.expression))

                hits = len(state_tokens & route_tokens)
                if hits > max_hits and hits > 0:
                    max_hits = hits
                    best_route = route.target

        if best_route is not None:
            return best_route

        for state in pair:
            target_route = self._best_route_for_state(state, routes, impact, knowledge=knowledge)
            if target_route is not None:
                return target_route
        return None

    @staticmethod
    def _family_relevant(pair: tuple[SemanticState, SemanticState], impact: ImpactReport) -> bool:
        state_evidence_paths = {item.path for state in pair for item in state.evidence}
        impacted_paths = {
            item.path
            for impact_item in [*impact.direct_impacts, *impact.indirect_impacts, *impact.affected_states]
            for item in impact_item.evidence
        }
        return bool(state_evidence_paths & impacted_paths)

    @staticmethod
    def _cross_state_relevant(impact: ImpactReport) -> bool:
        interesting = {
            ChangeCategory.UI,
            ChangeCategory.STYLING,
            ChangeCategory.STATE,
            ChangeCategory.RESPONSIVE,
            ChangeCategory.SHARED,
        }
        return any(
            interesting & set(item.categories)
            for item in [*impact.direct_impacts, *impact.indirect_impacts]
        )

    @staticmethod
    def _state_item_matches(item: ImpactItem, state: SemanticState) -> bool:
        return item.target in {state.key, state.label}

    @staticmethod
    def _shared_breadth_by_route(impact: ImpactReport) -> dict[str, int]:
        result: dict[str, int] = {}
        for group in impact.shared_groups:
            for route in group.affected_routes:
                result[route] = max(result.get(route, 0), group.reuse_count)
        return result

    def _scenario(self, **kwargs: object) -> Scenario:
        scenario = Scenario(key="pending", **kwargs)
        return scenario.model_copy(update={"key": self._stable_key(scenario_signature(scenario))})

    @staticmethod
    def _stable_key(*parts: str) -> str:
        return "scn_" + hashlib.sha256("\0".join(parts).encode()).hexdigest()[:18]

    @staticmethod
    def _dedupe(candidates: list[Scenario]) -> list[Scenario]:
        merged: dict[str, Scenario] = {}
        for candidate in candidates:
            signature = scenario_signature(candidate)
            existing = merged.get(signature)
            merged[signature] = candidate if existing is None else merge_scenarios(existing, candidate)
        return list(merged.values())

    @staticmethod
    def _summary(scenarios: list[Scenario]) -> ScenarioSummary:
        return ScenarioSummary(
            total=len(scenarios),
            ready=sum(item.readiness == AutomationReadiness.READY for item in scenarios),
            runtime_discovery=sum(
                item.readiness == AutomationReadiness.RUNTIME_DISCOVERY_REQUIRED
                for item in scenarios
            ),
            manual_only=sum(item.readiness == AutomationReadiness.MANUAL_ONLY for item in scenarios),
            blocked=sum(item.readiness == AutomationReadiness.BLOCKED_BY_GAP for item in scenarios),
            p0=sum(item.priority == ScenarioPriority.P0 for item in scenarios),
            p1=sum(item.priority == ScenarioPriority.P1 for item in scenarios),
            p2=sum(item.priority == ScenarioPriority.P2 for item in scenarios),
            p3=sum(item.priority == ScenarioPriority.P3 for item in scenarios),
        )

    @staticmethod
    def _dedupe_evidence(items: list[object]) -> list[object]:
        seen: set[tuple[object, ...]] = set()
        result: list[object] = []
        for item in items:
            key = (
                getattr(item, "path", None),
                getattr(item, "line", None),
                getattr(item, "kind", None),
                getattr(item, "excerpt", None),
            )
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def _lower_confidence(left: Confidence, right: Confidence) -> Confidence:
        rank = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
        return left if rank[left] <= rank[right] else right
