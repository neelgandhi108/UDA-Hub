from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from agentic.workflow import process_ticket
from data.models import udahub
from conftest import ticket


def test_end_to_end_technical_resolution_is_grounded(project):
    result = process_ticket(
        ticket("I can't log in and my password reset email never arrived", urgency="high"),
        thread_id="technical-resolution",
        graph=project["graph"],
    )
    assert result["classification"]["category"] == "technical"
    assert result["classification"]["urgency"] == "high"
    assert result["route"] == "knowledge"
    assert result["outcome"] == "resolved"
    assert result["knowledge_results"][0]["article_id"] == "kb-login"
    assert "Source:" in result["response"] and "kb-login" in result["response"]
    assert any("classifier:" in step for step in result["decision_trace"])


def test_operations_route_uses_tool_and_executes_explicit_action(project):
    result = process_ticket(
        ticket("Please pause my subscription", execute_action=True),
        thread_id="billing-action",
        graph=project["graph"],
    )
    assert result["classification"]["category"] == "billing"
    assert result["route"] == "operations"
    assert [item["tool"] for item in result["tool_results"]] == ["lookup_account", "update_subscription"]
    assert result["tool_results"][1]["data"]["status"] == "paused"
    assert result["outcome"] == "resolved"
    assert "status changed" in result["response"]


def test_unknown_topic_escalates_at_confidence_gate(project):
    result = process_ticket(
        ticket("Can CultPass arrange a private astronomy lesson on Mars?"),
        thread_id="unknown-escalation",
        graph=project["graph"],
    )
    assert result["route"] == "knowledge"
    assert result["retrieval_confidence"] < 0.42
    assert result["outcome"] == "escalated"
    assert "human support specialist" in result["response"]
    assert "No sufficiently relevant knowledge" in result["response"]


def test_high_risk_ticket_is_immediately_escalated(project):
    result = process_ticket(
        ticket("I think my card was stolen and this is fraud", urgency="urgent"),
        thread_id="risk-escalation",
        graph=project["graph"],
    )
    assert result["route"] == "escalation"
    assert result["outcome"] == "escalated"
    assert "fraud" in result["classification"]["risk_signals"]
    assert result["knowledge_results"] == []


def test_input_validation(project):
    with pytest.raises(ValueError, match="external_user_id"):
        process_ticket({"text": "help"}, thread_id="invalid", graph=project["graph"])


def test_interaction_and_structured_logs_are_persisted(project):
    result = process_ticket(ticket("How do I join an event waitlist?"), thread_id="logging", graph=project["graph"])
    with Session(create_engine(f"sqlite:///{project['core_db']}")) as session:
        db_ticket = session.get(udahub.Ticket, "ticket-logging")
        messages = session.scalars(select(udahub.TicketMessage).where(udahub.TicketMessage.ticket_id == "ticket-logging")).all()
        assert db_ticket is not None
        assert db_ticket.ticket_metadata.status == result["outcome"]
        assert {message.role.value for message in messages} == {"user", "ai"}

    records = [json.loads(line) for line in project["log_path"].read_text().splitlines()]
    events = {record["event"] for record in records}
    assert {"ticket_received", "ticket_classified", "route_selected", "knowledge_retrieved",
            "resolution_decided", "interaction_persisted"} <= events
    assert all(record["thread_id"] == "logging" for record in records)
