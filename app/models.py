"""SQLAlchemy declarative ORM models for Users, Books, and Notes."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

try:
    from app.database import Base
except ModuleNotFoundError:
    from database import Base


class User(Base):
    """User account model supporting role-based access control and relationships."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)

    # Relational joins
    books = relationship(
        "Book",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notes = relationship(
        "Note",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Book(Base):
    """Book model representing inventory items in the bookstore."""

    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    price = Column(Float, nullable=False)
    genre = Column(String(100), nullable=False, index=True)
    stock = Column(Integer, nullable=False, default=0)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relational join to User
    owner = relationship("User", back_populates="books", lazy="selectin")


class Note(Base):
    """Relational model demonstrating user notes with foreign key and joins."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relational join to User
    user = relationship("User", back_populates="notes", lazy="selectin")

