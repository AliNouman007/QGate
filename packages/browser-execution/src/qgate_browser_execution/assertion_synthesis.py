from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .models import OperationKind, TargetHint

if TYPE_CHECKING:
    from playwright.async_api import Page

STOP_WORDS: set[str] = {
    "app", "src", "js", "ts", "jsx", "tsx", "const", "let", "var", "function",
    "export", "default", "import", "from", "return", "use", "state", "context",
    "null", "true", "false", "0", "1", "2", "the", "and", "for", "with", "this",
    "that", "page", "route", "http", "https", "localhost", "com", "org", "net",
}

TIMESTAMP_REGEX = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b)",
    re.IGNORECASE,
)


def extract_relevance_tokens(
    state_key: str | None = None,
    state_label: str | None = None,
    route: str | None = None,
    evidence_excerpts: list[str] | None = None,
) -> set[str]:
    tokens: set[str] = set()
    raw_strings = [state_key, state_label, route]
    if evidence_excerpts:
        raw_strings.extend(evidence_excerpts)
    for raw in raw_strings:
        if not raw:
            continue
        words = re.findall(r"\b[A-Za-z0-9_$]+\b", raw)
        for w in words:
            w_lower = w.lower()
            if len(w_lower) >= 2 and w_lower not in STOP_WORDS:
                tokens.add(w_lower)
    return tokens


class BaselineAssertion(BaseModel):
    scenario_key: str
    route: str
    state_key: str | None = None
    pass_key: str | None = None
    target: TargetHint
    operation: OperationKind = OperationKind.ASSERT_TEXT
    expected_value: str
    baseline_source_id: str | None = None
    change_source_id: str | None = None
    reason: str
    confidence: str = "high"
    provenance: str = "baseline_observation"


