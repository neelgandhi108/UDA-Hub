"""Short- and long-term context retrieval agent."""

from langchain_core.runnables import RunnableConfig

from .common import context


def make_memory_agent(core_repository, logger):
    def memory_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        ticket = state["ticket"]
        thread_id, ticket_id = context(state, config)
        persistent = core_repository.load_customer_context(ticket["account_id"], ticket["external_user_id"])
        session_user_turns = sum(1 for message in state.get("messages", []) if getattr(message, "type", "") == "human")
        memory_context = {**persistent, "session_user_turns": session_user_turns}
        logger.log("memory_loaded", "memory", thread_id=thread_id, ticket_id=ticket_id,
                   details={"durable_memories": len(persistent["memories"]),
                            "prior_ticket_count": persistent["prior_ticket_count"],
                            "session_user_turns": session_user_turns})
        return {"memory_context": memory_context,
                "decision_trace": [f"memory: loaded {len(persistent['memories'])} durable memories and {session_user_turns} session turn(s)"]}

    return memory_agent
