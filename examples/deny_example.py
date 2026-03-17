"""Example: DENY scenario - Dangerous deployment action.

This example demonstrates a tool call that should be DENIED by Stage0.
The goal involves deploying to production without proper approval.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from stage0 import Stage0Client, Verdict, Decision

load_dotenv()


def check_api_key() -> bool:
    """Check if Stage0 API key is configured."""
    api_key = os.getenv("STAGE0_API_KEY")
    return bool(api_key and api_key != "your_api_key_here")


def run_deny_example():
    """Run a DENY scenario - dangerous deployment without approval.

    This simulates an agent that wants to deploy to production.
    Since this is a high-risk action with side effects and no approval,
    Stage0 should return DENY.
    """
    print("=" * 70)
    print("EXAMPLE: DENY Scenario - Dangerous Deployment Action")
    print("=" * 70)
    print()

    if not check_api_key():
        print("ERROR: STAGE0_API_KEY not configured.")
        print("Set your API key in .env or environment variables.")
        print()
        print("Simulating DENY response...")
        print()
        run_simulated_deny()
        return

    print("Goal: Deploy a hotfix to production API gateway")
    print("Tools: shell, kubectl")
    print("Side effects: deploy (HIGH RISK)")
    print("Context: No approval, production environment, automated request")
    print()

    try:
        client = Stage0Client()
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    print("Calling Stage0 /check...")
    print()

    response = client.check_goal(
        goal="Deploy the hotfix to production API gateway immediately",
        success_criteria=[
            "Hotfix is deployed to production",
            "API gateway is running new version",
        ],
        constraints=[],
        tools=["shell", "kubectl", "argo_cd"],
        side_effects=["deploy", "production_change"],
        context={
            "run_id": "incident-response-001",
            "actor_role": "incident_bot",
            "approval_status": "missing",
            "approved_by": None,
            "approved_at": None,
            "environment": "production",
            "request_channel": "api",
            "target_resources": ["api-gateway-prod"],
            "current_tool": "kubectl",
        },
    )

    print_response(response)

    if response.verdict == Verdict.DENY:
        print()
        print("ACTION: BLOCKED - Tool call denied by Stage0")
        print("The agent MUST NOT execute this deployment.")
        print()
        print("Required actions:")
        print("  1. Get human approval before deployment")
        print("  2. Run in staging environment first")
        print("  3. Follow change management process")
    elif response.verdict == Verdict.DEFER:
        print()
        print("ACTION: DEFERRED - Human review required")
        print("The agent should wait for human confirmation.")
        if response.defer_questions:
            print()
            print("Questions to resolve:")
            for question in response.defer_questions:
                print(f"  - {question}")
    else:
        print()
        print(f"UNEXPECTED: Got {response.verdict.value} instead of DENY/DEFER")

    return response


def run_simulated_deny():
    """Simulate a DENY response when no API key is available."""
    print("Simulated Stage0 Response:")
    print("-" * 70)
    print("  verdict: DENY")
    print("  decision: NO_GO")
    print("  reason: HIGH severity: SIDE_EFFECTS_NEED_GUARDRAILS")
    print("          - 'deploy' side effect without approval")
    print("          - 'production_change' without change management")
    print("  request_id: sim_deny_001")
    print("  policy_version: 2024.01.01")
    print("  risk_score: 85")
    print("  high_risk: True")
    print("-" * 70)
    print()
    print("Issues detected:")
    print("  [HIGH] SIDE_EFFECTS_NEED_GUARDRAILS: Deploy side effect requires")
    print("         explicit approval and change management process")
    print("  [HIGH] MISSING_APPROVAL: Production deployment requires human approval")
    print("  [MEDIUM] ENVIRONMENT_RISK: Direct production access without staging")
    print()
    print("ACTION: BLOCKED - Tool call denied by Stage0")
    print("The agent MUST NOT execute this deployment.")


def run_defer_example():
    """Run a DEFER scenario - loop-like behavior needs review.

    This simulates an agent that wants to keep retrying an action.
    Stage0 should return DEFER to request human checkpoint.
    """
    print("=" * 70)
    print("EXAMPLE: DEFER Scenario - Agent Loop Guard")
    print("=" * 70)
    print()

    if not check_api_key():
        print("ERROR: STAGE0_API_KEY not configured.")
        print("Simulating DEFER response...")
        print()
        run_simulated_defer()
        return

    print("Goal: Continue autonomous retries until workflow succeeds")
    print("Tools: shell, recovery_script")
    print("Side effects: loop (repeated execution)")
    print("Context: Multiple retries already attempted, cost increasing")
    print()

    try:
        client = Stage0Client()
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    print("Calling Stage0 /check...")
    print()

    response = client.check_goal(
        goal="Continue autonomous retries until the workflow succeeds",
        success_criteria=[
            "Workflow eventually succeeds",
            "No human intervention needed",
        ],
        constraints=[],
        tools=["shell", "recovery_script"],
        side_effects=["loop", "repeated_tool_call"],
        context={
            "run_id": "recovery-workflow-001",
            "current_iteration": 5,
            "elapsed_seconds": 180,
            "recent_tools": ["recovery_script", "recovery_script", "recovery_script"],
            "cumulative_cost_usd": 1.25,
            "request_channel": "api",
        },
    )

    print_response(response)

    if response.verdict == Verdict.DEFER:
        print()
        print("ACTION: DEFERRED - Human checkpoint required")
        print("The agent should NOT continue retrying autonomously.")
        print()
        print("Reasons:")
        print("  - Loop threshold reached")
        print("  - Cost and time are growing")
        print("  - Same tool path repeated without success")
        if response.defer_questions:
            print()
            print("Questions to resolve:")
            for question in response.defer_questions:
                print(f"  - {question}")
    elif response.verdict == Verdict.DENY:
        print()
        print("ACTION: BLOCKED - Tool call denied by Stage0")
    else:
        print()
        print(f"UNEXPECTED: Got {response.verdict.value} instead of DEFER")

    return response


def run_simulated_defer():
    """Simulate a DEFER response when no API key is available."""
    print("Simulated Stage0 Response:")
    print("-" * 70)
    print("  verdict: DEFER")
    print("  decision: DEFER")
    print("  reason: Loop threshold reached - human checkpoint required")
    print("  request_id: sim_defer_001")
    print("  policy_version: 2024.01.01")
    print("-" * 70)
    print()
    print("Context indicators:")
    print("  - current_iteration: 5 (exceeds threshold)")
    print("  - elapsed_seconds: 180s")
    print("  - cumulative_cost_usd: $1.25")
    print("  - recent_tools: [recovery_script x3]")
    print()
    print("ACTION: DEFERRED - Human checkpoint required")
    print("The agent should NOT continue retrying autonomously.")


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

    if response.defer_questions:
        print()
        print("  Defer Questions:")
        for question in response.defer_questions:
            print(f"    - {question}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run DENY or DEFER example")
    parser.add_argument(
        "--defer",
        action="store_true",
        help="Run DEFER scenario instead of DENY",
    )
    args = parser.parse_args()

    if args.defer:
        run_defer_example()
    else:
        run_deny_example()
