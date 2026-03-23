"""Tracing integration for Stage0 decisions.

This module provides helpers to record Stage0 policy decisions
in OpenAI Agents SDK traces using custom_span.
"""

from __future__ import annotations

from typing import Any

from agents import custom_span

from stage0 import PolicyResponse


def trace_stage0_decision(
    tool_name: str,
    response: PolicyResponse,
    extra_data: dict[str, Any] | None = None,
) -> None:
    with custom_span(
        "stage0_policy_check",
        data={
            "tool_name": tool_name,
            "verdict": response.verdict.value,
            "request_id": response.request_id,
            "policy_version": response.policy_version,
            "reason": response.reason[:200] if response.reason else "",
            "risk_score": response.risk_score,
            "high_risk": response.high_risk,
            **(extra_data or {}),
        },
    ):
        pass


def trace_tool_execution(
    tool_name: str,
    success: bool,
    error: str | None = None,
) -> None:
    with custom_span(
        "tool_execution",
        data={
            "tool_name": tool_name,
            "success": success,
            "error": error,
        },
    ):
        pass


def format_decision_summary(response: PolicyResponse) -> str:
    lines = [
        f"Verdict: {response.verdict.value}",
        f"Request ID: {response.request_id}",
        f"Policy Version: {response.policy_version}",
        f"Reason: {response.reason}",
    ]

    if response.risk_score > 0:
        lines.append(f"Risk Score: {response.risk_score}")

    if response.high_risk:
        lines.append("High Risk: True")

    if response.issues:
        lines.append("Issues:")
        for issue in response.issues:
            severity = issue.get("severity", "UNKNOWN")
            code = issue.get("code", "UNKNOWN")
            message = issue.get("message", "")
            lines.append(f"  [{severity}] {code}: {message}")

    return "\n".join(lines)
