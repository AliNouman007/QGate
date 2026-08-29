from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from .models import ArtifactRef, DomEvidence, StepEvidence

if TYPE_CHECKING:
    from pathlib import Path

    from playwright.async_api import Locator, Page


_CSS_KEYS = (
    "display",
    "visibility",
    "position",
    "width",
    "height",
    "marginTop",
    "marginRight",
    "marginBottom",
    "marginLeft",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "fontSize",
    "fontWeight",
    "textAlign",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def capture_page_evidence(
    page: Page,
    *,
    requested_route: str | None = None,
    locator: Locator | None = None,
    locator_description: str | None = None,
    screenshot_path: Path | None = None,
) -> StepEvidence:
    evidence = StepEvidence(
        requested_route=requested_route,
        final_url=page.url,
        title=await page.title(),
    )
    if locator is not None:
        evidence.dom = await capture_dom_evidence(locator, locator_description=locator_description)
    if screenshot_path is not None:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        evidence.artifacts.append(
            ArtifactRef(kind="screenshot", path=str(screenshot_path), sha256=_sha256(screenshot_path))
        )
    return evidence


async def capture_dom_evidence(
    locator: Locator,
    *,
    locator_description: str | None = None,
) -> DomEvidence:
    visible = await locator.is_visible()
    enabled = await locator.is_enabled()
    tag = await locator.evaluate("el => el.tagName.toLowerCase()")
    role = await locator.get_attribute("role")
    text = (await locator.inner_text())[:1000]
    value: str | None = None
    try:
        value = await locator.input_value()
    except Exception:
        value = None
    html = (await locator.evaluate("el => el.outerHTML"))[:2000]
    box = await locator.bounding_box()
    css = await locator.evaluate(
        """(el, keys) => {
          const s = getComputedStyle(el);
          const out = {};
          for (const key of keys) out[key] = s[key] || '';
          return out;
        }""",
        list(_CSS_KEYS),
    )
    return DomEvidence(
        locator_description=locator_description,
        tag=str(tag),
        role=role,
        text=text,
        value=value,
        visible=visible,
        enabled=enabled,
        html_excerpt=str(html),
        bounding_box={k: float(v) for k, v in box.items()} if box else None,  # type: ignore[arg-type]
        computed_css={str(k): str(v) for k, v in dict(css).items()},
    )
