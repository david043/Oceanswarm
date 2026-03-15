"""Integration tests for the FastAPI routes using an in-memory SQLite DB."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.database import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_agent(client):
    response = await client.post("/agents/", json={"name": "Mira", "age": 28, "gender": "female"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mira"
    assert data["age"] == 28
    assert "id" in data


async def test_list_agents_empty(client):
    response = await client.get("/agents/")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_agents(client):
    await client.post("/agents/", json={"name": "Mira"})
    await client.post("/agents/", json={"name": "Kael"})
    response = await client.get("/agents/")
    assert len(response.json()) == 2


async def test_get_agent(client):
    create_resp = await client.post("/agents/", json={"name": "Mira"})
    agent_id = create_resp.json()["id"]
    response = await client.get(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Mira"


async def test_get_agent_not_found(client):
    response = await client.get("/agents/nonexistent-id")
    assert response.status_code == 404


async def test_delete_agent(client):
    create_resp = await client.post("/agents/", json={"name": "Mira"})
    agent_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/agents/{agent_id}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/agents/{agent_id}")
    assert get_resp.status_code == 404


async def test_create_predefined_event(client):
    response = await client.post("/world/events", json={"event_type": "storm"})
    assert response.status_code == 201
    data = response.json()
    assert data["event_type"] == "storm"
    assert "storm" in data["description"].lower()


async def test_create_custom_event(client):
    response = await client.post(
        "/world/events",
        json={"event_type": "custom", "description": "A comet is visible in the sky."},
    )
    assert response.status_code == 201


async def test_create_unknown_event_without_description(client):
    response = await client.post("/world/events", json={"event_type": "unknown_event"})
    assert response.status_code == 400


async def test_simulation_status(client):
    response = await client.get("/simulation/status")
    assert response.status_code == 200
    data = response.json()
    assert "current_tick" in data
    assert "is_running" in data
