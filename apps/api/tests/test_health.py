import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orq-api"


@pytest.mark.asyncio
async def test_root_returns_200(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_version_returns_version(client):
    response = await client.get("/api/v1/version/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "name" in data
