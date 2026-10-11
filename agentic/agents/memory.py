"""Short- and long-term context retrieval agent."""

from langchain_core.runnables import RunnableConfig

from .common import context


def _message_text(message) -> str:
    """Return plain text for normal text messages and structured content blocks."""

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            str(block.get("text", "")) if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    return str(content).strip()


def make_memory_agent(core_repository, logger):
    def memory_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        ticket = state["ticket"]
        thread_id, ticket_id = context(state, config)
        persistent = core_repository.load_customer_context(ticket["account_id"], ticket["external_user_id"])
        messages = list(state.get("messages", []))
        session_user_turns = sum(1 for message in messages if getattr(message, "type", "") == "human")

        # Intake appends the current HumanMessage after checkpoint restoration.
        # Everything before it is earlier context from this exact thread_id.
        prior_messages = messages[:-1] if messages and getattr(messages[-1], "type", "") == "human" else messages
        recent_session_messages = [
            {"role": getattr(message, "type", "unknown"), "content": _message_text(message)}
            for message in prior_messages[-6:]
            if _message_text(message)
        ]
        prior_user_messages = [
            item["content"] for item in recent_session_messages if item["role"] == "human"
        ]
        memory_context = {
            **persistent,
            "session_user_turns": session_user_turns,
            "session_messages": recent_session_messages,
            "prior_user_messages": prior_user_messages,
        }
        logger.log("memory_loaded", "memory", thread_id=thread_id, ticket_id=ticket_id,
                   details={"durable_memories": len(persistent["memories"]),
                            "prior_ticket_count": persistent["prior_ticket_count"],
                            "session_user_turns": session_user_turns,
                            "prior_session_messages": len(recent_session_messages)})
        return {"memory_context": memory_context,
                "decision_trace": [
                    f"memory: loaded {len(persistent['memories'])} durable memories, "
                    f"{session_user_turns} session turn(s), and {len(recent_session_messages)} prior message(s)"
                ]}

    return memory_agent
