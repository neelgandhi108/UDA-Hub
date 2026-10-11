"""Account-scoped knowledge retrieval agent."""

from langchain_core.runnables import RunnableConfig

from .common import context


def make_knowledge_agent(tools, logger):
    def knowledge_agent(state: dict, config: RunnableConfig | None = None) -> dict:
        ticket = state["ticket"]
        classification = state["classification"]
        expanded_query = " ".join([
            state.get("interpreted_query") or ticket["text"], classification.get("category", ""),
            " ".join(classification.get("signals", [])),
        ])
        result = tools.search_knowledge(ticket["account_id"], expanded_query, limit=3)
        articles = result["data"] if result.get("ok") else []
        confidence = articles[0]["confidence"] if articles else 0.0
        errors = list(state.get("errors", []))
        if not result.get("ok"):
            errors.append(result["error"])
        thread_id, ticket_id = context(state, config)
        logger.log("knowledge_retrieved", "knowledge", thread_id=thread_id, ticket_id=ticket_id,
                   details={"result_count": len(articles), "confidence": confidence,
                            "article_ids": [article["article_id"] for article in articles]})
        return {"knowledge_results": articles, "retrieval_confidence": confidence,
                "retrieval_query": expanded_query, "errors": errors,
                "decision_trace": [f"knowledge: retrieved {len(articles)} article(s), confidence {confidence:.2f}"]}

    return knowledge_agent
