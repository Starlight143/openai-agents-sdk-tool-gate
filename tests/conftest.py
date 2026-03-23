"""Pytest fixtures for Stage0 Tool Gate tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_stage0_client():
    """Create a mock Stage0 client for testing."""
    from unittest.mock import MagicMock

    from stage0 import PolicyResponse, Verdict

    def create_response(verdict: Verdict, reason: str = "") -> PolicyResponse:
        return PolicyResponse(
            verdict=verdict,
            reason=reason,
            constraints_applied=[],
            raw_response={},
            request_id="test_req_123",
            policy_version="test-1.0.0",
        )

    client = MagicMock()
    client.check_goal = MagicMock(
        side_effect=lambda **kwargs: create_response(Verdict.ALLOW, "Test allow")
    )

    return client


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    from unittest.mock import MagicMock

    agent = MagicMock()
    agent.name = "TestAgent"
    return agent


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing."""
    from unittest.mock import MagicMock

    tool = MagicMock()
    tool.name = "test_tool"
    return tool


@pytest.fixture
def mock_context():
    """Create a mock RunContextWrapper for testing."""
    from unittest.mock import MagicMock

    context = MagicMock()
    context.context = {}
    return context
