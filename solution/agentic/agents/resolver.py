"""Grounded response composition and confidence-gate agent."""

import re

from langchain_core.runnables import RunnableConfig

from .common import context


def _suggested_phrasing(content: str) -> str:
    match = re.search(r"Suggested phrasing:\s*(.+)", content, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return " ".join(match.group(1).strip().split())
    first_paragraph = content.split("\n\n", 1)[0]
    return " ".join(first_paragraph.split())


def _tool_context(results: list[dict]) -> str:
    parts: list[str] = []
    for result in results:
        if not result.get("ok"):
            continue
        data = result.get("data") or {}
        if result["tool"] == "lookup_account" and data:
            subscription = data.get("subscription") or {}
            parts.append(f"Account check: subscription is {subscription.get('status', 'unknown')} on the {subscription.get('tier', 'unknown')} tier.")
        elif result["tool"] == "list_reservations":
            active = [item for item in data if item.get("status") == "reserved"]
            if active:
                parts.append("Active reservations: " + "; ".join(f"{item['title']} ({item['reservation_id']})" for item in active[:3]) + ".")
            else:
                parts.append("Account check: no active reservations were found.")
        elif result["tool"] == "update_subscription":
            parts.append(f"Subscription action completed: status changed from {data['previous_status']} to {data['status']}.")
        elif result["tool"] == "update_subscription_preview":
            parts.append(f"No account change was made; the requested {data['action']} action is ready for confirmation.")
    return " ".join(parts)


def make_resolver_agent(logger, threshold: float = 0.42):
    def resolver_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        confidence = state.get("retrieval_confidence", 0.0)
        articles = state.get("knowledge_results", [])
        tool_failed = any(not item.get("ok") for item in state.get("tool_results", []))
        if tool_failed:
            outcome, reason = "escalated", "A required customer-data tool did not complete successfully."
            result = {"outcome": outcome, "escalation_reason": reason,
                      "decision_trace": [f"resolver: confidence gate failed — {reason}"]}
        elif not articles or confidence < threshold:
            outcome, reason = "escalated", f"No sufficiently relevant knowledge was found (confidence {confidence:.2f}, required {threshold:.2f})."
            result = {"outcome": outcome, "escalation_reason": reason,
                      "decision_trace": [f"resolver: confidence gate failed — {reason}"]}
        else:
            primary = articles[0]
            response_parts = [_suggested_phrasing(primary["content"])]
            tool_text = _tool_context(state.get("tool_results", []))
            if tool_text:
                response_parts.append(tool_text)
            preferences = [item["content"] for item in state.get("memory_context", {}).get("memories", [])
                           if item.get("kind") == "preference"]
            if preferences:
                response_parts.append(f"I also remember: {preferences[0]}")
            response_parts.append(f"Source: {primary['title']} [{primary['article_id']}].")
            result = {"outcome": "resolved", "response": " ".join(response_parts),
                      "decision_trace": [f"resolver: resolved with grounded article {primary['article_id']}"]}
        thread_id, ticket_id = context(state, config)
        logger.log("resolution_decided", "resolver", thread_id=thread_id, ticket_id=ticket_id,
                   details={"outcome": result["outcome"], "confidence": confidence,
                            "threshold": threshold, "reason": result.get("escalation_reason")})
        return result

    return resolver_agent
