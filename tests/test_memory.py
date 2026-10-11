from __future__ import annotations

from agentic.workflow import process_ticket
from conftest import ticket


def test_checkpoint_short_term_memory_uses_thread_id(project):
    first = process_ticket(ticket("How do I manage notifications?"), thread_id="same-session", graph=project["graph"])
    second = process_ticket(ticket("How do I change my app language?"), thread_id="same-session", graph=project["graph"])
    assert first["memory_context"]["session_user_turns"] == 1
    assert second["memory_context"]["session_user_turns"] == 2
    human_messages = [message for message in second["messages"] if message.type == "human"]
    assert [message.content for message in human_messages] == [
        "How do I manage notifications?", "How do I change my app language?",
    ]


def test_preference_is_recalled_across_different_sessions(project):
    write = process_ticket(
        ticket("I prefer email. How can I change notification settings?", user_id="88382b"),
        thread_id="preference-write",
        graph=project["graph"],
    )
    assert write["outcome"] == "resolved"
    assert write["knowledge_results"][0]["article_id"] == "kb-notifications"

    recall = process_ticket(
        ticket("How do I change the app language?", user_id="88382b"),
        thread_id="preference-recall",
        graph=project["graph"],
    )
    assert recall["memory_context"]["session_user_turns"] == 1
    assert recall["classification"]["category"] == "account"
    assert any(memory["kind"] == "preference" for memory in recall["memory_context"]["memories"])
    assert "prefers contact by email" in recall["response"]
    assert recall["memory_context"]["prior_ticket_count"] >= 1
