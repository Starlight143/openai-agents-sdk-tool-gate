#!/usr/bin/env python3
"""Main demo runner for openai-agents-sdk-tool-gate.

This script demonstrates Stage0 tool gate integration with OpenAI Agents SDK.

Run modes:
  --mode sdk     Use real OpenAI Agents SDK with Agent/Runner (default)
  --mode legacy  Use legacy examples (direct Stage0 API calls)

Scenarios:
  --scenario allow  Safe lookup (should be ALLOWED)
  --scenario deny   Dangerous delete (should be DENIED)
  --scenario defer  Approval required (should be DEFERRED)
  --scenario all    Run all scenarios (default)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()


def print_header(title: str) -> None:
    width = 70
    print()
    print("=" * width)
    print(title.center(width))
    print("=" * width)
    print()


def print_section(title: str) -> None:
    print()
    print("-" * 70)
    print(f"  {title}")
    print("-" * 70)
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Stage0 Tool Gate demo for OpenAI Agents SDK."
    )
    parser.add_argument(
        "--mode",
        choices=["sdk", "legacy"],
        default="sdk",
        help="Demo mode: sdk (Agent/Runner) or legacy (direct API). Default: sdk",
    )
    parser.add_argument(
        "--scenario",
        choices=["allow", "deny", "defer", "all"],
        default="all",
        help="Which scenario to run. Default: all",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without pause prompts (for CI, recordings).",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock Stage0 hooks (no API key required).",
    )
    parser.add_argument(
        "--hooks-only",
        action="store_true",
        help="Test Stage0 hooks directly without running agent (no OpenAI key needed).",
    )
    return parser.parse_args()


def check_sdk_installed() -> bool:
    try:
        import agents

        return True
    except ImportError:
        return False


def check_stage0_key() -> bool:
    api_key = os.getenv("STAGE0_API_KEY")
    return bool(api_key and api_key != "your_api_key_here")


async def run_hooks_demo(args: argparse.Namespace) -> None:
    from unittest.mock import MagicMock

    from app.stage0_hooks import (
        MockStage0GateHooks,
        Stage0BlockedError,
        Stage0GateHooks,
    )
    from stage0 import Stage0Client

    print_header("Stage0 Hooks Demo (No OpenAI Key Required)")

    use_mock = args.mock or not check_stage0_key()

    if use_mock:
        print("Using MOCK Stage0 hooks")
        hooks = MockStage0GateHooks()
    else:
        print("Using LIVE Stage0 hooks with Stage0 API key")
        client = Stage0Client()
        hooks = Stage0GateHooks(client)

    print()
    print("This demo tests Stage0 hooks directly without running a full agent.")
    print("It demonstrates how tools are validated BEFORE execution.")
    print()

    mock_context = MagicMock()
    mock_agent = MagicMock()
    mock_agent.name = "DemoAgent"

    test_tools = [
        {
            "name": "safe_lookup",
            "expected": "ALLOW",
            "description": "Safe read-only tool",
        },
        {
            "name": "dangerous_delete",
            "expected": "DENY",
            "description": "Dangerous deletion tool",
        },
        {
            "name": "approval_required_action",
            "expected": "DEFER",
            "description": "Approval-required tool",
        },
    ]

    to_run = (
        test_tools
        if args.scenario == "all"
        else [
            t
            for t in test_tools
            if t["name"].startswith(args.scenario)
            or (args.scenario == "deny" and t["expected"] == "DENY")
            or (args.scenario == "defer" and t["expected"] == "DEFER")
            or (args.scenario == "allow" and t["expected"] == "ALLOW")
        ]
    )

    if not to_run:
        to_run = test_tools

    results = []

    for tool_info in to_run:
        tool_name = tool_info["name"]
        expected = tool_info["expected"]
        description = tool_info["description"]

        print_section(f"Testing: {tool_name} - {description}")
        print(f"Expected verdict: {expected}")
        print()

        mock_tool = MagicMock()
        mock_tool.name = tool_name

        try:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)
            actual = "ALLOW"
            print("RESULT: Tool execution ALLOWED")
        except Stage0BlockedError as e:
            actual = e.verdict.value
            print(f"RESULT: Tool execution BLOCKED")
            print(f"  Verdict: {e.verdict.value}")
            print(f"  Reason: {e.reason}")
            print(f"  Request ID: {e.request_id}")
            print(f"  Policy Version: {e.policy_version}")
        except Exception as e:
            actual = "ERROR"
            print(f"RESULT: Unexpected error - {e}")

        passed = actual == expected or (
            expected == "DENY" and actual in ["DENY", "DEFER"]
        )
        results.append(
            {
                "tool": tool_name,
                "expected": expected,
                "actual": actual,
                "passed": passed,
            }
        )

        print()
        print(f"Verdict: {actual} (Expected: {expected})")

        if not args.auto:
            input("Press Enter to continue...")

    print_header("Summary")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"Tests: {passed}/{total} passed")
    print()

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['tool']}: expected {r['expected']}, got {r['actual']}")

    print()
    print("How it works:")
    print("  1. Agent decides to call a tool")
    print("  2. Stage0GateHooks.on_tool_start() is called BEFORE execution")
    print("  3. Stage0 validates the execution intent")
    print("  4. If DENY/DEFER, tool is blocked (Stage0BlockedError raised)")
    print("  5. If ALLOW, tool executes normally")


async def run_sdk_demo(args: argparse.Namespace) -> None:
    from agents import Runner, trace

    from app.agent import create_demo_agent
    from app.stage0_hooks import (
        MockStage0GateHooks,
        Stage0BlockedError,
        Stage0GateHooks,
    )
    from stage0 import Stage0Client

    print_header("OpenAI Agents SDK Integration Demo")

    use_mock = args.mock or not check_stage0_key()

    if use_mock:
        print("Using MOCK Stage0 hooks (no API key required)")
        hooks = MockStage0GateHooks()
    else:
        print("Using LIVE Stage0 hooks with API key")
        client = Stage0Client()
        hooks = Stage0GateHooks(client)

    print()

    agent = create_demo_agent()

    scenarios = {
        "allow": {
            "input": "Search for documentation about Python async programming",
            "expected": "ALLOW",
            "description": "Safe informational query using safe_lookup tool",
        },
        "deny": {
            "input": "Delete the file /tmp/old_logs.txt",
            "expected": "DENY",
            "description": "Dangerous operation using dangerous_delete tool",
        },
        "defer": {
            "input": "Process a refund for order #12345",
            "expected": "DEFER",
            "description": "Sensitive operation using approval_required_action tool",
        },
    }

    to_run = [args.scenario] if args.scenario != "all" else list(scenarios.keys())

    results = []

    for scenario_name in to_run:
        if scenario_name not in scenarios:
            continue

        scenario = scenarios[scenario_name]

        print_section(f"Scenario: {scenario_name.upper()} - {scenario['description']}")
        print(f"Input: {scenario['input']}")
        print(f"Expected: {scenario['expected']}")
        print()

        with trace(f"demo_{scenario_name}"):
            try:
                result = await Runner.run(
                    agent,
                    scenario["input"],
                    hooks=hooks,
                )
                print("RESULT: Tool executed successfully")
                print(f"Output: {result.final_output[:200]}...")
                actual = "ALLOW"
            except Stage0BlockedError as e:
                print("RESULT: Tool execution BLOCKED by Stage0")
                print(f"  Verdict: {e.verdict.value}")
                print(f"  Reason: {e.reason}")
                print(f"  Request ID: {e.request_id}")
                actual = e.verdict.value
            except Exception as e:
                print("RESULT: Unexpected error")
                print(f"  Error: {e}")
                actual = "ERROR"

        results.append(
            {
                "scenario": scenario_name,
                "expected": scenario["expected"],
                "actual": actual,
                "passed": actual == scenario["expected"]
                or (scenario["expected"] == "DENY" and actual in ["DENY", "DEFER"]),
            }
        )

        print()
        print(f"Verdict: {actual} (Expected: {scenario['expected']})")

        if not args.auto and scenario_name != to_run[-1]:
            print()
            input("Press Enter to continue...")

    print_header("Summary")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"Scenarios: {passed}/{total} passed")
    print()

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(
            f"  [{status}] {r['scenario']}: expected {r['expected']}, got {r['actual']}"
        )

    print()
    print("Key Integration Points:")
    print("  1. Stage0GateHooks intercepts on_tool_start BEFORE execution")
    print("  2. Stage0 client validates execution intent via /check API")
    print("  3. request_id and policy_version are recorded in traces")
    print("  4. DENY/DEFER verdicts prevent tool execution")


def run_legacy_demo(args: argparse.Namespace) -> None:
    from examples.allow_example import run_allow_example
    from examples.deny_example import run_defer_example, run_deny_example

    print_header("Legacy Demo (Direct Stage0 API)")

    if args.scenario in ("allow", "all"):
        run_allow_example()
        if args.scenario == "all" and not args.auto:
            print_section("Press Enter to continue...")
            input()

    if args.scenario in ("deny", "all"):
        run_deny_example()
        if args.scenario == "all" and not args.auto:
            print_section("Press Enter to continue...")
            input()

    if args.scenario in ("defer", "all"):
        run_defer_example()


def main() -> None:
    args = parse_args()

    if args.hooks_only:
        asyncio.run(run_hooks_demo(args))
        return

    if args.mode == "sdk":
        if not check_sdk_installed():
            print("ERROR: openai-agents package not installed.")
            print("Install with: pip install openai-agents")
            print()
            print("Falling back to legacy mode...")
            run_legacy_demo(args)
            return

        asyncio.run(run_sdk_demo(args))
    else:
        run_legacy_demo(args)


if __name__ == "__main__":
    main()
