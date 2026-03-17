#!/usr/bin/env python3
"""Main demo runner for openai-agents-sdk-tool-gate.

This script runs the ALLOW and DENY/DEFER examples to demonstrate
how Stage0 protects AI agents from executing dangerous actions.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()


def print_header(title: str):
    """Print a formatted header."""
    width = 70
    print()
    print("=" * width)
    print(title.center(width))
    print("=" * width)
    print()


def print_section(title: str):
    """Print a section divider."""
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
        "--example",
        choices=["allow", "deny", "defer", "all"],
        default="all",
        help="Which example to run. Default: all",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without pause prompts (for CI, recordings, scripted tests).",
    )
    return parser.parse_args()


def check_setup():
    """Check if the environment is properly set up."""
    issues = []

    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        issues.append(".env file not found. Copy .env.example to .env")

    api_key = os.getenv("STAGE0_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        issues.append("STAGE0_API_KEY not configured in .env")

    return issues


def main():
    args = parse_args()

    print_header("Stage0 Tool Gate Demo for OpenAI Agents SDK")
    print("This demo shows how Stage0 protects AI agents from dangerous actions.")
    print()
    print("Examples available:")
    print("  - allow: Safe informational query (should be ALLOWED)")
    print("  - deny:  Dangerous deployment action (should be DENIED)")
    print("  - defer: Loop-like behavior (should be DEFERRED)")
    print()

    issues = check_setup()
    if issues:
        print("NOTE: Setup issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("The demo will run with simulated Stage0 responses.")
        print(
            "Configure a real API key from https://signalpulse.org for live validation."
        )
        print()

    from examples.allow_example import run_allow_example
    from examples.deny_example import run_deny_example, run_defer_example

    if args.example in ("allow", "all"):
        run_allow_example()
        if args.example == "all" and not args.auto:
            print_section("Press Enter to continue to DENY example...")
            input()

    if args.example in ("deny", "all"):
        run_deny_example()
        if args.example == "all" and not args.auto:
            print_section("Press Enter to continue to DEFER example...")
            input()

    if args.example in ("defer", "all"):
        run_defer_example()

    print_section("Summary")
    print("""
Stage0 Tool Gate Integration Points:

1. BEFORE any tool call with side effects:
   - Call Stage0 /check with the execution intent
   - Wait for verdict (ALLOW/DENY/DEFER)
   - Only execute if verdict is ALLOW

2. Key response fields to log:
   - request_id: Unique identifier for audit trail
   - policy_version: Which policy version made the decision
   - verdict: The action gate (ALLOW/DENY/DEFER)
   - reason: Why the decision was made

3. Integration pattern:
   ```python
   from stage0 import Stage0Client, Verdict

   client = Stage0Client()

   # Before executing a tool call
   response = client.check_goal(
       goal="Your tool call description",
       tools=["tool_name"],
       side_effects=["deploy", "publish"],  # Be honest about risks
       context={"environment": "production"},
   )

   if response.verdict != Verdict.ALLOW:
       raise RuntimeError(f"Blocked: {response.reason}")

   # Safe to execute the tool call
   result = execute_tool_call()
   ```

4. Where Stage0 sits in your architecture:
   - Between your agent's decision and tool execution
   - NOT inside the agent - the agent cannot self-approve
   - External authority that the agent must respect

Get your API key: https://signalpulse.org
""")


if __name__ == "__main__":
    main()
