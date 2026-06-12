import pytest

@pytest.mark.asyncio
async def test_health_returns_200(make_client):
    async with make_client() as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_readiness_returns_ready_when_required_keys_are_set(make_client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")

    async with make_client() as client:
        response = await client.get("/readiness")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_returns_503_when_required_keys_are_missing(make_client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    async with make_client() as client:
        response = await client.get("/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "missing_env_vars": ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
    }
