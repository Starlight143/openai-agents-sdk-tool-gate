"""Stage0 API client for runtime policy validation.

This client tracks the SignalPulse Stage0 contract, including
runtime context fields, request tracing, and richer decision payloads.

Stage0 is the runtime policy authority that validates execution intent
before AI agents can execute tool calls with side effects.
"""

import os
import uuid
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class Decision(Enum):
    """Stage0 decision types."""

    GO = "GO"
    NO_GO = "NO_GO"
    DEFER = "DEFER"
    ERROR = "ERROR"


class Verdict(Enum):
    """Stage0 verdict types - the action gate you should enforce."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"


@dataclass
class CostEstimate:
    """Optional cost estimate returned by Stage0."""

    currency: str = "USD"
    min: float = 0.0
    max: float = 0.0
    assumptions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CostEstimate":
        """Parse a cost estimate from an API payload."""
        return cls(
            currency=str(data.get("currency", "USD") or "USD"),
            min=_safe_float(data.get("min"), 0.0),
            max=_safe_float(data.get("max"), 0.0),
            assumptions=[str(item) for item in (data.get("assumptions") or [])],
        )


@dataclass
class PolicyResponse:
    """Response from a Stage0 policy check.

    Key fields:
    - verdict: The action gate (ALLOW/DENY/DEFER) - this is what you enforce
    - decision: The decision posture (GO/NO_GO/DEFER/ERROR)
    - request_id: Store this in your logs for audit traceability
    - policy_version: Track which policy version made the decision
    """

    verdict: Verdict
    reason: str
    constraints_applied: list[str]
    raw_response: dict[str, Any]
    decision: Decision = Decision.ERROR
    task_hash: str = ""
    risk_score: int = 0
    high_risk: bool = False
    value_risk: int = 0
    waste_risk: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)
    defer_questions: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    guardrail_checks: dict[str, Any] = field(default_factory=dict)
    value_findings: list[str] = field(default_factory=list)
    cost_estimate: Optional[CostEstimate] = None
    request_id: str = ""
    policy_pack_version: str = ""
    policy_version: str = ""
    timestamp: float = 0.0
    evaluated_at: float = 0.0
    decision_trace_summary: str = ""
    cached: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyResponse":
        """Parse policy response from an API response body."""
        verdict = _parse_verdict(data.get("verdict", "DENY"))
        decision = _parse_decision(data.get("decision", "ERROR"))
        issues = _ensure_dict_list(data.get("issues"))
        clarifying = [str(item) for item in (data.get("clarifying_questions") or [])]
        defer_questions = [
            str(item) for item in (data.get("defer_questions") or clarifying)
        ]
        constraints = [str(item) for item in (data.get("constraints_applied") or [])]
        policy_pack_version = str(
            data.get("policy_pack_version") or data.get("policy_version") or ""
        )
        policy_version = str(data.get("policy_version") or policy_pack_version)
        timestamp = _safe_float(data.get("timestamp"), 0.0)
        evaluated_at = _safe_float(data.get("evaluated_at"), timestamp)
        decision_trace_summary = str(data.get("decision_trace_summary") or "")

        reason = data.get("reason")
        if not reason and issues:
            issue_messages = [
                f"{item.get('code', 'UNKNOWN')}: {item.get('message', '')}"
                for item in issues
            ]
            reason = "; ".join(issue_messages)
        if not reason and decision_trace_summary:
            reason = decision_trace_summary
        if not reason:
            reason = "No reason provided"

        cost_estimate_payload = data.get("cost_estimate")
        cost_estimate = None
        if isinstance(cost_estimate_payload, dict):
            cost_estimate = CostEstimate.from_dict(cost_estimate_payload)

        return cls(
            verdict=verdict,
            reason=str(reason),
            constraints_applied=constraints,
            raw_response=data,
            decision=decision,
            task_hash=str(data.get("task_hash", "") or ""),
            risk_score=_safe_int(data.get("risk_score"), 0),
            high_risk=bool(data.get("high_risk", False)),
            value_risk=_safe_int(data.get("value_risk"), 0),
            waste_risk=_safe_int(data.get("waste_risk"), 0),
            issues=issues,
            clarifying_questions=clarifying,
            defer_questions=defer_questions,
            guardrails=[str(item) for item in (data.get("guardrails") or [])],
            guardrail_checks=_ensure_dict(data.get("guardrail_checks")),
            value_findings=[str(item) for item in (data.get("value_findings") or [])],
            cost_estimate=cost_estimate,
            request_id=str(data.get("request_id", "") or ""),
            policy_pack_version=policy_pack_version,
            policy_version=policy_version,
            timestamp=timestamp,
            evaluated_at=evaluated_at,
            decision_trace_summary=decision_trace_summary,
            cached=bool(data.get("cached", False)),
            meta=_ensure_dict(data.get("meta")),
        )

    def has_issues(self) -> bool:
        """Check if there are any issues detected."""
        return bool(self.issues)

    def get_issue_severities(self) -> list[str]:
        """Return the severity values from every issue."""
        return [str(issue.get("severity", "UNKNOWN")) for issue in self.issues]

    def has_high_severity_issues(self) -> bool:
        """Check if there are any HIGH severity issues."""
        return "HIGH" in self.get_issue_severities()


@dataclass
class ExecutionIntent:
    """Represents an execution intent to be validated by Stage0.

    This is what you send to Stage0 before executing a tool call.
    The goal is to describe WHAT you're about to do so Stage0 can
    decide if it's allowed.

    Key fields:
    - goal: What you're trying to accomplish
    - tools: What tools you plan to use
    - side_effects: What side effects this might have (publish, deploy, etc.)
    - context: Runtime context (actor_role, environment, approval_status, etc.)
    """

    goal: str
    success_criteria: list[str]
    constraints: list[str]
    tools: list[str]
    side_effects: list[str]
    context: dict[str, Any] = field(default_factory=dict)
    pro: bool = False
    policy_pack_version: str = ""
    debug_store_input: bool = False

    def to_request_body(self) -> dict[str, Any]:
        """Convert the execution intent into the API request format."""
        return {
            "goal": self.goal,
            "success_criteria": self.success_criteria,
            "constraints": self.constraints,
            "tools": self.tools,
            "side_effects": self.side_effects,
            "context": self.context,
            "pro": self.pro,
            "policy_pack_version": self.policy_pack_version,
            "debug_store_input": self.debug_store_input,
        }


class Stage0Client:
    """Client for Stage0 runtime policy validation.

    Stage0 is the runtime policy authority and must be treated as
    the final decision maker. All execution intents must be validated
    through this client before execution.

    Integration pattern:
    ```python
    client = Stage0Client()
    response = client.check_goal(
        goal="Search for documentation",
        tools=["web_search"],
        side_effects=[],
    )
    if response.verdict != Verdict.ALLOW:
        raise RuntimeError(f"Blocked: {response.reason}")
    ```

    API behavior:
    - HIGH severity issues should resolve to DENY
    - Under-specified or loop-sensitive actions can resolve to DEFER
    - Hosted SignalPulse (https://api.signalpulse.org) is the production default
    """

    API_BASE_URL = "https://api.signalpulse.org"
    CHECK_ENDPOINT = "/check"

    def __init__(
        self,
        api_key: Optional[str] = None,
        risk_threshold: int = 100,
        deny_on_issues: bool = False,
        api_base_url: Optional[str] = None,
    ):
        """Initialize the Stage0 client.

        Args:
            api_key: Your Stage0 API key from signalpulse.org
            risk_threshold: Local risk score threshold (default 100 = disabled)
            deny_on_issues: If True, deny on any HIGH severity issues locally
            api_base_url: Override the API base URL (default: https://api.signalpulse.org)
        """
        self.api_key = api_key or os.getenv("STAGE0_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Stage0 API key is required. Set STAGE0_API_KEY environment variable "
                "or pass api_key parameter. Get your key from https://signalpulse.org"
            )
        self.risk_threshold = risk_threshold
        self.deny_on_issues = deny_on_issues
        self.api_base_url = (
            api_base_url or os.getenv("STAGE0_BASE_URL") or self.API_BASE_URL
        )

    def check(self, intent: ExecutionIntent) -> PolicyResponse:
        """Validate an execution intent with Stage0.

        This is the core method - call it before executing any tool call
        that could have side effects.

        Args:
            intent: The execution intent to validate

        Returns:
            PolicyResponse with verdict (ALLOW/DENY/DEFER), reason, request_id, etc.
        """
        url = f"{self.api_base_url}{self.CHECK_ENDPOINT}"
        request_id = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "X-Request-Id": request_id,
        }

        try:
            response = requests.post(
                url,
                json=intent.to_request_body(),
                headers=headers,
                timeout=30,
            )

            if response.status_code == 402:
                return self._handle_pro_required(response, intent, request_id)

            if not response.ok:
                return self._handle_http_error(response, intent, request_id)

            policy_response = PolicyResponse.from_dict(
                self._safe_json(response, {"request_id": request_id})
            )
            if not policy_response.request_id:
                policy_response.request_id = request_id

            if policy_response.verdict == Verdict.ALLOW:
                policy_response = self._apply_local_rules(policy_response)

            return policy_response

        except requests.RequestException as exc:
            return PolicyResponse(
                verdict=Verdict.DENY,
                reason=f"Stage0 validation failed: {str(exc)}",
                constraints_applied=[],
                raw_response={"error": str(exc), "request_id": request_id},
                decision=Decision.ERROR,
                request_id=request_id,
            )

    def _handle_pro_required(
        self,
        response: requests.Response,
        intent: ExecutionIntent,
        request_id: str,
    ) -> PolicyResponse:
        """Handle 402 Payment Required responses."""
        payload = self._safe_json(response, {})
        detail = payload.get("detail", "Pro checks require a paid plan")
        if isinstance(detail, dict):
            reason = str(detail.get("detail", "Pro checks require a paid plan"))
            request_id = str(detail.get("request_id", request_id) or request_id)
        else:
            reason = str(detail)
            request_id = str(payload.get("request_id", request_id) or request_id)

        return PolicyResponse(
            verdict=Verdict.DENY,
            reason=f"Stage0 Pro required: {reason}",
            constraints_applied=[],
            raw_response={
                "status_code": 402,
                "response": payload,
                "intent": intent.to_request_body(),
            },
            decision=Decision.NO_GO,
            request_id=request_id,
            issues=[
                {
                    "code": "PRO_PLAN_REQUIRED",
                    "severity": "HIGH",
                    "message": reason,
                }
            ],
        )

    def _handle_http_error(
        self,
        response: requests.Response,
        intent: ExecutionIntent,
        request_id: str,
    ) -> PolicyResponse:
        """Normalize non-2xx responses into a structured policy response."""
        payload = self._safe_json(response, {})
        detail = payload.get("detail", payload)

        if isinstance(detail, dict):
            reason = str(detail.get("detail", f"HTTP {response.status_code}"))
            request_id = str(detail.get("request_id", request_id) or request_id)
        else:
            reason = str(detail or f"HTTP {response.status_code}")
            request_id = str(payload.get("request_id", request_id) or request_id)

        verdict = Verdict.DENY
        decision = Decision.ERROR
        clarifying_questions: list[str] = []

        if response.status_code == 429:
            verdict = Verdict.DEFER
            decision = Decision.DEFER
            retry_after = None
            if isinstance(detail, dict):
                retry_after = detail.get("retry_after_seconds")
            if retry_after is not None:
                clarifying_questions.append(
                    f"Retry after {retry_after} seconds or lower request volume."
                )

        return PolicyResponse(
            verdict=verdict,
            reason=reason,
            constraints_applied=[],
            raw_response={
                "status_code": response.status_code,
                "response": payload,
                "intent": intent.to_request_body(),
            },
            decision=decision,
            request_id=request_id,
            clarifying_questions=clarifying_questions,
            defer_questions=list(clarifying_questions),
        )

    def _apply_local_rules(self, response: PolicyResponse) -> PolicyResponse:
        """Apply optional local deny rules on top of the hosted decision."""
        if response.risk_score >= self.risk_threshold:
            return replace(
                response,
                verdict=Verdict.DENY,
                decision=Decision.NO_GO,
                reason=(
                    f"Risk score ({response.risk_score}) exceeds threshold "
                    f"({self.risk_threshold})"
                ),
            )

        if self.deny_on_issues and response.has_high_severity_issues():
            first_issue = response.issues[0].get("message", "Unknown issue")
            return replace(
                response,
                verdict=Verdict.DENY,
                decision=Decision.NO_GO,
                reason=f"High severity issues detected: {first_issue}",
            )

        return response

    def _safe_json(
        self, response: requests.Response, fallback: dict[str, Any]
    ) -> dict[str, Any]:
        """Read a JSON response body without raising parsing errors."""
        try:
            data = response.json()
        except ValueError:
            return dict(fallback)
        return data if isinstance(data, dict) else dict(fallback)

    def check_goal(
        self,
        goal: str,
        success_criteria: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        tools: Optional[list[str]] = None,
        side_effects: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
        pro: bool = False,
        policy_pack_version: str = "",
        debug_store_input: bool = False,
    ) -> PolicyResponse:
        """Convenience method to check a goal directly.

        This is the simplest way to integrate Stage0 into your agent:

        ```python
        client = Stage0Client()
        response = client.check_goal(
            goal="Search for Python documentation",
            tools=["web_search"],
            side_effects=[],
        )
        if response.verdict == Verdict.ALLOW:
            # Execute your tool call
            ...
        else:
            print(f"Blocked: {response.reason}")
            print(f"Request ID: {response.request_id}")
        ```

        Args:
            goal: What you're trying to accomplish
            success_criteria: What success looks like
            constraints: Any constraints to apply
            tools: Tools you plan to use
            side_effects: Potential side effects (publish, deploy, etc.)
            context: Runtime context (actor_role, environment, etc.)
            pro: Whether this requires Pro features
            policy_pack_version: Specific policy version to use
            debug_store_input: Whether to store input for debugging

        Returns:
            PolicyResponse with verdict, reason, request_id, policy_version, etc.
        """
        intent = ExecutionIntent(
            goal=goal,
            success_criteria=success_criteria or [],
            constraints=constraints or [],
            tools=tools or [],
            side_effects=side_effects or [],
            context=context or {},
            pro=pro,
            policy_pack_version=policy_pack_version,
            debug_store_input=debug_store_input,
        )
        return self.check(intent)


def _parse_verdict(value: Any) -> Verdict:
    """Parse a verdict value safely."""
    token = str(value or "DENY").upper()
    try:
        return Verdict(token)
    except ValueError:
        return Verdict.DENY


def _parse_decision(value: Any) -> Decision:
    """Parse a decision value safely."""
    token = str(value or "ERROR").upper()
    try:
        return Decision(token)
    except ValueError:
        return Decision.ERROR


def _ensure_dict(value: Any) -> dict[str, Any]:
    """Return a dictionary or an empty dictionary."""
    return value if isinstance(value, dict) else {}


def _ensure_dict_list(value: Any) -> list[dict[str, Any]]:
    """Return a list of dictionaries, filtering invalid items."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
