"""Customer-specific support operations agent."""

from langchain_core.runnables import RunnableConfig

from .common import context, safe_tool_summary


def _subscription_action(text: str) -> str | None:
    lowered = text.lower()
    if any(word in lowered for word in ("cancel", "terminate")):
        return "cancel"
    if any(word in lowered for word in ("pause", "suspend")):
        return "pause"
    if any(word in lowered for word in ("reactivate", "resume")):
        return "reactivate"
    return None


def make_operations_agent(tools, logger):
    def operations_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        ticket = state["ticket"]
        category = state["classification"]["category"]
        user_id = ticket["external_user_id"]
        thread_id, ticket_id = context(state, config)
        results: list[dict] = []

        calls = [("lookup_account", lambda: tools.lookup_account(user_id))]
        if category == "reservation":
            calls.append(("list_reservations", lambda: tools.list_reservations(user_id)))
        action = _subscription_action(ticket["text"]) if category == "billing" else None
        if action and ticket.get("execute_action"):
            calls.append(("update_subscription", lambda: tools.update_subscription(user_id, action)))

        for tool_name, operation in calls:
            logger.log("tool_invoked", "operations", thread_id=thread_id, ticket_id=ticket_id,
                       details={"tool": tool_name})
            result = operation()
            results.append(result)
            logger.log("tool_completed", "operations", thread_id=thread_id, ticket_id=ticket_id,
                       details=safe_tool_summary(result))

        if action and not ticket.get("execute_action"):
            results.append({"ok": True, "tool": "update_subscription_preview",
                            "data": {"action": action, "executed": False}, "error": None})
        errors = [result["error"] for result in results if not result.get("ok")]
        trace = f"operations: invoked {', '.join(result['tool'] for result in results)}"
        return {"tool_results": results, "errors": errors,
                "decision_trace": [trace]}

    return operations_agent
