from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass



engine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.database_pool_size,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)



celery_engine = create_async_engine(
    str(settings.database_url),
    poolclass=NullPool,
    echo=settings.debug,
    pool_pre_ping=True,
)

celery_session_maker = async_sessionmaker(
    bind=celery_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Закрыть все соединения с БД (используется при остановке приложения)."""
    await engine.dispose()
    await celery_engine.dispose()
