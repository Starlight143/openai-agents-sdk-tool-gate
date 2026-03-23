"""Test that safe tools are allowed to execute."""

from __future__ import annotations

import pytest


class TestSafeToolAllowed:
    """Tests for ALLOW scenario - safe tools should execute."""

    @pytest.mark.asyncio
    async def test_safe_lookup_registered_correctly(self):
        from app.tools import safe_lookup, TOOL_SIDE_EFFECTS

        assert safe_lookup.name == "safe_lookup"
        assert TOOL_SIDE_EFFECTS.get("safe_lookup") == []

    @pytest.mark.asyncio
    async def test_get_system_status_registered_correctly(self):
        from app.tools import get_system_status, TOOL_SIDE_EFFECTS

        assert get_system_status.name == "get_system_status"
        assert TOOL_SIDE_EFFECTS.get("get_system_status") == []

    @pytest.mark.asyncio
    async def test_safe_tools_have_no_side_effects(self):
        from app.tools import TOOL_SIDE_EFFECTS, SAFE_TOOLS

        for tool in SAFE_TOOLS:
            tool_name = tool.name
            side_effects = TOOL_SIDE_EFFECTS.get(tool_name, [])
            assert side_effects == [], (
                f"Safe tool {tool_name} should have no side effects"
            )

    @pytest.mark.asyncio
    async def test_mock_hooks_allow_safe_tools(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "safe_lookup"

        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is not None

    @pytest.mark.asyncio
    async def test_mock_hooks_log_safe_tool_call(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks()

        mock_tool.name = "safe_lookup"
        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert len(hooks.call_log) == 1
        assert hooks.call_log[0]["tool_name"] == "safe_lookup"
        assert hooks.call_log[0]["verdict"] == "ALLOW"

    @pytest.mark.asyncio
    async def test_safe_tools_in_all_tools(self):
        from app.tools import ALL_TOOLS, SAFE_TOOLS

        all_tool_names = {t.name for t in ALL_TOOLS}
        safe_tool_names = {t.name for t in SAFE_TOOLS}

        assert safe_tool_names.issubset(all_tool_names)
