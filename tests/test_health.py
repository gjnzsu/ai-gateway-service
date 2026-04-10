# tests/test_health.py
import httpx
import pytest

BASE_URL = "http://localhost:4000"

@pytest.mark.asyncio
async def test_health_returns_200():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_readiness_checks_openai_key():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/readiness")
    # Returns 200 if keys are configured, 503 if missing
    assert response.status_code in (200, 503)
