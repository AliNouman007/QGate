from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import FailureCategory, TargetHint

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page


@dataclass(frozen=True)
class ResolutionResult:
    resolved: bool
    locator: Locator | None = None
    description: str | None = None
    failure_category: FailureCategory | None = None
    detail: str | None = None


async def resolve_target(page: Page, hint: TargetHint, *, timeout_ms: int) -> ResolutionResult:
    candidates: list[tuple[str, Locator]] = []
    if hint.role and hint.name:
        candidates.append((f"role={hint.role} name={hint.name}", page.get_by_role(hint.role, name=hint.name)))  # type: ignore[arg-type]
    if hint.label:
        candidates.append((f"label={hint.label}", page.get_by_label(hint.label)))
    if hint.test_id:
        candidates.append((f"testid={hint.test_id}", page.get_by_test_id(hint.test_id)))
    if hint.text:
        candidates.append((f"text={hint.text}", page.get_by_text(hint.text, exact=True)))
    if hint.selector:
        candidates.append((f"selector={hint.selector}", page.locator(hint.selector)))

    for description, locator in candidates:
        try:
            count = await locator.count()
        except Exception as exc:
            return ResolutionResult(
                resolved=False,
                failure_category=FailureCategory.TARGET_RESOLUTION_FAILURE,
                detail=f"target lookup failed: {exc}",
            )
        if count == 1:
            try:
                await locator.wait_for(state="attached", timeout=timeout_ms)
            except Exception as exc:
                return ResolutionResult(
                    resolved=False,
                    failure_category=FailureCategory.TARGET_RESOLUTION_FAILURE,
                    detail=f"resolved target did not become attached: {exc}",
                )
            return ResolutionResult(resolved=True, locator=locator, description=description)
        if count > 1:
            return ResolutionResult(
                resolved=False,
                failure_category=FailureCategory.TARGET_RESOLUTION_FAILURE,
                detail=f"ambiguous target: {description} matched {count} elements",
            )

    # Fallback for generic <select> controls where hint matches an option
    target_str = hint.text or hint.name or hint.label or ""
    if target_str:
        target_tokens = {t.lower() for t in re.findall(r"\b[A-Za-z0-9_$]+\b", target_str)}
        if target_tokens:
            try:
                selects = page.locator("select")
                select_count = await selects.count()
                matching_selects: list[tuple[str, Locator]] = []
                for idx in range(select_count):
                    sel = selects.nth(idx)
                    options = await sel.evaluate(
                        "el => Array.from(el.options).map(o => ({ value: o.value, text: o.text }))"
                    )
                    for opt in options:
                        opt_tokens = {
                            t.lower()
                            for t in re.findall(
                                r"\b[A-Za-z0-9_$]+\b", f"{opt['value']} {opt['text']}"
                            )
                        }
                        if target_tokens.issubset(opt_tokens):
                            matching_selects.append(
                                (
                                    f"select[{idx}] option value={opt['value']!r} text={opt['text']!r}",
                                    sel,
                                )
                            )
                            break
                if len(matching_selects) == 1:
                    desc, loc = matching_selects[0]
                    await loc.wait_for(state="attached", timeout=timeout_ms)
                    return ResolutionResult(resolved=True, locator=loc, description=desc)
                elif len(matching_selects) > 1:
                    return ResolutionResult(
                        resolved=False,
                        failure_category=FailureCategory.TARGET_RESOLUTION_FAILURE,
                        detail=f"ambiguous select target: {len(matching_selects)} select controls matched {target_str!r}",
                    )
            except Exception:
                pass

    return ResolutionResult(
        resolved=False,
        failure_category=FailureCategory.TARGET_RESOLUTION_FAILURE,
        detail="no trusted semantic locator could be derived from target hint",
    )
