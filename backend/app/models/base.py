"""Base model class and database session configuration."""

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

# Naming convention for constraints (helps with migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


def enum_column(enum_class: type, pg_name: str, **kwargs: object) -> SAEnum:
    """Create an Enum column that uses Python enum .value (not .name) for DB storage."""
    return SAEnum(
        enum_class,
        name=pg_name,
        values_callable=lambda x: [e.value for e in x],
        **kwargs,
    )


class Base(DeclarativeBase):
    """Base class for all models."""

    metadata = metadata


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Async engine and session
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with async_session_maker() as session:
        yield session
