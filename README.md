# Stage0 Tool Gate for OpenAI Agents SDK

A production-ready integration demonstrating how to protect AI agents built with OpenAI Agents SDK using Stage0 runtime policy validation.

**Clone-and-run quality**: Developers can see safe tools pass, dangerous tools get blocked, and Stage0 decisions logged to traces.

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Starlight143/openai-agents-sdk-tool-gate.git
cd openai-agents-sdk-tool-gate

python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

# Configure API key (optional - mock mode works without it)
cp .env.example .env
# Edit .env and add your STAGE0_API_KEY

# Run the demo
python run_demo.py --mock
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Your Application                         │
├─────────────────────────────────────────────────────────────────┤
│  run_demo.py                                                     │
│      │                                                           │
│      ▼                                                           │
│  ┌─────────────┐    hooks=Stage0GateHooks(client)               │
│  │   Runner    │────────────────────────────────┐               │
│  │  .run()     │                                 │               │
│  └──────┬──────┘                                 │               │
│         │                                        │               │
│         ▼                                        ▼               │
│  ┌─────────────┐    on_tool_start()    ┌─────────────────┐      │
│  │    Agent    │──────────────────────▶│ Stage0GateHooks │      │
│  │  (tools=[]) │                       └────────┬────────┘      │
│  └──────┬──────┘                                │               │
│         │                                       ▼               │
│         │                              ┌─────────────────┐      │
│         │                              │  Stage0 /check  │      │
│         │                              │  (API call)     │      │
│         │                              └────────┬────────┘      │
│         │                                       │               │
│         │                    ┌──────────────────┼───────────┐   │
│         │                    │                  │           │   │
│         │              ALLOW │            DENY  │     DEFER │   │
│         │                    ▼                  ▼           ▼   │
│         │            ┌─────────────┐    ┌─────────────┐  ...    │
│         │            │ Execute     │    │ Raise       │         │
│         │            │ Tool        │    │ BlockedError│         │
│         │            └─────────────┘    └─────────────┘         │
│         │                    │                                   │
│         ▼                    ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Tracing (custom_span)                 │    │
│  │  - tool_name, verdict, request_id, policy_version        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Integration Points

### 1. Tools with Side Effect Declarations

```python
from agents import function_tool
from app.tools import TOOL_SIDE_EFFECTS

@function_tool
def dangerous_delete(file_path: str) -> str:
    """Delete a file - HIGH RISK operation."""
    return f"Deleted: {file_path}"

# Declare side effects for Stage0 validation
TOOL_SIDE_EFFECTS["dangerous_delete"] = ["data_deletion", "filesystem_modification"]
```

### 2. RunHooks for Tool Interception

```python
from agents import Agent, Runner
from app.stage0_hooks import Stage0GateHooks
from stage0 import Stage0Client

client = Stage0Client()
hooks = Stage0GateHooks(client)

agent = Agent(name="ProtectedAgent", tools=[...])

# Stage0 validates BEFORE each tool call
result = await Runner.run(agent, "Delete temp.log", hooks=hooks)
```

### 3. Tracing Integration

```python
from app.tracing import trace_stage0_decision

# Automatically called by Stage0GateHooks
# Records in OpenAI Agents SDK trace:
# - tool_name
# - verdict (ALLOW/DENY/DEFER)
# - request_id
# - policy_version
```

---

## Demo Scenarios

```bash
# Run hooks demo (no OpenAI key needed, uses mock Stage0)
python run_demo.py --hooks-only --mock --scenario all

# Run specific scenario
python run_demo.py --hooks-only --mock --scenario allow   # Safe lookup - ALLOWED
python run_demo.py --hooks-only --mock --scenario deny    # Dangerous delete - DENIED
python run_demo.py --hooks-only --mock --scenario defer   # Approval required - DEFERRED

# Run with live Stage0 API (requires STAGE0_API_KEY)
python run_demo.py --hooks-only --scenario all

# Run full agent demo (requires OPENAI_API_KEY)
python run_demo.py --mock --scenario all
```

### Expected Output

