"""Shared pytest fixtures for integration tests.

Integration tests require a running PostgreSQL database.
Set TEST_DATABASE_URL env var to point to a test database, or use:
    docker compose run --rm api pytest tests/integration/ -v
"""
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://car_finder:car_finder@db:5432/car_finder_test",
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    """FastAPI test client with the DB session overridden."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_source(engine):
    """Ensure the otomoto source row exists for tests."""
    from sqlalchemy import text

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO sources (slug, display_name, base_url, is_active) "
                "VALUES ('otomoto', 'OTOMOTO', 'https://www.otomoto.pl', TRUE) "
                "ON CONFLICT (slug) DO NOTHING"
            )
        )
        await session.commit()
