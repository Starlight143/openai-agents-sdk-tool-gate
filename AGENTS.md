# Stage0 Tool Gate Integration

This document describes the agent architecture, tools, and Stage0 integration for the `openai-agents-sdk-tool-gate` repository.

## Overview

This project demonstrates how to integrate [Stage0](https://signalpulse.org) runtime policy validation with [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). It provides a production-ready pattern for protecting AI agents from executing unintended dangerous operations.

## Agent Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Application                              │
├─────────────────────────────────────────────────────────────────┤
│  Runner.run(agent, input, hooks=Stage0GateHooks(client))        │
│      │                                                           │
│      ▼                                                           │
│  ┌─────────────┐    on_tool_start()    ┌─────────────────┐      │
│  │    Agent    │──────────────────────▶│ Stage0GateHooks │      │
│  │  (tools=[]) │                       └────────┬────────┘      │
│  └──────┬──────┘                                │               │
│         │                                       ▼               │
│         │                              ┌─────────────────┐      │
│         │                              │  Stage0 /check  │      │
│         │                              └────────┬────────┘      │
│         │                                       │               │
│         │              ┌────────────────────────┼───────────┐   │
│         │              │                        │           │   │
│         │        ALLOW │                  DENY  │     DEFER │   │
│         │              ▼                        ▼           ▼   │
│         │      Execute Tool              Raise Error           │
│         │              │                                        │
│         ▼              ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Tracing (custom_span)                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Pattern

```python
from agents import Agent, Runner
from app import Stage0GateHooks, create_protected_agent
from stage0 import Stage0Client

# Create Stage0 client
client = Stage0Client(api_key="your-api-key")

# Create hooks for tool authorization
hooks = Stage0GateHooks(client)

# Create agent with protected tools
agent = create_protected_agent()

# Run with Stage0 protection
result = await Runner.run(agent, "user query", hooks=hooks)
```

## Tools

### Tool Categories

| Category | Tools | Side Effects | Stage0 Behavior |
|----------|-------|--------------|-----------------|
| **Safe** | `safe_lookup`, `get_system_status` | None | Always ALLOW |
| **Dangerous** | `dangerous_delete`, `deploy_to_production`, `send_notification` | data_deletion, deploy, external_communication | May DENY |
| **Approval Required** | `approval_required_action` | requires_approval, sensitive_operation | DEFER (needs human review) |

### Tool Definitions

#### Safe Tools (Read-Only)

```python
@function_tool
def safe_lookup(query: str) -> str:
    """Search for information in documentation or knowledge base."""
    # Returns search results without modifying any state

@function_tool
def get_system_status() -> str:
    """Get the current system status and health information."""
    # Returns status without side effects
```

#### Dangerous Tools (Side Effects)

```python
@function_tool
def dangerous_delete(file_path: str, confirm: bool = False) -> str:
    """Delete a file from the filesystem."""
    # Side effects: data_deletion, filesystem_modification

@function_tool
def deploy_to_production(service_name: str, version: str) -> str:
    """Deploy a service to production environment."""
    # Side effects: deploy, production_change, infrastructure_modification

@function_tool
def send_notification(recipient: str, message: str, channel: str = "email") -> str:
    """Send a notification to a user or team."""
    # Side effects: external_communication, send_email
```

#### Approval Required Tools

```python
@function_tool
def approval_required_action(action_type: str, target: str, reason: str) -> str:
    """Execute an action that requires human approval."""
    # Side effects: requires_approval, sensitive_operation
```

### Side Effects Registry

Each tool declares its potential side effects in `TOOL_SIDE_EFFECTS`:

```python
from app import TOOL_SIDE_EFFECTS

TOOL_SIDE_EFFECTS = {
    "safe_lookup": [],
    "get_system_status": [],
    "dangerous_delete": ["data_deletion", "filesystem_modification"],
    "deploy_to_production": ["deploy", "production_change", "infrastructure_modification"],
    "send_notification": ["external_communication", "send_email"],
    "approval_required_action": ["requires_approval", "sensitive_operation"],
}
```

## Stage0 Integration

### Stage0GateHooks

The `Stage0GateHooks` class implements `RunHooks` from OpenAI Agents SDK to intercept tool calls before execution.

```python
class Stage0GateHooks(RunHooks[Any]):
    def __init__(
        self,
        client: Stage0Client,
        raise_on_block: bool = True,      # Raise exception on DENY/DEFER
        log_decisions: bool = True,        # Log to tracing
        fail_safe_deny: bool = True,       # DENY when API unavailable
    ):
        ...

    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Any,
    ) -> None:
        # Called BEFORE each tool execution
        # Validates with Stage0 API
        # Raises Stage0BlockedError if DENY/DEFER
```

### Stage0BlockedError

Custom exception raised when Stage0 blocks a tool execution:

```python
class Stage0BlockedError(Exception):
    tool_name: str
    verdict: Verdict  # DENY or DEFER
    reason: str
    request_id: str   # For audit trail
    policy_version: str
```

### Mock Mode (Testing Without API Key)

```python
from app import MockStage0GateHooks

hooks = MockStage0GateHooks()
# Simulates Stage0 responses based on tool naming:
# - safe_* → ALLOW
# - dangerous_* → DENY
# - approval_* → DEFER
```

## Tracing

### Integration with OpenAI Agents SDK Tracing

```python
from app import trace_stage0_decision, trace_tool_execution

# Called automatically by Stage0GateHooks
trace_stage0_decision(
    tool_name="dangerous_delete",
    response=stage0_response,
)

# Records in trace:
# - tool_name
# - verdict (ALLOW/DENY/DEFER)
# - request_id
# - policy_version
# - risk_score
# - high_risk
```

### View Traces

Traces are available at: https://platform.openai.com/traces

## Agent Factory Functions

```python
from app import create_protected_agent, create_safe_agent, create_demo_agent

# Full agent with all tools
agent = create_protected_agent(
    name="ProtectedAgent",
    model="gpt-4o-mini",
)

# Safe-only agent (read-only operations)
agent = create_safe_agent()

# Demo agent for showcasing Stage0 blocking
agent = create_demo_agent()
```

## Running the Demo

```bash
# Quick demo (no API keys needed)
python run_demo.py --hooks-only --mock --scenario all --auto

# With live Stage0 API
python run_demo.py --hooks-only --scenario all --auto

# Full agent demo (requires OPENAI_API_KEY)
python run_demo.py --mock --scenario all --auto
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/test_risky_tool_denied.py -v
```

## Key Design Decisions

1. **RunHooks over tool wrapping**: Uses `on_tool_start` hook instead of wrapping individual tools for centralized, consistent protection.

2. **Async-to-thread for sync API**: `Stage0Client.check_goal()` is synchronous (uses `requests`), so we wrap it in `asyncio.to_thread()` to avoid blocking the event loop.

3. **Fail-safe deny**: When Stage0 API is unavailable, the default behavior is to DENY operations (configurable via `fail_safe_deny=False`).

4. **Tracing isolation**: Tracing failures don't break tool execution - errors are logged but don't propagate.

5. **Tool naming convention**: Mock mode uses tool name prefixes (`safe_*`, `dangerous_*`, `approval_*`) for deterministic demo behavior.

## References

- [OpenAI Agents SDK Documentation](https://github.com/openai/openai-agents-python)
- [Stage0 API Documentation](https://signalpulse.org/docs)
- [RunHooks Reference](https://github.com/openai/openai-agents-python/blob/main/src/agents/hooks.py)