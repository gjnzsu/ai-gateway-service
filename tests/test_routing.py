# tests/test_routing.py
import httpx
import pytest

BASE_URL = "http://localhost:4000"

@pytest.mark.asyncio
async def test_models_endpoint_returns_configured_models():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/models")
    assert response.status_code == 200
    data = response.json()
    model_ids = [m["id"] for m in data.get("data", [])]
    assert "gpt-4o" in model_ids or "gpt-4o-mini" in model_ids
    assert "deepseek-chat" in model_ids