class AssertionSynthesizer:
    def __init__(self, min_token_match: int = 1) -> None:
        self.min_token_match = min_token_match

    @staticmethod
    def is_stable_candidate(candidate: dict[str, Any]) -> bool:
        tag = candidate.get("tag", "").lower()
        if tag in {"select", "button", "input", "a", "option", "script", "style", "svg", "path", "g"}:
            return False

        text = candidate.get("text", "").strip()
        if not text:
            return False

        return not bool(TIMESTAMP_REGEX.search(text))

    def filter_and_rank_candidates(
        self,
        candidates: list[dict[str, Any]],
        relevance_tokens: set[str],
        route: str | None = None,
        state_key: str | None = None,
    ) -> list[dict[str, Any]]:
        valid = [c for c in candidates if self.is_stable_candidate(c)]
        if not valid:
            return []

        state_tokens = extract_relevance_tokens(state_key=state_key) if state_key else set()

        scored: list[tuple[int, dict[str, Any]]] = []
        for c in valid:
            c_tokens: set[str] = set()
            for key in ["testId", "id", "className", "role", "name", "text"]:
                val = c.get(key)
                if val and isinstance(val, str):
                    for w in re.findall(r"\b[A-Za-z0-9_$]+\b", val):
                        w_lower = w.lower()
                        if len(w_lower) >= 2 and w_lower not in STOP_WORDS:
                            c_tokens.add(w_lower)

            score = 0
            for tok in c_tokens:
                if state_tokens and tok in state_tokens:
                    score += 10
                elif tok in relevance_tokens:
                    score += 1

            test_id_val = (c.get("testId") or "").lower()
            if test_id_val:
                if state_tokens and any(t in test_id_val for t in state_tokens):
                    score += 20
                elif any(t in test_id_val for t in relevance_tokens):
                    score += 2

            OUTPUT_TOKENS = {"payable", "total", "sum", "amount", "result", "final", "price"}
            if test_id_val and any(ot in test_id_val for ot in OUTPUT_TOKENS):
                score += 25
            elif any(ot in c_tokens for ot in OUTPUT_TOKENS):
                score += 15

            if score >= self.min_token_match:
                scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return []

        top_score = scored[0][0]
        top_tier = [c for score, c in scored if score == top_score]
        leaf_top = [c for c in top_tier if not c.get("hasChildren")]
        if leaf_top:
            top_tier = leaf_top

        # If multiple top candidates in the highest score tier have conflicting text values, fail closed
        values = {c["text"].strip() for c in top_tier}
        if len(values) > 1:
            return []

        ordered = [c for score, c in scored if not c.get("hasChildren")]
        return ordered or [c for score, c in scored]

    async def observe_baseline_assertions(
        self,
        page: Page,
        *,
        scenario_key: str,
        route: str,
        state_key: str | None,
        pass_key: str | None,
        relevance_tokens: set[str],
        max_assertions: int = 3,
    ) -> list[BaselineAssertion]:
        try:
            js_eval = """
            () => {
                const candidates = [];
                const all = Array.from(document.querySelectorAll('*'));
                for (const el of all) {
                    const tag = el.tagName.toLowerCase();
                    if (['script', 'style', 'head', 'meta', 'html', 'body', 'select', 'button', 'input', 'a', 'option', 'svg', 'path', 'g', 'label', 'fieldset', 'form', 'nav', 'header', 'footer'].includes(tag)) continue;
                    if (el.querySelector('select, input, button, a, option, label')) continue;

                    const rect = el.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

                    const text = el.innerText ? el.innerText.trim() : '';
                    if (!text) continue;

                    const childTextNodes = Array.from(el.childNodes).filter(
                        n => n.nodeType === Node.ELEMENT_NODE && n.innerText && n.innerText.trim()
                    );
                    candidates.push({
                        tag,
                        id: el.id || null,
                        testId: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null,
                        role: el.getAttribute('role') || null,
                        name: el.getAttribute('aria-label') || el.getAttribute('name') || null,
                        text,
                        hasChildren: childTextNodes.length > 0
                    });
                }
                return candidates;
            }
            """
            raw_candidates_1: list[dict[str, Any]] = await page.evaluate(js_eval)
            await page.wait_for_timeout(100)
            raw_candidates_2: list[dict[str, Any]] = await page.evaluate(js_eval)

            c2_map = {f"{c.get('testId')}:{c.get('id')}:{c.get('text')}": c for c in raw_candidates_2}
            stable_candidates = [
                c1 for c1 in raw_candidates_1
                if f"{c1.get('testId')}:{c1.get('id')}:{c1.get('text')}" in c2_map
            ]

            ranked = self.filter_and_rank_candidates(
                stable_candidates,
                relevance_tokens=relevance_tokens,
                route=route,
                state_key=state_key,
            )

            if not ranked:
                return []

            results: list[BaselineAssertion] = []
            seen_texts: set[str] = set()

            for winner in ranked[:max_assertions]:
                exp_val = winner["text"].strip()
                if exp_val in seen_texts:
                    continue
                seen_texts.add(exp_val)

                target_hint = TargetHint(
                    test_id=winner.get("testId") or None,
                    role=winner.get("role") or None,
                    name=winner.get("name") or None,
                    text=winner.get("text") if not winner.get("testId") else None,
                    selector=f"#{winner.get('id')}" if winner.get("id") and not winner.get("testId") else None,
                )

                results.append(
                    BaselineAssertion(
                        scenario_key=scenario_key,
                        route=route,
                        state_key=state_key,
                        pass_key=pass_key,
                        target=target_hint,
                        operation=OperationKind.ASSERT_TEXT,
                        expected_value=exp_val,
                        reason=f"Matched relevant baseline DOM candidate with tag <{winner['tag']}> and testId={winner.get('testId')}",
                        confidence="high",
                        provenance="baseline_observation",
                    )
                )

            return results
        except Exception:
            return []

    async def observe_baseline_assertion(
        self,
        page: Page,
        *,
        scenario_key: str,
        route: str,
        state_key: str | None,
        pass_key: str | None,
        relevance_tokens: set[str],
    ) -> BaselineAssertion | None:
        assertions = await self.observe_baseline_assertions(
            page,
            scenario_key=scenario_key,
            route=route,
            state_key=state_key,
            pass_key=pass_key,
            relevance_tokens=relevance_tokens,
            max_assertions=1,
        )
        return assertions[0] if assertions else None
