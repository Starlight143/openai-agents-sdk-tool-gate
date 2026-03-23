"""Tool definitions for OpenAI Agents SDK with Stage0 metadata.

Each tool declares its potential side effects for Stage0 validation.
Stage0GateHooks will read these declarations before execution.
"""

from __future__ import annotations

from typing import Any

from agents import function_tool

TOOL_SIDE_EFFECTS: dict[str, list[str]] = {}


def _register_side_effects(tool_name: str, side_effects: list[str]) -> None:
    TOOL_SIDE_EFFECTS[tool_name] = side_effects


@function_tool
def safe_lookup(query: str) -> str:
    """Search for information in documentation or knowledge base.

    This is a low-risk, read-only operation that retrieves information
    without modifying any state or data.

    Args:
        query: The search query string.

    Returns:
        Search results as a formatted string.
    """
    results = [
        f"Result 1: Documentation about '{query}'",
        f"Result 2: Best practices for '{query}'",
        f"Result 3: Examples related to '{query}'",
    ]
    return "\n".join(results)


_register_side_effects("safe_lookup", [])


@function_tool
def get_system_status() -> str:
    """Get the current system status and health information.

    This is a read-only operation that checks system health.

    Returns:
        System status information.
    """
    return "System Status: All services operational. CPU: 45%, Memory: 62%, Disk: 78%"


_register_side_effects("get_system_status", [])


@function_tool
def dangerous_delete(file_path: str, confirm: bool = False) -> str:
    """Delete a file from the filesystem.

    WARNING: This is a destructive operation with permanent side effects.
    Stage0 MUST validate this action before execution.

    Args:
        file_path: The path to the file to delete.
        confirm: Must be True to execute the deletion.

    Returns:
        Result of the deletion operation.
    """
    if not confirm:
        return "Deletion cancelled: confirm parameter must be True"
    return f"File deleted successfully: {file_path}"


_register_side_effects("dangerous_delete", ["data_deletion", "filesystem_modification"])


@function_tool
def deploy_to_production(service_name: str, version: str) -> str:
    """Deploy a service to production environment.

    WARNING: This is a high-risk operation with significant side effects.
    Stage0 MUST validate this action before execution.

    Args:
        service_name: Name of the service to deploy.
        version: Version tag to deploy.

    Returns:
        Deployment status.
    """
    return f"Deployed {service_name} version {version} to production"


_register_side_effects(
    "deploy_to_production",
    ["deploy", "production_change", "infrastructure_modification"],
)


@function_tool
def send_notification(recipient: str, message: str, channel: str = "email") -> str:
    """Send a notification to a user or team.

    This action has external side effects (sends actual messages).

    Args:
        recipient: The recipient email or identifier.
        message: The message content to send.
        channel: Communication channel (email, slack, sms).

    Returns:
        Delivery confirmation.
    """
    return f"Notification sent to {recipient} via {channel}: {message[:50]}..."


_register_side_effects("send_notification", ["external_communication", "send_email"])


@function_tool
def approval_required_action(action_type: str, target: str, reason: str) -> str:
    """Execute an action that requires human approval.

    This tool represents actions that should always require human review,
    such as financial transactions, access grants, or policy changes.

    Args:
        action_type: Type of action (e.g., 'grant_access', 'process_payment').
        target: Target of the action (e.g., user ID, account).
        reason: Reason for executing this action.

    Returns:
        Action execution result.
    """
    return f"Executed {action_type} on {target}: {reason}"


_register_side_effects(
    "approval_required_action",
    ["requires_approval", "sensitive_operation"],
)


ALL_TOOLS = [
    safe_lookup,
    get_system_status,
    dangerous_delete,
    deploy_to_production,
    send_notification,
    approval_required_action,
]

SAFE_TOOLS = [safe_lookup, get_system_status]
DANGEROUS_TOOLS = [dangerous_delete, deploy_to_production, send_notification]
APPROVAL_REQUIRED_TOOLS = [approval_required_action]


def get_tool_by_name(name: str) -> Any | None:
    tool_map = {t.name: t for t in ALL_TOOLS}
    return tool_map.get(name)
