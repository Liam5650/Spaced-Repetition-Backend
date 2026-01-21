from sqlalchemy import ForeignKey, Integer, String, DateTime, Float, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from datetime import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    decks: Mapped[list["Deck"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Index based on user to quickly find all decks belonging to a user
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="decks")
    cards: Mapped[list["Card"]] = relationship(back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    front: Mapped[str] = mapped_column(String, nullable=False)
    back: Mapped[str] = mapped_column(String, nullable=False)

    # Index based on deck to quickly find all cards belonging to a deck
    deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("decks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Denormalized learned flag for fast "new cards" queries
    is_learned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    deck: Mapped["Deck"] = relationship(back_populates="cards")
    schedule: Mapped["CardSchedule | None"] = relationship(back_populates="card", uselist=False, cascade="all, delete-orphan", single_parent=True)
    review_history: Mapped[list["ReviewHistory"]] = relationship(back_populates="card", cascade="all, delete-orphan")

    # Composite index to efficiently query new cards by deck
    __table_args__ = (Index("ix_cards_deck_id_is_learned_id", "deck_id", "is_learned", "id"),)

class CardSchedule(Base):
    __tablename__ = "card_schedules"

    # 1:1 Card to CardSchedule relationship, must have an associated card to exist
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)

    # Denormalized deck for fast due queries at scale
    deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)

    # SM-2 algo needed values
    repetition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)

    # Essential
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Nice to haves
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    card: Mapped["Card"] = relationship(back_populates="schedule")

    # Composite index to efficiently query due cards by deck and review time
    __table_args__ = (Index("ix_card_schedules_deck_next_review", "deck_id", "next_review_at"),)


class ReviewHistory(Base):
    __tablename__ = "review_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)

    # History for deterministic reproducibility
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    quality: Mapped[int] = mapped_column(Integer, nullable=False)

    # Sorted card review history
    __table_args__ = (Index("ix_review_history_card_id_reviewed_at_desc", "card_id", reviewed_at.desc()),)

    # Nice to haves
    repetition_before: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_before: Mapped[int] = mapped_column(Integer, nullable=False)
    ease_before: Mapped[float] = mapped_column(Float, nullable=False)
    repetition_after: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_after: Mapped[int] = mapped_column(Integer, nullable=False)
    ease_after: Mapped[float] = mapped_column(Float, nullable=False)
    next_review_at_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    card: Mapped["Card"] = relationship(back_populates="review_history")