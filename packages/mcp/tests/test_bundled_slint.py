"""Bundled slint-mcp provider — contract checks that need no Slint app.

Driving a real application is covered by the desktop suite; what matters here is
that the provider is wired into the bundled registry, advertises exactly the
catalog its builtin spec promises, and fails understandably when a step runs
before anything was launched.
"""

from __future__ import annotations

import pytest
from suitest_mcp.bundled.in_process_runtime import get_bundled_builder
from suitest_mcp.bundled.slint import PROVIDER_NAME, build_slint_server
from suitest_mcp.models import McpProviderConfig, McpTransport
from suitest_mcp.providers.builtin_specs import BUILTIN_SPECS


def _config() -> McpProviderConfig:
    return McpProviderConfig(
        id="builtin:slint-mcp",
        workspace_id="_builtin_",
        name=PROVIDER_NAME,
        kind="desktop",
        transport=McpTransport.IN_PROCESS,
        endpoint="in-process://slint",
    )


def test_provider_resolves_through_the_bundled_registry() -> None:
    """The lazy-import entry is what lets the runtime find us without the
    bundled package importing every provider eagerly."""
    assert get_bundled_builder(PROVIDER_NAME) is not None


@pytest.mark.asyncio
async def test_tool_catalog_matches_the_builtin_spec() -> None:
    """The advertised tools and the spec's `config_json` must not drift — the
    spec is what routing and the docs are written against."""
    spec = next(s for s in BUILTIN_SPECS if s.name == PROVIDER_NAME)
    advertised = {t.name for t in await build_slint_server(_config()).list_tools()}
    assert advertised == set(spec.config_json["tools"])


@pytest.mark.asyncio
async def test_tools_before_launch_say_so() -> None:
    """A step that forgets `slint.launch` should name the missing step, not
    fail somewhere deep in the HTTP client."""
    server = build_slint_server(_config())
    with pytest.raises(AssertionError, match=r"slint\.launch"):
        await server.call_tool("slint.click", {"id": "Some::thing"})


@pytest.mark.asyncio
async def test_missing_selector_is_reported_as_such() -> None:
    server = build_slint_server(_config())
    with pytest.raises(AssertionError, match="no element given"):
        await server.call_tool("slint.click", {})


@pytest.mark.asyncio
async def test_selector_accepts_id_label_and_index() -> None:
    """Ids are component-scoped, so a step must be able to disambiguate by the
    label the user sees, or failing that by position."""
    from suitest_mcp.bundled.slint import _selector

    assert _selector({"id": "A::b"}) == ("A::b", None, 0)
    assert _selector({"label": "New Query"}) == (None, "New Query", 0)
    assert _selector({"id": "A::b", "label": "Save", "index": 2}) == ("A::b", "Save", 2)


@pytest.mark.asyncio
async def test_launch_without_a_command_is_rejected() -> None:
    server = build_slint_server(_config())
    with pytest.raises(AssertionError, match=r"`command` is required"):
        await server.call_tool("slint.launch", {})


@pytest.mark.asyncio
async def test_aclose_is_safe_before_launch() -> None:
    """Session teardown runs whether or not a step ever launched anything."""
    await build_slint_server(_config()).aclose()
