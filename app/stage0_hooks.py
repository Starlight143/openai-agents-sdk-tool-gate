"""Stage0 authorization hooks for OpenAI Agents SDK.

This module implements RunHooks to intercept tool calls and validate
execution intent with Stage0 BEFORE the tool actually executes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents import Agent, RunContextWrapper, RunHooks

from stage0 import PolicyResponse, Stage0Client, Verdict

from app.tools import TOOL_SIDE_EFFECTS
from app.tracing import trace_stage0_decision

logger = logging.getLogger(__name__)


class Stage0BlockedError(Exception):
    """Raised when Stage0 blocks a tool execution.

    This exception is raised in on_tool_start when Stage0 returns
    DENY or DEFER verdict, preventing the tool from executing.
    """

    def __init__(
        self,
        tool_name: str,
        verdict: Verdict,
        reason: str,
        request_id: str,
        policy_version: str,
    ):
        self.tool_name = tool_name
        self.verdict = verdict
        self.reason = reason
        self.request_id = request_id
        self.policy_version = policy_version
        super().__init__(
            f"Stage0 {verdict.value}: Tool '{tool_name}' blocked - {reason} "
            f"(request_id: {request_id})"
        )


class Stage0GateHooks(RunHooks[Any]):
    """RunHooks implementation that validates tool calls with Stage0.

    This hook intercepts every tool call and validates it with Stage0
    BEFORE execution. If Stage0 returns DENY or DEFER, the tool is
    blocked and a Stage0BlockedError is raised.

    Usage:
        client = Stage0Client()
        hooks = Stage0GateHooks(client)
        result = await Runner.run(agent, "query", hooks=hooks)
    """

    def __init__(
        self,
        client: Stage0Client,
        raise_on_block: bool = True,
        log_decisions: bool = True,
        fail_safe_deny: bool = True,
    ):
        self.client = client
        self.raise_on_block = raise_on_block
        self.log_decisions = log_decisions
        self.fail_safe_deny = fail_safe_deny
        self._last_response: PolicyResponse | None = None

    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Any,
    ) -> None:
        tool_name = getattr(tool, "name", str(tool))
        side_effects = TOOL_SIDE_EFFECTS.get(tool_name, [])

        try:
            response = await asyncio.to_thread(
                self.client.check_goal,
                goal=f"Execute tool: {tool_name}",
                tools=[tool_name],
                side_effects=side_effects,
                context={
                    "agent_name": agent.name,
                    "tool_name": tool_name,
                },
            )
        except Exception as e:
            logger.error(f"Stage0 API error for {tool_name}: {e}")
            if self.fail_safe_deny:
                raise Stage0BlockedError(
                    tool_name=tool_name,
                    verdict=Verdict.DENY,
                    reason=f"Stage0 unavailable: {e}",
                    request_id="error_unavailable",
                    policy_version="local",
                )
            return

        self._last_response = response

        if self.log_decisions:
            try:
                trace_stage0_decision(
                    tool_name=tool_name,
                    response=response,
                )
            except Exception as e:
                logger.warning(f"Tracing failed for {tool_name}: {e}")

        if response.verdict == Verdict.ALLOW:
            return

        if self.raise_on_block:
            raise Stage0BlockedError(
                tool_name=tool_name,
                verdict=response.verdict,
                reason=response.reason,
                request_id=response.request_id,
                policy_version=response.policy_version,
            )

    @property
    def last_response(self) -> PolicyResponse | None:
        return self._last_response


class MockStage0GateHooks(RunHooks[Any]):
    """Mock hooks for testing without a real Stage0 API key.

    This hook simulates Stage0 responses based on tool name patterns:
    - safe_* tools: ALLOW
    - dangerous_* tools: DENY
    - approval_* tools: DEFER
    """

    def __init__(self, raise_on_block: bool = True):
        self.raise_on_block = raise_on_block
        self._last_response: PolicyResponse | None = None
        self._call_log: list[dict[str, Any]] = []

    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Any,
    ) -> None:
        tool_name = getattr(tool, "name", str(tool))

        verdict, reason = self._determine_verdict(tool_name)

        response = PolicyResponse(
            verdict=verdict,
            reason=reason,
            constraints_applied=[],
            raw_response={},
            request_id=f"mock_{tool_name}_{len(self._call_log)}",
            policy_version="mock-1.0.0",
            risk_score=0 if verdict == Verdict.ALLOW else 80,
            high_risk=verdict != Verdict.ALLOW,
        )

        self._last_response = response
        self._call_log.append(
            {
                "tool_name": tool_name,
                "verdict": verdict.value,
                "reason": reason,
            }
        )

        try:
            trace_stage0_decision(tool_name=tool_name, response=response)
        except Exception:
            pass

        if verdict == Verdict.ALLOW:
            return

        if self.raise_on_block:
            raise Stage0BlockedError(
                tool_name=tool_name,
                verdict=verdict,
                reason=reason,
                request_id=response.request_id,
                policy_version=response.policy_version,
            )

    def _determine_verdict(self, tool_name: str) -> tuple[Verdict, str]:
        if tool_name.startswith("safe_"):
            return Verdict.ALLOW, "Low-risk read-only operation"
        if tool_name.startswith("dangerous_"):
            return Verdict.DENY, "High-risk operation requires explicit approval"
        if tool_name.startswith("approval_"):
            return Verdict.DEFER, "This action requires human review"
        if not TOOL_SIDE_EFFECTS.get(tool_name):
            return Verdict.ALLOW, "No side effects detected"
        return Verdict.DENY, "Unknown tool with potential side effects"

    @property
    def call_log(self) -> list[dict[str, Any]]:
        return list(self._call_log)
