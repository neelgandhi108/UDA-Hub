from __future__ import annotations


def test_account_and_reservation_tools_return_structured_results(project):
    tools = project["tools"]
    account = tools.lookup_account("f556c0")
    reservations = tools.list_reservations("f556c0")
    assert set(account) == {"ok", "tool", "data", "error"}
    assert account["ok"] and account["tool"] == "lookup_account"
    assert reservations["ok"] and reservations["tool"] == "list_reservations"
    assert reservations["data"][0]["reservation_id"] == "res-003"


def test_subscription_update_validates_and_mutates(project):
    tools = project["tools"]
    result = tools.update_subscription("f556c0", "pause")
    assert result["ok"] is True
    assert result["data"]["previous_status"] == "active"
    assert result["data"]["status"] == "paused"
    assert tools.lookup_account("f556c0")["data"]["subscription"]["status"] == "paused"

    invalid = tools.update_subscription("f556c0", "erase")
    unknown = tools.lookup_account("does-not-exist")
    blocked = tools.update_subscription("a4ab87", "pause")
    assert invalid["ok"] is False and "Unsupported" in invalid["error"]
    assert unknown["ok"] is False and "not found" in unknown["error"]
    assert blocked["ok"] is False and "Trust and Safety" in blocked["error"]


def test_knowledge_tool_retrieves_and_scores(project):
    result = project["tools"].search_knowledge("cultpass", "password reset email did not arrive")
    assert result["ok"] is True
    assert result["data"][0]["article_id"] == "kb-login"
    assert 0.42 <= result["data"][0]["confidence"] <= 1.0

    missing = project["tools"].search_knowledge("cultpass", "astronomy lesson on Mars")
    assert missing["ok"] is True
    assert missing["data"] == []


def test_retrieval_selects_articles_across_diverse_topics(project):
    tools = project["tools"]
    cases = {
        "turn off marketing notifications": "kb-notifications",
        "event is sold out how do I join the waitlist": "kb-sold-out",
        "payment card was declined": "kb-payment-failed",
        "request step-free accessibility accommodation": "kb-accessibility",
    }
    for query, expected_id in cases.items():
        result = tools.search_knowledge("cultpass", query)
        assert result["data"][0]["article_id"] == expected_id
