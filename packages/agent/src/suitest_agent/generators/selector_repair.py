"""Validated selector-repair proposals for self-healing web steps."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, Field

from suitest_agent.graphs._util import parse_json_object
from suitest_agent.providers.base import ChatMessage, ModelCall

if TYPE_CHECKING:
    from suitest_agent.providers.base import CompletionResult, LLMProvider

_SELECTOR_FAILURE: Final = re.compile(
    r"(selector|locator|element (?:was )?not found|strict mode violation|"
    r"not attached|detached from the dom|waiting for (?:locator|selector))",
    re.IGNORECASE,
)


class SelectorRepairError(ValueError):
    """A failure cannot safely produce or apply a selector repair."""


class SelectorRepairProposal(BaseModel):
    """An AI suggestion constrained to one selector value in a step envelope."""

    old_selector: str
    new_selector: str
    updated_code: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    code_sha256: str


def selector_code_sha256(code: str) -> str:
    """Return the optimistic-lock fingerprint carried by a proposal."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _selector_values(value: object) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, nested in value.items():
            if key == "selector" and isinstance(nested, str):
                found.append(nested)
            else:
                found.extend(_selector_values(nested))
        return found
    if isinstance(value, list):
        found = []
        for nested in value:
            found.extend(_selector_values(nested))
        return found
    return []


def selectors_in_step_code(code: str) -> list[str]:
    """Extract selector fields from a deterministic step JSON envelope."""
    try:
        parsed: object = json.loads(code)
    except json.JSONDecodeError:
        return []
    return _selector_values(parsed)


def is_selector_changed_failure(code: str | None, error: str | None) -> bool:
    """Detect selector drift only when the failing step actually owns a selector."""
    return bool(code and error and selectors_in_step_code(code) and _SELECTOR_FAILURE.search(error))


def apply_selector_repair(code: str, old_selector: str, new_selector: str) -> str:
    """Replace exactly one matching selector field and return canonical JSON."""
    if not old_selector or not new_selector or old_selector == new_selector:
        raise SelectorRepairError("selector repair must replace a non-empty selector")
    if len(new_selector) > 500:
        raise SelectorRepairError("replacement selector exceeds 500 characters")
    try:
        parsed: object = json.loads(code)
    except json.JSONDecodeError as exc:
        raise SelectorRepairError("step code is not valid JSON") from exc

    replaced = 0

    def _replace(value: object) -> None:
        nonlocal replaced
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "selector" and nested == old_selector:
                    value[key] = new_selector
                    replaced += 1
                else:
                    _replace(nested)
        elif isinstance(value, list):
            for nested in value:
                _replace(nested)

    _replace(parsed)
    if replaced != 1:
        raise SelectorRepairError(f"expected exactly one matching selector field, found {replaced}")
    return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)


async def propose_selector_repair(
    provider: LLMProvider,
    *,
    model: str,
    system_prompt: str,
    code: str,
    error: str,
    action: str,
    expected: str,
    dom_snapshot: str | None = None,
) -> tuple[SelectorRepairProposal, CompletionResult]:
    """Ask an LLM for a selector pair, then validate and build the code patch."""
    if not is_selector_changed_failure(code, error):
        raise SelectorRepairError("failure does not contain selector-change evidence")
    payload = {
        "action": action,
        "expected": expected,
        "step_code": code,
        "failure": error,
        "dom_snapshot": (dom_snapshot or "")[:20_000],
        "allowed_old_selectors": selectors_in_step_code(code),
    }
    result = await provider.complete(
        ModelCall(
            model=model,
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(
                    role="user",
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            ],
            temperature=0.0,
            max_tokens=1024,
            cache_control=False,
        )
    )
    parsed = parse_json_object(result.content)
    old_selector = str(parsed.get("old_selector") or "").strip()
    new_selector = str(parsed.get("new_selector") or "").strip()
    rationale = str(parsed.get("rationale") or "Selector changed after DOM drift.").strip()
    raw_confidence = parsed.get("confidence", 0.0)
    if not isinstance(raw_confidence, int | float):
        raise SelectorRepairError("repair confidence must be numeric")
    updated_code = apply_selector_repair(code, old_selector, new_selector)
    return (
        SelectorRepairProposal(
            old_selector=old_selector,
            new_selector=new_selector,
            updated_code=updated_code,
            rationale=rationale[:1000],
            confidence=float(raw_confidence),
            code_sha256=selector_code_sha256(code),
        ),
        result,
    )


__all__ = [
    "SelectorRepairError",
    "SelectorRepairProposal",
    "apply_selector_repair",
    "is_selector_changed_failure",
    "propose_selector_repair",
    "selector_code_sha256",
    "selectors_in_step_code",
]
