"""Tests for the database ORM base used by Alembic target_metadata."""

from app.db import Base as PackageBase
from app.db.models import Base


def test_declarative_base_exports_metadata() -> None:
    """Base must expose empty metadata for Alembic until models are added."""
    assert Base.metadata is not None
    assert PackageBase is Base
    assert list(Base.metadata.tables) == []
