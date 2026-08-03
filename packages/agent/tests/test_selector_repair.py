from __future__ import annotations

import json

import pytest
from suitest_agent.generators.selector_repair import (
    SelectorRepairError,
    apply_selector_repair,
    is_selector_changed_failure,
    propose_selector_repair,
)
from suitest_agent.providers.mock import MockProvider

_CODE = json.dumps(
    {
        "tool": "browser_click",
        "arguments": {"selector": "#submit"},
        "assertions": [
            {
                "tool": "browser.assert_text",
                "arguments": {"selector": "h1", "contains": "Done"},
            }
        ],
    }
)


def test_detects_selector_changed_only_for_selector_steps() -> None:
    assert is_selector_changed_failure(_CODE, "Timeout waiting for locator('#submit')")
    assert not is_selector_changed_failure(_CODE, "HTTP 500")
    assert not is_selector_changed_failure('{"tool":"api_get"}', "selector not found")


def test_applies_exactly_one_selector_field() -> None:
    updated = json.loads(apply_selector_repair(_CODE, "#submit", "[data-testid=save]"))
    assert updated["arguments"]["selector"] == "[data-testid=save]"
    assert updated["assertions"][0]["arguments"]["selector"] == "h1"
    with pytest.raises(SelectorRepairError, match="exactly one"):
        apply_selector_repair(_CODE, ".missing", "#new")


@pytest.mark.asyncio
async def test_ai_proposal_is_constrained_to_selector_patch() -> None:
    provider = MockProvider(
        scripted=[
            json.dumps(
                {
                    "old_selector": "#submit",
                    "new_selector": "[data-testid=save]",
                    "rationale": "DOM snapshot exposes a stable test id.",
                    "confidence": 0.93,
                }
            )
        ]
    )
    proposal, _ = await propose_selector_repair(
        provider,
        model="mock-1",
        system_prompt="repair",
        code=_CODE,
        error="Timeout waiting for locator('#submit')",
        action="Click save",
        expected="Saved",
        dom_snapshot='<button data-testid="save">Save</button>',
    )
    assert proposal.old_selector == "#submit"
    assert proposal.new_selector == "[data-testid=save]"
    assert json.loads(proposal.updated_code)["tool"] == "browser_click"
