from __future__ import annotations

import json

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from data.models import udahub


def test_required_core_schema_and_articles(project):
    engine = create_engine(f"sqlite:///{project['core_db']}")
    table_names = set(inspect(engine).get_table_names())
    assert {"accounts", "users", "tickets", "ticket_metadata", "ticket_messages", "knowledge"} <= table_names
    assert "customer_memories" in table_names

    with Session(engine) as session:
        articles = session.scalars(select(udahub.Knowledge)).all()
    assert len(articles) == 16
    all_tags = " ".join(article.tags for article in articles).lower()
    assert all(category in all_tags for category in ("technical", "billing", "account", "reservation", "privacy", "accessibility"))


def test_seed_data_is_retrievable(project):
    account = project["tools"].lookup_account("f556c0")
    reservations = project["tools"].list_reservations("a4ab87")
    assert account["ok"] is True
    assert account["data"]["full_name"] == "Bob Stone"
    assert account["data"]["subscription"]["monthly_quota"] == 4
    assert reservations["ok"] is True
    assert len(reservations["data"]) == 2
