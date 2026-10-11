"""Typed input and shared-state contracts for the support graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupportTicket(TypedDict, total=False):
    ticket_id: str
    account_id: str
    external_user_id: str
    user_name: str
    text: str
    channel: str
    urgency: str
    created_at: str
    execute_action: bool


class SupportState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    ticket: SupportTicket
    thread_id: str
    memory_context: dict[str, Any]
    interpreted_query: str
    retrieval_query: str
    classification: dict[str, Any]
    route: str
    tool_results: list[dict[str, Any]]
    knowledge_results: list[dict[str, Any]]
    retrieval_confidence: float
    decision_trace: Annotated[list[str], operator.add]
    outcome: str
    response: str
    escalation_reason: str
    errors: list[str]
