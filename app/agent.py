"""Agent factory with Stage0 protection.

This module provides functions to create agents with Stage0-protected tools.
"""

from __future__ import annotations

from typing import Any

from agents import Agent

from app.tools import ALL_TOOLS, SAFE_TOOLS


def create_protected_agent(
    name: str = "ProtectedAgent",
    instructions: str | None = None,
    tools: list[Any] | None = None,
    model: str = "gpt-4o-mini",
) -> Agent[Any]:
    if tools is None:
        tools = ALL_TOOLS

    default_instructions = """You are a helpful AI assistant with access to various tools.

IMPORTANT: Some tools are protected by Stage0 policy validation. If you attempt to
use a dangerous tool, Stage0 may block the execution. This is expected behavior
designed to protect against unintended actions.

Available tool categories:
- Safe tools (safe_lookup, get_system_status): Read-only operations that are always allowed
- Dangerous tools (dangerous_delete, deploy_to_production, send_notification): May be blocked
- Approval-required tools (approval_required_action): Require human review

Always explain what you're trying to do before using a tool. If a tool is blocked,
inform the user and suggest alternatives."""

    return Agent(
        name=name,
        instructions=instructions or default_instructions,
        tools=tools,
        model=model,
    )


def create_safe_agent(
    name: str = "SafeAgent",
    model: str = "gpt-4o-mini",
) -> Agent[Any]:
    return create_protected_agent(
        name=name,
        instructions="You are a safe assistant that can only perform read-only operations.",
        tools=SAFE_TOOLS,
        model=model,
    )


def create_demo_agent(
    name: str = "DemoAgent",
    model: str = "gpt-4o-mini",
) -> Agent[Any]:
    demo_instructions = """You are a demo agent showcasing Stage0 tool gate integration.

You have access to various tools, some of which are protected:
1. safe_lookup - Search for information (SAFE - always allowed)
2. get_system_status - Check system health (SAFE - always allowed)
3. dangerous_delete - Delete files (DANGEROUS - will be blocked)
4. deploy_to_production - Deploy services (DANGEROUS - will be blocked)
5. send_notification - Send messages (DANGEROUS - may be blocked)
6. approval_required_action - Sensitive operations (requires approval)

When asked to perform dangerous operations, try them to demonstrate Stage0 blocking."""

    return create_protected_agent(
        name=name,
        instructions=demo_instructions,
        model=model,
    )
