import pytest

@pytest.mark.asyncio
async def test_models_endpoint_returns_configured_models(make_client):
    async with make_client() as client:
        response = await client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    model_ids = [m["id"] for m in data.get("data", [])]
    assert "gpt-4o" in model_ids
    assert "gpt-4o-mini" in model_ids
    assert "deepseek-chat" in model_ids


@pytest.mark.asyncio
async def test_chat_completions_requires_model(make_client):
    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "model is required"


@pytest.mark.asyncio
async def test_chat_completions_requires_messages(make_client):
    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o-mini"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "messages is required"


@pytest.mark.asyncio
async def test_chat_completions_resolves_model_alias(make_client, monkeypatch):
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
                "temperature": 0.2,
            },
        )

    assert response.status_code == 200
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["temperature"] == 0.2


@pytest.mark.asyncio
async def test_streaming_chat_completions_passes_stream_once(make_client, monkeypatch):
    captured = {}

    async def fake_acompletion(*, model, messages, stream=False, **kwargs):
        captured.update(
            {
                "model": model,
                "messages": messages,
                "stream": stream,
                "extra_kwargs": kwargs,
            }
        )

        async def chunks():
            yield {"choices": [{"delta": {"content": "hello"}}]}

        return chunks()

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
                "temperature": 0.2,
            },
        )

    assert response.status_code == 200
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["stream"] is True
    assert "stream" not in captured["extra_kwargs"]
    assert "data: [DONE]" in response.text
