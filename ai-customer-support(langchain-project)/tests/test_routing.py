"""Routing graph smoke tests."""

import pytest

from app.graph.routing import route_after_supervisor
from app.graph.workflow import get_compiled_graph_sync


def test_workflow_compiles() -> None:
    graph = get_compiled_graph_sync()
    assert graph is not None


@pytest.mark.parametrize(
    "agent,node",
    [
        ("billing", "billing_agent"),
        ("technical", "technical_agent"),
        ("account", "account_agent"),
        ("general", "general_agent"),
    ],
)
def test_route_mapping(agent: str, node: str) -> None:
    assert route_after_supervisor({"assigned_agent": agent}) == node  # type: ignore[arg-type]
