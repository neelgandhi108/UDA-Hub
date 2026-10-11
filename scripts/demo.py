"""Run reproducible resolution, action, memory, and escalation demonstrations."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agentic.workflow import build_workflow, process_ticket
from scripts.setup_databases import setup_all


def summary(result: dict) -> dict:
    return {
        "outcome": result["outcome"], "route": result["route"],
        "category": result["classification"]["category"],
        "confidence": result.get("retrieval_confidence"),
        "tools": [item["tool"] for item in result.get("tool_results", [])],
        "sources": [item["title"] for item in result.get("knowledge_results", [])[:1]],
        "response": result["response"],
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="udahub-demo-") as directory:
        root = Path(directory)
        external, core = setup_all(root / "cultpass.db", root / "udahub.db")
        graph = build_workflow(core_db_path=core, external_db_path=external, log_path=root / "audit.jsonl")
        cases = [
            ("resolution", "demo-resolution", {
                "account_id": "cultpass", "external_user_id": "a4ab87", "user_name": "Alice Kingsley",
                "text": "I cannot log in and the password reset email is missing", "channel": "chat", "urgency": "high",
            }),
            ("same-thread-follow-up", "demo-resolution", {
                "account_id": "cultpass", "external_user_id": "a4ab87", "user_name": "Alice Kingsley",
                "text": "That did not work. What should I do next?", "channel": "chat", "urgency": "high",
            }),
            ("tool-action", "demo-action", {
                "account_id": "cultpass", "external_user_id": "f556c0", "user_name": "Bob Stone",
                "text": "Please pause my subscription", "channel": "email", "urgency": "normal", "execute_action": True,
            }),
            ("memory-write", "memory-one", {
                "account_id": "cultpass", "external_user_id": "88382b", "user_name": "Cathy Bloom",
                "text": "I prefer email. How do I change notification settings?", "channel": "chat", "urgency": "normal",
            }),
            ("memory-recall", "memory-two", {
                "account_id": "cultpass", "external_user_id": "88382b", "user_name": "Cathy Bloom",
                "text": "How do I change my app language?", "channel": "chat", "urgency": "normal",
            }),
            ("escalation", "demo-escalation", {
                "account_id": "cultpass", "external_user_id": "e6376d", "user_name": "Frank Ocean",
                "text": "Can CultPass arrange a private astronomy lesson on Mars?", "channel": "web", "urgency": "normal",
            }),
        ]
        for label, thread_id, ticket in cases:
            print(f"\n--- {label} ---")
            print(json.dumps(summary(process_ticket(ticket, thread_id=thread_id, graph=graph)), indent=2))
        print(f"\nStructured log records: {sum(1 for _ in (root / 'audit.jsonl').open())}")


if __name__ == "__main__":
    main()
