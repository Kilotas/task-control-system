import asyncio
import os
from datetime import date, datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.data.models.base import Base
from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.work_center import WorkCenter


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres-test:5432/production_control_test"
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    yield session_maker

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    async with test_db() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_uow(test_db):
    from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
    return SqlAlchemyUnitOfWork(test_db)


@pytest_asyncio.fixture
async def test_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=None)
    cache.delete = AsyncMock(return_value=None)
    cache.delete_pattern = AsyncMock(return_value=None)
    return cache


@pytest_asyncio.fixture
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    from src.main import app
    from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
    from src.core.dependencies import get_uow

    def override_get_uow():
        return SqlAlchemyUnitOfWork(test_db)

    app.dependency_overrides[get_uow] = override_get_uow

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_work_center(test_session) -> WorkCenter:
    wc = WorkCenter(identifier="WC-001", name="Test Work Center")
    test_session.add(wc)
    await test_session.commit()
    await test_session.refresh(wc)
    return wc


@pytest_asyncio.fixture
async def sample_batch(test_db, sample_work_center) -> Batch:
    async with test_db() as session:
        batch = Batch(
            batch_number=1001,
            batch_date=date.today(),
            work_center_id=sample_work_center.id,
            shift="1",
            team="A",
            task_description="Test task description",
            nomenclature="Test nomenclature",
            ekn_code="EKN001",
            shift_start=datetime.now(),
            shift_end=datetime.now() + timedelta(hours=8),
            is_closed=False,
        )
        session.add(batch)
        await session.commit()
        await session.refresh(batch)
        return batch


@pytest_asyncio.fixture
async def sample_products(test_db, sample_batch) -> list[Product]:
    async with test_db() as session:
        products = []
        for i in range(10):
            product = Product(
                batch_id=sample_batch.id,
                unique_code=f"PROD-{i:04d}",
                is_aggregated=i < 5,
            )
            products.append(product)

        session.add_all(products)
        await session.commit()

        for p in products:
            await session.refresh(p)

        return products
