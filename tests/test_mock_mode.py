"""Test mock mode functionality."""

from __future__ import annotations

import pytest

from stage0 import Verdict


class TestMockMode:
    """Tests for mock mode operation."""

    @pytest.mark.asyncio
    async def test_mock_hooks_allow_safe_tools(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks()

        mock_tool.name = "safe_lookup"
        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is not None
        assert hooks._last_response.verdict == Verdict.ALLOW

    @pytest.mark.asyncio
    async def test_mock_hooks_deny_dangerous_tools(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "dangerous_delete"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert exc_info.value.verdict == Verdict.DENY

    @pytest.mark.asyncio
    async def test_mock_hooks_defer_approval_tools(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "approval_required_action"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert exc_info.value.verdict == Verdict.DEFER

    @pytest.mark.asyncio
    async def test_mock_hooks_generate_request_ids(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks()

        mock_tool.name = "safe_lookup"
        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is not None
        assert hooks._last_response.request_id.startswith("mock_")
        assert "safe_lookup" in hooks._last_response.request_id

    @pytest.mark.asyncio
    async def test_mock_hooks_track_call_history(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks(raise_on_block=False)

        for tool_name in ["safe_lookup", "dangerous_delete", "safe_query"]:
            mock_tool.name = tool_name
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert len(hooks.call_log) == 3

        tool_names = [entry["tool_name"] for entry in hooks.call_log]
        assert tool_names == ["safe_lookup", "dangerous_delete", "safe_query"]

    @pytest.mark.asyncio
    async def test_unknown_tool_with_side_effects_denied(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.tools import TOOL_SIDE_EFFECTS
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        TOOL_SIDE_EFFECTS["unknown_risky_tool"] = ["unknown_side_effect"]

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "unknown_risky_tool"

        with pytest.raises(Stage0BlockedError):
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        del TOOL_SIDE_EFFECTS["unknown_risky_tool"]

    @pytest.mark.asyncio
    async def test_mock_hooks_set_risk_score_correctly(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks(raise_on_block=False)

        mock_tool.name = "safe_lookup"
        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)
        assert hooks._last_response is not None
        assert hooks._last_response.risk_score == 0

        mock_tool.name = "dangerous_delete"
        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)
        assert hooks._last_response is not None
        assert hooks._last_response.risk_score > 0
