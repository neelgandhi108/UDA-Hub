"""Shared helpers and a small terminal chat UI."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from langchain_core.messages import HumanMessage


def reset_db(db_path: str | Path, echo: bool = False) -> Engine:
    """Recreate an empty SQLite file and return its engine.

    Models use separate declarative bases, so callers intentionally invoke the
    relevant ``Base.metadata.create_all`` after this helper.
    """

    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        os.remove(path)
    return create_engine(f"sqlite:///{path}", echo=echo)


@contextmanager
def get_session(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def model_to_dict(instance: object) -> dict:
    return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}


def chat_interface(
    agent,
    ticket_defaults: dict | str = "1",
    thread_id: str | None = None,
) -> None:
    """Run a conversational loop while preserving state under ``thread_id``.

    Supports both ``chat_interface(agent, defaults, thread_id)`` from the CLI and
    the starter notebook's ``chat_interface(agent, thread_id)``.
    """
    if thread_id is None:
        if isinstance(ticket_defaults, str):
            thread_id = ticket_defaults
            defaults = {
                "account_id": "cultpass",
                "external_user_id": "a4ab87",
                "user_name": "Alice Kingsley",
                "channel": "chat",
                "urgency": "normal",
                "execute_action": False,
            }
        else:
            defaults = ticket_defaults
            thread_id = "cli-session"
    else:
        defaults = ticket_defaults if isinstance(ticket_defaults, dict) else {}

    print("UDA-Hub ready. Type 'quit' to exit.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nUDA-Hub: Goodbye!")
            return
        if user_input.lower() in {"quit", "exit", "q"}:
            print("UDA-Hub: Goodbye!")
            return
        if not user_input:
            continue
        ticket = {**defaults, "text": user_input}
        state = agent.invoke(
            {"ticket": ticket, "messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"thread_id": thread_id}},
        )
        print(f"UDA-Hub: {state['response']}")
