"""Supervisor routing agent."""

from langchain_core.runnables import RunnableConfig

from .common import context


def make_supervisor_agent(logger):
    def supervisor_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        classification = state["classification"]
        if classification.get("risk_signals"):
            route = "escalation"
            reason = "High-risk language requires a trained human review."
        elif classification["category"] in {"billing", "account", "reservation"}:
            route = "operations"
            reason = f"{classification['category']} needs customer-specific operational context."
        else:
            route = "knowledge"
            reason = f"{classification['category']} can start with account-scoped knowledge retrieval."
        thread_id, ticket_id = context(state, config)
        logger.log("route_selected", "supervisor", thread_id=thread_id, ticket_id=ticket_id,
                   details={"route": route, "reason": reason})
        result = {"route": route, "decision_trace": [f"supervisor: routed to {route} — {reason}"]}
        if route == "escalation":
            result["escalation_reason"] = reason
        return result

    return supervisor_agent
