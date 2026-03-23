"""Test that approval-required tools trigger DEFER."""

from __future__ import annotations

import pytest

from stage0 import Verdict


class TestDeferPath:
    """Tests for DEFER scenario - approval-required tools should defer."""

    @pytest.mark.asyncio
    async def test_approval_required_has_correct_side_effects(self):
        from app.tools import TOOL_SIDE_EFFECTS

        side_effects = TOOL_SIDE_EFFECTS.get("approval_required_action", [])
        assert "requires_approval" in side_effects
        assert "sensitive_operation" in side_effects

    @pytest.mark.asyncio
    async def test_approval_required_deferred_by_mock_hooks(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "approval_required_action"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert exc_info.value.verdict == Verdict.DEFER

    @pytest.mark.asyncio
    async def test_approval_required_in_correct_category(self):
        from app.tools import APPROVAL_REQUIRED_TOOLS

        tool_names = {t.name for t in APPROVAL_REQUIRED_TOOLS}
        assert "approval_required_action" in tool_names

    @pytest.mark.asyncio
    async def test_defer_message_is_informative(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "approval_required_action"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        error = exc_info.value
        assert (
            "human review" in error.reason.lower() or "approval" in error.reason.lower()
        )

    @pytest.mark.asyncio
    async def test_no_raise_on_block_mode(self, mock_agent, mock_tool, mock_context):
        from app.stage0_hooks import MockStage0GateHooks

        hooks = MockStage0GateHooks(raise_on_block=False)

        mock_tool.name = "approval_required_action"

        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is not None
        assert hooks._last_response.verdict == Verdict.DEFER

    @pytest.mark.asyncio
    async def test_approval_tools_in_all_tools(self):
        from app.tools import ALL_TOOLS, APPROVAL_REQUIRED_TOOLS

        all_tool_names = {t.name for t in ALL_TOOLS}
        approval_tool_names = {t.name for t in APPROVAL_REQUIRED_TOOLS}

        assert approval_tool_names.issubset(all_tool_names)
