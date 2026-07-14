"""SQLAlchemy ORM models for the estimator persistence layer."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for Alembic metadata and ORM models."""

    pass
