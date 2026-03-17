# Stage0 Tool Gate for OpenAI Agents SDK

A minimal, production-ready example showing how to integrate [SignalPulse Stage0](https://signalpulse.org) runtime policy validation into your OpenAI Agents SDK project.

**Target audience**: Developers building AI agents who need to prevent autonomous agents from executing dangerous actions without approval.

---

## Problem Scenario

Your AI agent can helpfully research, analyze, and draft content. But what happens when it tries to:

- **Deploy** to production without approval
- **Publish** customer-facing content without review
- **Execute** shell commands that modify state
- **Keep retrying** a failing action indefinitely

Without a runtime guard, these actions execute silently. With Stage0, every execution intent is validated **before** the action happens.

### The Risk

```
User: "Help me investigate the production incident"

Agent WITHOUT Stage0:
1. [RESEARCH] Gather logs... ✓
2. [ANALYSIS] Identify root cause... ✓
3. [OUTPUT] Draft fix plan... ✓
4. [ACTION] Deploy hotfix to production... ✗ ALREADY EXECUTED

Agent WITH Stage0:
1. [RESEARCH] Gather logs... ✓ ALLOWED
2. [ANALYSIS] Identify root cause... ✓ ALLOWED
3. [OUTPUT] Draft fix plan... ✓ ALLOWED
4. [ACTION] Deploy hotfix to production... ✗ BLOCKED by Stage0
   Reason: SIDE_EFFECTS_NEED_GUARDRAILS - deploy requires approval
```

---

## Where Stage0 Sits (Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                      Your AI Agent                          │
│  (OpenAI Agents SDK, LangGraph, custom agent, etc.)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Before every tool call
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Stage0 /check API                        │
│  (https://api.signalpulse.org)                              │
│                                                             │
│  Input: goal, tools, side_effects, context                  │
│  Output: verdict (ALLOW/DENY/DEFER), reason, request_id     │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ALLOW │                   │ DENY/DEFER
                    ▼                   ▼
           ┌───────────────┐    ┌──────────────────┐
           │ Execute Tool  │    │ Block Execution  │
           │ Call          │    │ Log & Escalate   │
           └───────────────┘    └──────────────────┘
```

**Key principle**: Stage0 is NOT part of your agent. The agent cannot self-approve. All execution intent MUST be validated via external `/check` call.

---

## Quick Start (10-15 minutes)

### Prerequisites

- Python 3.10 or newer
- A Stage0 API key from [signalpulse.org](https://signalpulse.org)

### Installation

```bash
# Clone this repository
git clone https://github.com/Starlight143/openai-agents-sdk-tool-gate.git
cd openai-agents-sdk-tool-gate

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your STAGE0_API_KEY
```

### Run the Demo

```bash
# Run all examples (interactive mode)
python run_demo.py

# Run all examples without prompts (for CI, recordings)
python run_demo.py --auto

# Run specific example
python run_demo.py --example deny

# Run ALLOW example only
python run_demo.py --example allow

# Run DEFER example only
python run_demo.py --example defer
```

---

## Expected Output

### ALLOW Example (Safe Informational Query)

```
======================================================================
EXAMPLE: ALLOW Scenario - Safe Informational Query
======================================================================

Goal: Search for Python web framework documentation
Tools: web_search
Side effects: None
Constraints: informational only, no side effects

Calling Stage0 /check...

======================================================================
Stage0 Response
======================================================================

  Verdict:        ALLOW
  Decision:       GO
  Reason:         Informational query with no side effects
  Request ID:     req_abc123xyz
  Policy Version: 2024.01.01
  Risk Score:     0
  High Risk:      False

ACTION: Execute the tool call
The agent can now safely search for documentation.
```

### DENY Example (Dangerous Deployment)

```
======================================================================
EXAMPLE: DENY Scenario - Dangerous Deployment Action
======================================================================

Goal: Deploy a hotfix to production API gateway immediately
Tools: shell, kubectl
Side effects: deploy (HIGH RISK)
Context: No approval, production environment, automated request

Calling Stage0 /check...

======================================================================
Stage0 Response
======================================================================

  Verdict:        DENY
  Decision:       NO_GO
  Reason:         HIGH severity: SIDE_EFFECTS_NEED_GUARDRAILS
  Request ID:     req_def456uvw
  Policy Version: 2024.01.01
  Risk Score:     85
  High Risk:      True

  Issues:
    [HIGH] SIDE_EFFECTS_NEED_GUARDRAILS: Deploy side effect requires approval
    [HIGH] MISSING_APPROVAL: Production deployment requires human approval

ACTION: BLOCKED - Tool call denied by Stage0
The agent MUST NOT execute this deployment.
```

### DEFER Example (Loop Guard)

```
======================================================================
EXAMPLE: DEFER Scenario - Agent Loop Guard
======================================================================

Goal: Continue autonomous retries until the workflow succeeds
Tools: shell, recovery_script
Side effects: loop (repeated execution)
Context: Multiple retries already attempted, cost increasing

Calling Stage0 /check...

======================================================================
Stage0 Response
======================================================================

  Verdict:        ALLOW or DEFER
  Decision:       GO or DEFER
  Reason:         Review clarifying questions before continuing
  Request ID:     req_ghi789rst
  Policy Version: stage0-policy-pack@0.1.0

  Clarifying Questions:
    - What hard constraints must never be violated?

ACTION: Review clarifying questions before continuing
The agent should consider human checkpoint for loop scenarios.
```

**Note**: DEFER verdict depends on policy configuration and plan. Free tier may return ALLOW with clarifying questions instead of DEFER.

---

## Where to Find request_id and policy_version

These critical audit fields are in **every** Stage0 response:

```python
response = client.check_goal(...)

# Unique identifier for this request - store in your logs
print(f"request_id: {response.request_id}")
# Output: request_id: req_abc123xyz

# Which policy version made the decision - for audit trail
print(f"policy_version: {response.policy_version}")
# Output: policy_version: 2024.01.01

# Also available as policy_pack_version
print(f"policy_pack_version: {response.policy_pack_version}")
```

**Best practice**: Log `request_id` and `policy_version` with every tool call for audit traceability.

---

## Integration Code

The minimal integration pattern:

```python
from stage0 import Stage0Client, Verdict

# Initialize client (reads STAGE0_API_KEY from environment)
client = Stage0Client()

# Before executing any tool call with potential side effects
response = client.check_goal(
    goal="Deploy the hotfix to production",
    tools=["shell", "kubectl"],
    side_effects=["deploy"],  # Be honest about risks
    context={
        "environment": "production",
        "approval_status": "pending",
        "actor_role": "incident_bot",
    },
)

# Check the verdict
if response.verdict == Verdict.ALLOW:
    # Safe to execute
    result = execute_tool_call()
elif response.verdict == Verdict.DEFER:
    # Need human review
    request_human_approval(response.defer_questions)
else:  # DENY
    # Block and log
    log_blocked_action(
        request_id=response.request_id,
        reason=response.reason,
        policy_version=response.policy_version,
    )
```

---

## Request/Response Contract

### Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `goal` | string | What you're trying to accomplish |
| `success_criteria` | string[] | What success looks like |
| `constraints` | string[] | Any constraints to apply |
| `tools` | string[] | Tools you plan to use |
| `side_effects` | string[] | Potential side effects (deploy, publish, etc.) |
| `context` | object | Runtime context (environment, approval, etc.) |

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | enum | **The action gate**: ALLOW, DENY, or DEFER |
| `decision` | enum | Decision posture: GO, NO_GO, DEFER, ERROR |
| `reason` | string | Why this decision was made |
| `request_id` | string | **Unique ID** - log this for audits |
| `policy_version` | string | **Policy version** - for audit trail |
| `risk_score` | int | Risk score (0-100) |
| `high_risk` | bool | Whether this is considered high risk |
| `issues` | array | List of detected issues with severity |

---

## Common Side Effects to Declare

When calling Stage0, be honest about potential side effects:

| Side Effect | When to Use |
|-------------|-------------|
| `deploy` | Deploying code, containers, or infrastructure |
| `publish` | Publishing content, posts, or public statements |
| `send_email` | Sending emails or notifications |
| `payment` | Processing payments or refunds |
| `data_modification` | Modifying database records |
| `external_api` | Calling external APIs that may have side effects |
| `loop` | Repeated execution or retry loops |
| `shell` | Executing shell commands |

---

## Project Structure

```
openai-agents-sdk-tool-gate/
├── README.md           # This file
├── .env.example        # Environment template
├── requirements.txt    # Python dependencies
├── run_demo.py         # Main entry point
├── stage0/
│   ├── __init__.py
│   └── client.py       # Stage0 API client
└── examples/
    ├── __init__.py
    ├── allow_example.py    # ALLOW scenario
    └── deny_example.py     # DENY/DEFER scenarios
```

---

## Other Framework Quickstarts

SignalPulse provides quickstart examples for major agent frameworks:

| Framework | Repository |
|-----------|------------|
| OpenAI Agents SDK | This repo |
| Custom/General | [stage0-agent-runtime-guard](https://github.com/Starlight143/stage0-agent-runtime-guard) |

---

## Get Your API Key

1. Visit [signalpulse.org](https://signalpulse.org)
2. Create an account
3. Subscribe to a plan (free tier available)
4. Generate an API key
5. Add it to your `.env` file:

```env
STAGE0_API_KEY=your_api_key_here
STAGE0_BASE_URL=https://api.signalpulse.org
```

---

## Support

- Documentation: [signalpulse.org/docs](https://signalpulse.org/docs)
- Issues: [GitHub Issues](https://github.com/Starlight143/openai-agents-sdk-tool-gate/issues)

---

## License

See [LICENSE](LICENSE) for details.