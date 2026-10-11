"""UDA-Hub core schema for account data, tickets, knowledge, and memory."""

from __future__ import annotations

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    account_id = Column(String, primary_key=True)
    account_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("User", back_populates="account")
    tickets = relationship("Ticket", back_populates="account")
    knowledge_articles = relationship("Knowledge", back_populates="account")
    memories = relationship("CustomerMemory", back_populates="account")


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    external_user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    account = relationship("Account", back_populates="users")
    tickets = relationship("Ticket", back_populates="user")
    memories = relationship("CustomerMemory", back_populates="user")
    __table_args__ = (
        UniqueConstraint("account_id", "external_user_id", name="uq_user_external_per_account"),
    )


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    channel = Column(String, nullable=False, default="chat")
    created_at = Column(DateTime, default=func.now(), nullable=False)

    account = relationship("Account", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    ticket_metadata = relationship("TicketMetadata", uselist=False, back_populates="ticket")
    messages = relationship("TicketMessage", back_populates="ticket", order_by="TicketMessage.created_at")


class TicketMetadata(Base):
    __tablename__ = "ticket_metadata"
    ticket_id = Column(String, ForeignKey("tickets.ticket_id"), primary_key=True)
    status = Column(String, nullable=False)
    main_issue_type = Column(String)
    tags = Column(Text)
    urgency = Column(String, nullable=False, default="normal")
    resolution_confidence = Column(String)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    ticket = relationship("Ticket", back_populates="ticket_metadata")


class RoleEnum(enum.Enum):
    user = "user"
    agent = "agent"
    ai = "ai"
    system = "system"


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    message_id = Column(String, primary_key=True)
    ticket_id = Column(String, ForeignKey("tickets.ticket_id"), nullable=False)
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    ticket = relationship("Ticket", back_populates="messages")


class Knowledge(Base):
    __tablename__ = "knowledge"
    article_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    account = relationship("Account", back_populates="knowledge_articles")


class CustomerMemory(Base):
    """Durable cross-session fact associated with a customer."""

    __tablename__ = "customer_memories"
    memory_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    kind = Column(String, nullable=False)  # preference or resolution
    content = Column(Text, nullable=False)
    source_ticket_id = Column(String)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    account = relationship("Account", back_populates="memories")
    user = relationship("User", back_populates="memories")

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "content", name="uq_memory_fact"),
    )
