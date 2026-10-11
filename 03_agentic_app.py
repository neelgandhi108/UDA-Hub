"""CLI entry point for the UDA-Hub support workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic.workflow import DEFAULT_CORE_DB, DEFAULT_EXTERNAL_DB, build_workflow, process_ticket
from scripts.setup_databases import setup_all
from utils import chat_interface


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", help="Process one ticket and print JSON")
    parser.add_argument("--thread-id", default="cli-session")
    parser.add_argument("--user-id", default="a4ab87")
    parser.add_argument("--user-name", default="Alice Kingsley")
    parser.add_argument("--channel", default="chat", choices=("chat", "email", "web", "phone"))
    parser.add_argument("--urgency", default="normal", choices=("low", "normal", "high", "urgent"))
    parser.add_argument("--execute-actions", action="store_true")
    parser.add_argument("--reset-databases", action="store_true")
    args = parser.parse_args()

    if args.reset_databases or not (Path(DEFAULT_CORE_DB).exists() and Path(DEFAULT_EXTERNAL_DB).exists()):
        setup_all()
    graph = build_workflow()
    defaults = {
        "account_id": "cultpass", "external_user_id": args.user_id,
        "user_name": args.user_name, "channel": args.channel,
        "urgency": args.urgency, "execute_action": args.execute_actions,
    }
    if args.once:
        result = process_ticket({**defaults, "text": args.once}, thread_id=args.thread_id, graph=graph)
        public = {key: result.get(key) for key in (
            "outcome", "response", "classification", "route", "retrieval_confidence",
            "tool_results", "knowledge_results", "decision_trace", "errors",
        )}
        print(json.dumps(public, indent=2, default=str))
    else:
        chat_interface(graph, defaults, args.thread_id)


if __name__ == "__main__":
    main()
