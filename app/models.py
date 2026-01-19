from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    decks: Mapped[list["Deck"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="decks")
    cards: Mapped[list["Card"]] = relationship(back_populates="deck", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    front: Mapped[str] = mapped_column(String, nullable=False)
    back: Mapped[str] = mapped_column(String, nullable=False)

    deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)

    deck: Mapped["Deck"] = relationship(back_populates="cards")