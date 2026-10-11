"""Human hand-off agent."""

from langchain_core.runnables import RunnableConfig

from .common import context


def make_escalation_agent(logger):
    def escalation_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        classification = state.get("classification", {})
        reason = state.get("escalation_reason") or "Automation could not safely resolve this request."
        attempted_tools = ", ".join(item.get("tool", "unknown") for item in state.get("tool_results", [])) or "none"
        prior_user_messages = state.get("memory_context", {}).get("prior_user_messages", [])
        issue_context = ""
        if classification.get("used_session_context") and prior_user_messages:
            issue_context = f' Original issue: "{prior_user_messages[-1]}".'
        response = (
            "I’m escalating this to a human support specialist so it can be handled safely. "
            f"Reason: {reason}{issue_context} The hand-off includes category={classification.get('category', 'unknown')}, "
            f"urgency={classification.get('urgency', 'normal')}, and attempted tools={attempted_tools}."
        )
        thread_id, ticket_id = context(state, config)
        logger.log("ticket_escalated", "escalation", thread_id=thread_id, ticket_id=ticket_id,
                   details={"reason": reason, "category": classification.get("category"),
                            "urgency": classification.get("urgency")})
        return {"outcome": "escalated", "response": response,
                "decision_trace": [f"escalation: prepared human hand-off — {reason}"]}

    return escalation_agent
