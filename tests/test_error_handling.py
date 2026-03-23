"""Test error handling in Stage0 hooks."""

from __future__ import annotations

import pytest

from stage0 import Verdict


class TestErrorHandling:
    """Tests for error handling in Stage0GateHooks."""

    @pytest.mark.asyncio
    async def test_api_error_with_fail_safe_deny(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import Stage0GateHooks, Stage0BlockedError

        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.check_goal.side_effect = Exception("Network error")

        hooks = Stage0GateHooks(mock_client, raise_on_block=True, fail_safe_deny=True)

        mock_tool.name = "safe_lookup"

        with pytest.raises(Stage0BlockedError) as exc_info:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert exc_info.value.request_id == "error_unavailable"
        assert "Stage0 unavailable" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_api_error_with_fail_safe_allow(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import Stage0GateHooks

        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.check_goal.side_effect = Exception("Network error")

        hooks = Stage0GateHooks(mock_client, raise_on_block=True, fail_safe_deny=False)

        mock_tool.name = "safe_lookup"

        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is None

    @pytest.mark.asyncio
    async def test_tracing_error_does_not_break_execution(
        self, mock_agent, mock_tool, mock_context
    ):
        from app.stage0_hooks import Stage0GateHooks
        from stage0 import PolicyResponse

        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.check_goal.return_value = PolicyResponse(
            verdict=Verdict.ALLOW,
            reason="OK",
            constraints_applied=[],
            raw_response={},
            request_id="test_123",
            policy_version="v1.0",
        )

        hooks = Stage0GateHooks(mock_client, raise_on_block=True, log_decisions=True)

        mock_tool.name = "safe_lookup"

        with patch(
            "app.stage0_hooks.trace_stage0_decision",
            side_effect=Exception("Tracing error"),
        ):
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is not None
        assert hooks._last_response.verdict == Verdict.ALLOW

    @pytest.mark.asyncio
    async def test_async_to_thread_works(self, mock_agent, mock_tool, mock_context):
        from app.stage0_hooks import Stage0GateHooks
        from stage0 import PolicyResponse

        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.check_goal.return_value = PolicyResponse(
            verdict=Verdict.ALLOW,
            reason="OK",
            constraints_applied=[],
            raw_response={},
            request_id="test_async",
            policy_version="v1.0",
        )

        hooks = Stage0GateHooks(mock_client, raise_on_block=True)

        mock_tool.name = "safe_lookup"

        await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

        assert hooks._last_response is not None
        assert hooks._last_response.request_id == "test_async"
        mock_client.check_goal.assert_called_once()