```
======================================================================
  Scenario: ALLOW - Safe informational query
======================================================================

Input: Search for documentation about Python async programming
Expected: ALLOW

Calling Stage0...

RESULT: Tool executed successfully
Output: Result 1: Documentation about 'Python async programming'...

Verdict: ALLOW (Expected: ALLOW)

======================================================================
  Scenario: DENY - Dangerous operation
======================================================================

Input: Delete the file /tmp/old_logs.txt
Expected: DENY

Calling Stage0...

RESULT: Tool execution BLOCKED by Stage0
Error: Stage0 DENY: Tool 'dangerous_delete' blocked...

Verdict: DENY (Expected: DENY)
```

---

## Project Structure

```
openai-agents-sdk-tool-gate/
├── app/
│   ├── __init__.py           # Module exports
│   ├── tools.py              # @function_tool definitions with side effects
│   ├── stage0_hooks.py       # RunHooks implementation for Stage0
│   ├── tracing.py            # custom_span helpers for decision logging
│   └── agent.py              # Agent factory functions
├── stage0/
│   ├── __init__.py
│   └── client.py             # Stage0 API client
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_safe_tool_allowed.py
│   ├── test_risky_tool_denied.py
│   ├── test_defer_path.py
│   └── test_mock_mode.py
├── examples/                  # Legacy examples (direct API)
├── run_demo.py               # Main demo entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Tool Categories

| Category | Tools | Stage0 Verdict | Side Effects |
|----------|-------|----------------|--------------|
| **Safe** | `safe_lookup`, `get_system_status` | ALLOW | None |
| **Dangerous** | `dangerous_delete`, `deploy_to_production`, `send_notification` | DENY | data_deletion, deploy, etc. |
| **Approval Required** | `approval_required_action` | DEFER | requires_approval |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_risky_tool_denied.py -v

# Run with coverage
pytest tests/ --cov=app --cov=stage0
```

---

## Key Concepts

### Why RunHooks?

OpenAI Agents SDK provides `RunHooks` as the official way to intercept lifecycle events. The `on_tool_start` callback fires BEFORE tool execution, making it the perfect integration point for Stage0 validation.

### Why Not Wrap Tools Individually?

You could wrap each tool function, but that:
1. Requires modifying every tool
2. Easy to forget on new tools
3. Duplicates validation logic

`RunHooks` provides centralized, consistent protection across all tools.

### What Gets Traced?

Every Stage0 decision is recorded in the trace with:
- `tool_name`: Which tool was checked
- `verdict`: ALLOW/DENY/DEFER
- `request_id`: For audit trail
- `policy_version`: Which policy made the decision
- `risk_score`: Risk assessment

View traces at https://platform.openai.com/traces

---

## Get Your API Key

1. Visit [signalpulse.org](https://signalpulse.org)
2. Create an account (free tier available)
3. Generate an API key
4. Add to `.env`:

```env
STAGE0_API_KEY=your_api_key_here
STAGE0_BASE_URL=https://api.signalpulse.org
```

---

## Version Stability

This project follows [Semantic Versioning](https://semver.org/). The current version is **1.0.0**.

### What to Pin

When using this repository as a reference or dependency:

```bash
# Clone a specific release
git clone --branch v1.0.0 https://github.com/Starlight143/openai-agents-sdk-tool-gate.git

# Or use a specific commit
git clone https://github.com/Starlight143/openai-agents-sdk-tool-gate.git
cd openai-agents-sdk-tool-gate
git checkout v1.0.0
```

### Stability Guarantees

| Component | Stability | Notes |
|-----------|-----------|-------|
| `Stage0GateHooks` | **Stable** | Public API locked for v1.x |
| `Stage0BlockedError` | **Stable** | Exception interface locked |
| `create_protected_agent()` | **Stable** | Factory function locked |
| Tool definitions | **Stable** | 6 tools with fixed side effects |
| `TOOL_SIDE_EFFECTS` | **Stable** | Registry format locked |
| Tracing helpers | **Stable** | `trace_stage0_decision()` locked |

### Breaking Changes Policy

- **Major version** (v2.0.0): Breaking changes to public APIs
- **Minor version** (v1.1.0): New features, backwards compatible
- **Patch version** (v1.0.1): Bug fixes, backwards compatible

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

See [LICENSE](LICENSE) for details.