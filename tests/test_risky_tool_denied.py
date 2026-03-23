"""Test that dangerous tools are blocked by Stage0."""

from __future__ import annotations

import pytest

from stage0 import Verdict


class TestRiskyToolDenied:
    """Tests for DENY scenario - dangerous tools should be blocked."""

    @pytest.mark.asyncio
    async def test_dangerous_delete_has_side_effects(self):
        from app.tools import TOOL_SIDE_EFFECTS

        side_effects = TOOL_SIDE_EFFECTS.get("dangerous_delete", [])
        assert len(side_effects) > 0
        assert (
            "data_deletion" in side_effects or "filesystem_modification" in side_effects
        )

    @pytest.mark.asyncio
    async def test_dangerous_delete_blocked_by_mock_hooks(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "dangerous_delete"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert exc_info.value.verdict in (Verdict.DENY, Verdict.DEFER)
        assert "dangerous_delete" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_deploy_to_production_has_side_effects(self):
        from app.tools import TOOL_SIDE_EFFECTS

        side_effects = TOOL_SIDE_EFFECTS.get("deploy_to_production", [])
        assert "deploy" in side_effects
        assert "production_change" in side_effects

    @pytest.mark.asyncio
    async def test_deploy_blocked_by_mock_hooks(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "deploy_to_production"

        with pytest.raises(Stage0BlockedError):
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

    @pytest.mark.asyncio
    async def test_blocked_error_contains_required_fields(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import MockStage0GateHooks, Stage0BlockedError

        hooks = MockStage0GateHooks(raise_on_block=True)

        mock_tool.name = "dangerous_delete"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        error = exc_info.value
        assert error.tool_name == "dangerous_delete"
        assert error.verdict in (Verdict.DENY, Verdict.DEFER)
        assert error.request_id.startswith("mock_")
        assert error.policy_version == "mock-1.0.0"

    @pytest.mark.asyncio
    async def test_dangerous_tools_category(self):
        from app.tools import DANGEROUS_TOOLS, TOOL_SIDE_EFFECTS

        for tool in DANGEROUS_TOOLS:
            tool_name = tool.name
            side_effects = TOOL_SIDE_EFFECTS.get(tool_name, [])
            assert len(side_effects) > 0, (
                f"Dangerous tool {tool_name} should have side effects"
            )

    @pytest.mark.asyncio
    async def test_dangerous_tools_in_all_tools(self):
        from app.tools import ALL_TOOLS, DANGEROUS_TOOLS

        all_tool_names = {t.name for t in ALL_TOOLS}
        dangerous_tool_names = {t.name for t in DANGEROUS_TOOLS}

        assert dangerous_tool_names.issubset(all_tool_names)
