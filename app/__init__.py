"""OpenAI Agents SDK integration with Stage0 Tool Gate.

This module provides:
- Protected tools with @function_tool decorator
- Stage0GateHooks for runtime policy validation
- Tracing integration for audit trail
- Agent factory with Stage0 protection
"""

from app.tools import (
    safe_lookup,
    get_system_status,
    dangerous_delete,
    deploy_to_production,
    send_notification,
    approval_required_action,
    TOOL_SIDE_EFFECTS,
    ALL_TOOLS,
    SAFE_TOOLS,
    DANGEROUS_TOOLS,
    APPROVAL_REQUIRED_TOOLS,
)
from app.stage0_hooks import Stage0GateHooks, Stage0BlockedError, MockStage0GateHooks
from app.tracing import (
    trace_stage0_decision,
    trace_tool_execution,
    format_decision_summary,
)
from app.agent import create_protected_agent, create_safe_agent, create_demo_agent

__all__ = [
    "safe_lookup",
    "get_system_status",
    "dangerous_delete",
    "deploy_to_production",
    "send_notification",
    "approval_required_action",
    "TOOL_SIDE_EFFECTS",
    "ALL_TOOLS",
    "SAFE_TOOLS",
    "DANGEROUS_TOOLS",
    "APPROVAL_REQUIRED_TOOLS",
    "Stage0GateHooks",
    "MockStage0GateHooks",
    "Stage0BlockedError",
    "trace_stage0_decision",
    "trace_tool_execution",
    "format_decision_summary",
    "create_protected_agent",
    "create_safe_agent",
    "create_demo_agent",
]
