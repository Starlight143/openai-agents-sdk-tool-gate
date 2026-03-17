"""Example: ALLOW scenario - Safe informational query.

This example demonstrates a tool call that should be ALLOWED by Stage0.
The goal is informational research with no side effects.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from stage0 import Stage0Client, Verdict

load_dotenv()


def check_api_key() -> bool:
    """Check if Stage0 API key is configured."""
    api_key = os.getenv("STAGE0_API_KEY")
    return bool(api_key and api_key != "your_api_key_here")


def run_allow_example():
    """Run an ALLOW scenario - safe informational query.

    This simulates an agent that wants to search for documentation.
    Since there are no side effects, Stage0 should return ALLOW.
    """
    print("=" * 70)
    print("EXAMPLE: ALLOW Scenario - Safe Informational Query")
    print("=" * 70)
    print()

    if not check_api_key():
        print("ERROR: STAGE0_API_KEY not configured.")
        print("Set your API key in .env or environment variables.")
        print()
        print("Simulating ALLOW response...")
        print()
        run_simulated_allow()
        return

    print("Goal: Search for Python web framework documentation")
    print("Tools: web_search")
    print("Side effects: None")
    print("Constraints: informational only, no side effects")
    print()

    try:
        client = Stage0Client()
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    print("Calling Stage0 /check...")
    print()

    response = client.check_goal(
        goal="Search for Python web framework documentation and best practices",
        success_criteria=[
            "Return relevant documentation links",
            "Provide informational summary only",
        ],
        constraints=[
            "informational only",
            "no side effects",
            "no actionable recommendations",
        ],
        tools=["web_search", "documentation_reader"],
        side_effects=[],
        context={
            "actor_role": "developer",
            "environment": "development",
            "request_channel": "cli",
        },
    )

    print_response(response)

    if response.verdict == Verdict.ALLOW:
        print()
        print("ACTION: Execute the tool call")
        print("The agent can now safely search for documentation.")
    else:
        print()
        print(f"UNEXPECTED: Got {response.verdict.value} instead of ALLOW")

    return response


def run_simulated_allow():
    """Simulate an ALLOW response when no API key is available."""
    print("Simulated Stage0 Response:")
    print("-" * 70)
    print("  verdict: ALLOW")
    print("  decision: GO")
    print("  reason: Informational query with no side effects")
    print("  request_id: sim_allow_001")
    print("  policy_version: 2024.01.01")
    print("-" * 70)
    print()
    print("ACTION: Execute the tool call")
    print("The agent can now safely search for documentation.")


def print_response(response):
    """Print the Stage0 response in a readable format."""
    print("=" * 70)
    print("Stage0 Response")
    print("=" * 70)
    print()
    print(f"  Verdict:        {response.verdict.value}")
    print(f"  Decision:       {response.decision.value}")
    print(f"  Reason:         {response.reason}")
    print(f"  Request ID:     {response.request_id}")
    print(
        f"  Policy Version: {response.policy_version or response.policy_pack_version}"
    )
    print(f"  Risk Score:     {response.risk_score}")
    print(f"  High Risk:      {response.high_risk}")

    if response.constraints_applied:
        print()
        print("  Constraints Applied:")
        for constraint in response.constraints_applied:
            print(f"    - {constraint}")

    if response.issues:
        print()
        print("  Issues:")
        for issue in response.issues:
            severity = issue.get("severity", "UNKNOWN")
            code = issue.get("code", "UNKNOWN")
            message = issue.get("message", "")
            print(f"    [{severity}] {code}: {message}")

    if response.guardrails:
        print()
        print("  Guardrails:")
        for guardrail in response.guardrails:
            print(f"    - {guardrail}")


if __name__ == "__main__":
    run_allow_example()
