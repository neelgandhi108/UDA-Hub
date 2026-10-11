"""Rule-based, metadata-aware ticket classifier agent."""

import re
from collections import defaultdict

from langchain_core.runnables import RunnableConfig

from .common import context


CATEGORY_TERMS = {
    "billing": {"billing", "payment", "paid", "card", "charged", "charge", "refund", "subscription", "plan", "cancel", "pause", "price", "fee"},
    "reservation": {"reserve", "reservation", "booking", "event", "experience", "qr", "waitlist", "sold out", "venue", "reschedule", "accommodation"},
    "technical": {"login", "log in", "password", "reset", "crash", "freeze", "error", "bug", "app", "code", "sign in"},
    "account": {"account", "email", "profile", "blocked", "delete", "privacy", "notification", "language", "location", "personal data"},
}
HIGH_RISK_TERMS = {"fraud", "stolen card", "data breach", "hacked", "legal action", "lawsuit", "chargeback", "injured", "unsafe", "threat"}
URGENT_TERMS = {"urgent", "immediately", "right now", "today", "event starts", "locked out"}
GENERIC_TERM_WEIGHTS = {"app": 0.25, "event": 0.4, "account": 0.5, "subscription": 0.5}
FOLLOW_UP_PATTERN = re.compile(
    r"\b(that|this|it|those|they|still|again|next|same issue|did not|didn't|does not|doesn't|not work|failed)\b",
    flags=re.IGNORECASE,
)


def _category_scores(text: str) -> tuple[dict[str, float], list[str]]:
    scores: dict[str, float] = defaultdict(float)
    matched_signals: list[str] = []
    for category, terms in CATEGORY_TERMS.items():
        for term in terms:
            if re.search(rf"\b{re.escape(term)}\b", text):
                scores[category] += 2.0 if " " in term else GENERIC_TERM_WEIGHTS.get(term, 1.0)
                matched_signals.append(term)
    return scores, matched_signals


def make_classifier_agent(logger):
    def classifier_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        ticket = state["ticket"]
        current_text = ticket["text"].lower()
        prior_user_messages = state.get("memory_context", {}).get("prior_user_messages", [])
        uses_session_context = bool(prior_user_messages and FOLLOW_UP_PATTERN.search(current_text))
        original_issue = prior_user_messages[-1] if uses_session_context else ""
        interpreted_query = ticket["text"]
        if original_issue:
            interpreted_query = f"Current follow-up: {ticket['text']} Earlier issue: {original_issue}"

        text = interpreted_query.lower()
        scores, matched_signals = _category_scores(text)
        category = max(scores, key=scores.get) if scores else "general"
        risk_signals = sorted(term for term in HIGH_RISK_TERMS if term in text)
        urgency = ticket.get("urgency", "normal")
        if any(term in text for term in URGENT_TERMS):
            urgency = "urgent"
        history = state.get("memory_context", {})
        clauses = len([part for part in re.split(r"[;?.!]", text) if part.strip()])
        complexity = "high" if risk_signals or clauses >= 4 or history.get("prior_ticket_count", 0) >= 4 else "normal"
        confidence = 0.5 if category == "general" else min(0.98, 0.62 + scores[category] * 0.07)
        classification = {
            "category": category,
            "urgency": urgency,
            "complexity": complexity,
            "confidence": round(confidence, 3),
            "signals": sorted(set(matched_signals)),
            "risk_signals": risk_signals,
            "used_session_context": uses_session_context,
            "context_turns_used": 1 if uses_session_context else 0,
            "channel": ticket["channel"],
            "created_at": ticket["created_at"],
        }
        thread_id, ticket_id = context(state, config)
        logger.log("ticket_classified", "classifier", thread_id=thread_id, ticket_id=ticket_id, details=classification)
        context_note = " with prior-thread context" if uses_session_context else ""
        return {"classification": classification, "interpreted_query": interpreted_query,
                "decision_trace": [
                    f"classifier: {category} / {urgency} / {complexity} "
                    f"(confidence {confidence:.2f}){context_note}"
                ]}

    return classifier_agent
