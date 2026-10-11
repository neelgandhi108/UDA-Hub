"""Repositories isolate every SQLAlchemy operation from graph agents."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, joinedload

from data.models import cultpass, udahub
from .retrieval import rank_articles


def _engine(path: str | Path):
    resolved = Path(path).resolve()
    return create_engine(f"sqlite:///{resolved}", future=True)


class CultPassRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()
        self.engine = _engine(self.db_path)

    def lookup_account(self, external_user_id: str) -> dict | None:
        with Session(self.engine) as session:
            user = session.scalar(
                select(cultpass.User)
                .options(joinedload(cultpass.User.subscription))
                .where(cultpass.User.user_id == external_user_id)
            )
            if not user:
                return None
            subscription = user.subscription
            return {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "is_blocked": bool(user.is_blocked),
                "subscription": None if not subscription else {
                    "subscription_id": subscription.subscription_id,
                    "status": subscription.status,
                    "tier": subscription.tier,
                    "monthly_quota": subscription.monthly_quota,
                },
            }

    def list_reservations(self, external_user_id: str) -> list[dict] | None:
        with Session(self.engine) as session:
            user = session.get(cultpass.User, external_user_id)
            if not user:
                return None
            rows = session.scalars(
                select(cultpass.Reservation)
                .options(joinedload(cultpass.Reservation.experience))
                .where(cultpass.Reservation.user_id == external_user_id)
            ).all()
            return [
                {
                    "reservation_id": row.reservation_id,
                    "status": row.status,
                    "experience_id": row.experience_id,
                    "title": row.experience.title,
                    "location": row.experience.location,
                    "when": row.experience.when.isoformat(),
                    "is_premium": bool(row.experience.is_premium),
                }
                for row in rows
            ]

    def update_subscription(self, external_user_id: str, action: str) -> dict:
        transitions = {"cancel": "cancelled", "pause": "paused", "reactivate": "active"}
        if action not in transitions:
            raise ValueError(f"Unsupported subscription action: {action}")
        with Session(self.engine) as session, session.begin():
            user = session.scalar(
                select(cultpass.User)
                .options(joinedload(cultpass.User.subscription))
                .where(cultpass.User.user_id == external_user_id)
            )
            if not user:
                raise LookupError("Customer was not found")
            if user.is_blocked:
                raise PermissionError("Blocked accounts require Trust and Safety review")
            if not user.subscription:
                raise LookupError("Customer has no subscription")
            previous = user.subscription.status
            user.subscription.status = transitions[action]
            user.subscription.ended_at = datetime.now(UTC).replace(tzinfo=None) if action == "cancel" else None
            return {
                "subscription_id": user.subscription.subscription_id,
                "previous_status": previous,
                "status": user.subscription.status,
                "action": action,
            }


class CoreRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()
        self.engine = _engine(self.db_path)

    def search_knowledge(self, account_id: str, query: str, limit: int = 3) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(udahub.Knowledge).where(udahub.Knowledge.account_id == account_id)
            ).all()
            articles = [
                {"article_id": row.article_id, "title": row.title, "content": row.content, "tags": row.tags or ""}
                for row in rows
            ]
        return rank_articles(query, articles, limit)

    def load_customer_context(self, account_id: str, external_user_id: str, limit: int = 8) -> dict:
        with Session(self.engine) as session:
            user = session.scalar(
                select(udahub.User).where(
                    udahub.User.account_id == account_id,
                    udahub.User.external_user_id == external_user_id,
                )
            )
            if not user:
                return {"memories": [], "recent_messages": [], "prior_ticket_count": 0}
            memories = session.scalars(
                select(udahub.CustomerMemory)
                .where(udahub.CustomerMemory.user_id == user.user_id)
                .order_by(udahub.CustomerMemory.created_at.desc())
                .limit(limit)
            ).all()
            messages = session.scalars(
                select(udahub.TicketMessage)
                .join(udahub.Ticket)
                .where(udahub.Ticket.user_id == user.user_id)
                .order_by(udahub.TicketMessage.created_at.desc())
                .limit(limit)
            ).all()
            ticket_count = len(user.tickets)
            return {
                "memories": [{"kind": row.kind, "content": row.content, "ticket_id": row.source_ticket_id} for row in memories],
                "recent_messages": [{"role": row.role.value, "content": row.content} for row in reversed(messages)],
                "prior_ticket_count": ticket_count,
            }

    def persist_interaction(
        self,
        ticket: dict,
        *,
        classification: dict,
        outcome: str,
        response: str,
        confidence: float,
        sources: list[dict],
    ) -> None:
        with Session(self.engine) as session, session.begin():
            account = session.get(udahub.Account, ticket["account_id"])
            if not account:
                raise LookupError(f"Unknown account: {ticket['account_id']}")
            user = session.scalar(
                select(udahub.User).where(
                    udahub.User.account_id == ticket["account_id"],
                    udahub.User.external_user_id == ticket["external_user_id"],
                )
            )
            if not user:
                user = udahub.User(
                    user_id=str(uuid.uuid4()),
                    account_id=ticket["account_id"],
                    external_user_id=ticket["external_user_id"],
                    user_name=ticket.get("user_name") or "Unknown customer",
                )
                session.add(user)
                session.flush()

            db_ticket = session.get(udahub.Ticket, ticket["ticket_id"])
            if not db_ticket:
                db_ticket = udahub.Ticket(
                    ticket_id=ticket["ticket_id"], account_id=ticket["account_id"],
                    user_id=user.user_id, channel=ticket.get("channel", "chat"),
                )
                session.add(db_ticket)
                session.flush()
                session.add(udahub.TicketMetadata(
                    ticket_id=db_ticket.ticket_id, status=outcome,
                    main_issue_type=classification.get("category"),
                    tags=",".join(classification.get("signals", [])),
                    urgency=classification.get("urgency", "normal"),
                    resolution_confidence=f"{confidence:.4f}",
                ))
            else:
                metadata = db_ticket.ticket_metadata
                metadata.status = outcome
                metadata.main_issue_type = classification.get("category")
                metadata.urgency = classification.get("urgency", "normal")
                metadata.resolution_confidence = f"{confidence:.4f}"

            session.add_all([
                udahub.TicketMessage(message_id=str(uuid.uuid4()), ticket_id=db_ticket.ticket_id,
                                     role=udahub.RoleEnum.user, content=ticket["text"]),
                udahub.TicketMessage(message_id=str(uuid.uuid4()), ticket_id=db_ticket.ticket_id,
                                     role=udahub.RoleEnum.ai, content=response),
            ])

            preference = _extract_preference(ticket["text"])
            if preference:
                self._add_memory(session, user, ticket, "preference", preference)
            if outcome == "resolved":
                titles = ", ".join(source["title"] for source in sources[:2]) or "operational account data"
                content = f"Resolved {classification.get('category', 'general')} issue using {titles}."
                self._add_memory(session, user, ticket, "resolution", content)

    @staticmethod
    def _add_memory(session: Session, user: udahub.User, ticket: dict, kind: str, content: str) -> None:
        existing = session.scalar(select(udahub.CustomerMemory).where(
            udahub.CustomerMemory.user_id == user.user_id,
            udahub.CustomerMemory.kind == kind,
            udahub.CustomerMemory.content == content,
        ))
        if not existing:
            session.add(udahub.CustomerMemory(
                memory_id=str(uuid.uuid4()), account_id=ticket["account_id"], user_id=user.user_id,
                kind=kind, content=content, source_ticket_id=ticket["ticket_id"],
            ))


def _extract_preference(text: str) -> str | None:
    lowered = text.lower()
    channels = ("email", "phone", "chat", "text message", "sms")
    if "prefer" in lowered or "contact me by" in lowered:
        for channel in channels:
            if channel in lowered:
                return f"Customer prefers contact by {channel}."
    return None
