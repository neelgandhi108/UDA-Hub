"""From-scratch LangGraph orchestration for UDA-Hub.

No prebuilt workflow or ReAct agent is used. Every node is a specialized agent
defined under ``agentic/agents`` and every database operation is injected through
``agentic/tools``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agentic.agents import (
    make_classifier_agent,
    make_escalation_agent,
    make_intake_agent,
    make_knowledge_agent,
    make_memory_agent,
    make_operations_agent,
    make_persistence_agent,
    make_resolver_agent,
    make_supervisor_agent,
)
from agentic.state import SupportState, SupportTicket
from agentic.tools import CoreRepository, CultPassRepository, JsonlAuditLogger, SupportTools


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORE_DB = SOLUTION_ROOT / "data" / "core" / "udahub.db"
DEFAULT_EXTERNAL_DB = SOLUTION_ROOT / "data" / "external" / "cultpass.db"
DEFAULT_LOG = SOLUTION_ROOT / "logs" / "udahub.jsonl"


def build_workflow(
    *,
    core_db_path: str | Path = DEFAULT_CORE_DB,
    external_db_path: str | Path = DEFAULT_EXTERNAL_DB,
    log_path: str | Path = DEFAULT_LOG,
    checkpointer: Any | None = None,
    retrieval_threshold: float = 0.42,
):
    """Build and compile the supervisor graph with injected dependencies."""

    core = CoreRepository(core_db_path)
    external = CultPassRepository(external_db_path)
    tools = SupportTools(external, core)
    logger = JsonlAuditLogger(log_path)

    graph = StateGraph(SupportState)
    graph.add_node("intake", make_intake_agent(logger))
    graph.add_node("memory", make_memory_agent(core, logger))
    graph.add_node("classifier", make_classifier_agent(logger))
    graph.add_node("supervisor", make_supervisor_agent(logger))
    graph.add_node("operations", make_operations_agent(tools, logger))
    graph.add_node("knowledge", make_knowledge_agent(tools, logger))
    graph.add_node("resolver", make_resolver_agent(logger, retrieval_threshold))
    graph.add_node("escalation", make_escalation_agent(logger))
    graph.add_node("persistence", make_persistence_agent(core, logger))

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "memory")
    graph.add_edge("memory", "classifier")
    graph.add_edge("classifier", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"operations": "operations", "knowledge": "knowledge", "escalation": "escalation"},
    )
    graph.add_edge("operations", "knowledge")
    graph.add_edge("knowledge", "resolver")
    graph.add_conditional_edges(
        "resolver",
        lambda state: "escalation" if state["outcome"] == "escalated" else "persistence",
        {"escalation": "escalation", "persistence": "persistence"},
    )
    graph.add_edge("escalation", "persistence")
    graph.add_edge("persistence", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def process_ticket(
    ticket: SupportTicket,
    *,
    thread_id: str,
    graph=None,
) -> SupportState:
    """Process one turn. Reuse ``thread_id`` for short-term session memory."""

    active_graph = graph or orchestrator
    return active_graph.invoke(
        {"ticket": ticket},
        config={"configurable": {"thread_id": thread_id}},
    )


# Convenient default for the notebook and CLI. Building does not open either DB;
# callers receive a clear repository error only if setup was skipped and invoked.
orchestrator = build_workflow()
