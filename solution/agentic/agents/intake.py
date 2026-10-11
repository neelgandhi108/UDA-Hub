"""Input validation and normalization agent."""

import re
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from .common import context


VALID_URGENCY = {"low", "normal", "high", "urgent"}


def make_intake_agent(logger):
    def intake_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        raw_ticket = state.get("ticket")
        if raw_ticket is None and state.get("messages"):
            last_text = ""
            for m in reversed(state.get("messages", [])):
                content = getattr(m, "content", "")
                if content:
                    last_text = str(content).strip()
                    break
            raw = {
                "text": last_text,
                "external_user_id": "a4ab87",
                "account_id": "cultpass",
                "user_name": "Alice Kingsley",
                "channel": "chat",
                "urgency": "normal",
            }
        else:
            raw = dict(raw_ticket or {})

        required = ("text", "external_user_id")
        missing = [field for field in required if not str(raw.get(field, "")).strip()]
        if missing:
            raise ValueError(f"Ticket is missing required field(s): {', '.join(missing)}")

        thread_id, _ = context(state, config)
        urgency = str(raw.get("urgency", "normal")).lower()
        if urgency not in VALID_URGENCY:
            urgency = "normal"
        safe_thread = re.sub(r"[^a-zA-Z0-9_.-]", "-", thread_id)[:80]
        ticket = {
            **raw,
            "text": str(raw["text"]).strip(),
            "external_user_id": str(raw["external_user_id"]).strip(),
            "account_id": str(raw.get("account_id", "cultpass")).strip(),
            "user_name": str(raw.get("user_name", "Unknown customer")).strip(),
            "channel": str(raw.get("channel", "chat")).lower(),
            "urgency": urgency,
            "created_at": str(raw.get("created_at") or datetime.now(UTC).isoformat()),
            "execute_action": bool(raw.get("execute_action", False)),
            "ticket_id": str(raw.get("ticket_id") or f"ticket-{safe_thread}"),
        }
        logger.log("ticket_received", "intake", thread_id=thread_id, ticket_id=ticket["ticket_id"],
                   details={"channel": ticket["channel"], "urgency": ticket["urgency"]})
        return {
            "ticket": ticket,
            "thread_id": thread_id,
            "messages": [HumanMessage(content=ticket["text"])],
            "classification": {}, "route": "", "tool_results": [], "knowledge_results": [],
            "retrieval_confidence": 0.0, "outcome": "", "response": "",
            "escalation_reason": "", "errors": [],
            "decision_trace": ["intake: ticket validated and normalized"],
        }

    return intake_agent
