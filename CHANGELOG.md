# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-03-23

### Added

- **Stage0GateHooks**: `RunHooks` implementation for tool authorization before execution
  - `on_tool_start()` intercepts each tool call and validates with Stage0 API
  - Configurable `raise_on_block`, `log_decisions`, `fail_safe_deny` options
  - Async-safe via `asyncio.to_thread()` for non-blocking API calls

- **Tools**: 6 `@function_tool` decorated tools with side effect declarations
  - Safe tools: `safe_lookup`, `get_system_status` (read-only, always ALLOW)
  - Dangerous tools: `dangerous_delete`, `deploy_to_production`, `send_notification` (side effects, may DENY)
  - Approval-required tools: `approval_required_action` (requires human review, DEFER)

- **Tracing**: Integration with OpenAI Agents SDK `custom_span`
  - Records `tool_name`, `verdict`, `request_id`, `policy_version`, `risk_score`
  - `trace_stage0_decision()` and `trace_tool_execution()` helpers

- **Agent Factory Functions**:
  - `create_protected_agent()` - Full agent with all tools
  - `create_safe_agent()` - Safe-only agent (read-only operations)
  - `create_demo_agent()` - Demo agent for showcasing Stage0 blocking

- **Error Handling**:
  - `Stage0BlockedError` exception with `tool_name`, `verdict`, `reason`, `request_id`, `policy_version`
  - Graceful degradation on API errors with `fail_safe_deny` option
  - Tracing errors don't break tool execution

- **Testing**: 30 comprehensive tests
  - `test_safe_tool_allowed.py` - ALLOW scenario tests
  - `test_risky_tool_denied.py` - DENY scenario tests
  - `test_defer_path.py` - DEFER scenario tests
  - `test_mock_mode.py` - Mock mode tests
  - `test_error_handling.py` - Error handling tests

- **Demo Script**: `run_demo.py` with multiple modes
  - `--hooks-only` - Test hooks directly without running agent
  - `--mock` - Use mock Stage0 hooks (no API key required)
  - `--scenario` - Run specific scenario (allow/deny/defer/all)
  - `--auto` - Run without pause prompts

- **Documentation**:
  - `AGENTS.md` - Agent architecture and integration documentation
  - Updated `README.md` with architecture diagrams and usage examples
  - `.env.example` with required environment variables

### Changed

- **requirements.txt**: Added `openai-agents>=0.0.2`, `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`

### Project Structure

```
openai-agents-sdk-tool-gate/
├── app/
│   ├── __init__.py           # Module exports
│   ├── tools.py              # @function_tool definitions
│   ├── stage0_hooks.py       # RunHooks implementation
│   ├── tracing.py            # custom_span helpers
│   └── agent.py              # Agent factory functions
├── stage0/
│   ├── __init__.py
│   └── client.py             # Stage0 API client
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_safe_tool_allowed.py
│   ├── test_risky_tool_denied.py
│   ├── test_defer_path.py
│   ├── test_mock_mode.py
│   └── test_error_handling.py
├── examples/                 # Legacy examples
├── run_demo.py
├── requirements.txt
├── .env.example
├── AGENTS.md
├── CHANGELOG.md
└── README.md
```

## [0.1.0] - 2025-03-17

### Added

- Initial release with basic Stage0 client
- Example scripts for ALLOW, DENY, DEFER scenarios
- Basic README and project setup

[1.0.0]: https://github.com/Starlight143/openai-agents-sdk-tool-gate/releases/tag/v1.0.0
[0.1.0]: https://github.com/Starlight143/openai-agents-sdk-tool-gate/releases/tag/v0.1.0