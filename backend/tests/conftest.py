import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app import create_app
from app.core.database import Base, get_db

TEST_DATABASE_URL = "postgresql+asyncpg://testplatform:testplatform@localhost:5433/testplatform_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    session_local = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_local() as session:
        yield session


@pytest.fixture
async def client(async_engine):
    app = create_app()

    async def override_get_db():
        session_local = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client: AsyncClient):
    await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    yield client
