"""Interaction-history and long-term-memory persistence agent."""

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from .common import context


def make_persistence_agent(core_repository, logger):
    def persistence_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        thread_id, ticket_id = context(state, config)
        errors = list(state.get("errors", []))
        try:
            core_repository.persist_interaction(
                state["ticket"], classification=state.get("classification", {}),
                outcome=state["outcome"], response=state["response"],
                confidence=state.get("retrieval_confidence", 0.0),
                sources=state.get("knowledge_results", []),
            )
            logger.log("interaction_persisted", "persistence", thread_id=thread_id, ticket_id=ticket_id,
                       details={"outcome": state["outcome"]})
            trace = "persistence: stored ticket messages and durable memory"
        except Exception as exc:
            error = f"Persistence failed: {type(exc).__name__}"
            errors.append(error)
            logger.log("persistence_failed", "persistence", thread_id=thread_id, ticket_id=ticket_id,
                       details={"error": error})
            trace = "persistence: failed safely; response remains available"
        return {"messages": [AIMessage(content=state["response"])], "errors": errors,
                "decision_trace": [trace]}

    return persistence_agent
