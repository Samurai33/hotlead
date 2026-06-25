import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db

# Usa a mesma DB do docker ou uma de teste se definida
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://hotlead:91798a77327350340aeb63ab211a46e3@localhost:5432/hotlead"
)
TEST_API_KEY = "test-api-key-1234"


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(TEST_DB_URL, echo=False)
    async with e.begin() as conn:
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
async def client(db):
    def override_get_db():
        yield db

    os.environ["API_KEY"] = TEST_API_KEY
    os.environ["SECRET_KEY"] = "test-secret-key-for-ci"
    os.environ["POSTGRES_PASSWORD"] = "test"
    os.environ["DATABASE_URL"] = TEST_DB_URL

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
