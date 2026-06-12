import pytest


@pytest.mark.asyncio
async def test_observability_ingestion_is_skipped_when_url_is_unset(
    make_client, monkeypatch
):
    calls = []

    async def fake_acompletion(**kwargs):
        return {"id": "chatcmpl-test", "usage": {"prompt_tokens": 3, "completion_tokens": 2}}

    async def fake_post_observability_metric(payload):
        calls.append(payload)

    monkeypatch.delenv("OBSERVABILITY_URL", raising=False)
    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main._post_observability_metric", fake_post_observability_metric)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert calls == []


@pytest.mark.asyncio
async def test_non_streaming_success_sends_llm_call_metric(make_client, monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        return {
            "id": "chatcmpl-test",
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
            },
        }

    async def fake_post_observability_metric(payload):
        calls.append(payload)

    monkeypatch.setenv("OBSERVABILITY_URL", "http://observability.test")
    monkeypatch.setenv("OBSERVABILITY_SERVICE_NAME", "ai-gateway-service")
    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main._post_observability_metric", fake_post_observability_metric)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Request-ID": "req-success-001"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert len(calls) == 1
    payload = calls[0]
    assert payload["service_name"] == "ai-gateway-service"
    assert payload["metric_type"] == "llm_call"
    assert payload["trace_id"] == "req-success-001"
    assert payload["data"]["provider"] == "openai"
    assert payload["data"]["model"] == "gpt-4o-mini"
    assert payload["data"]["prompt_tokens"] == 12
    assert payload["data"]["completion_tokens"] == 5
    assert payload["data"]["duration_seconds"] >= 0
    assert payload["data"]["status"] == "success"
    assert payload["data"]["error_type"] is None


@pytest.mark.asyncio
async def test_streaming_success_sends_zero_token_metric(make_client, monkeypatch):
    calls = []

    async def fake_acompletion(*, model, messages, stream=False, **kwargs):
        async def chunks():
            yield {"choices": [{"delta": {"content": "hello"}}]}

        return chunks()

    async def fake_post_observability_metric(payload):
        calls.append(payload)

    monkeypatch.setenv("OBSERVABILITY_URL", "http://observability.test")
    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main._post_observability_metric", fake_post_observability_metric)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Request-ID": "req-stream-001"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    payload = calls[0]
    assert payload["trace_id"] == "req-stream-001"
    assert payload["data"]["provider"] == "deepseek"
    assert payload["data"]["model"] == "deepseek-chat"
    assert payload["data"]["prompt_tokens"] == 0
    assert payload["data"]["completion_tokens"] == 0
    assert payload["data"]["status"] == "success"


@pytest.mark.asyncio
async def test_provider_error_sends_error_metric(make_client, monkeypatch):
    calls = []

    class ProviderFailure(Exception):
        pass

    async def fake_acompletion(**kwargs):
        raise ProviderFailure("provider unavailable")

    async def fake_post_observability_metric(payload):
        calls.append(payload)

    monkeypatch.setenv("OBSERVABILITY_URL", "http://observability.test")
    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main._post_observability_metric", fake_post_observability_metric)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Request-ID": "req-error-001"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 500
    payload = calls[0]
    assert payload["trace_id"] == "req-error-001"
    assert payload["data"]["provider"] == "openai"
    assert payload["data"]["model"] == "gpt-4o-mini"
    assert payload["data"]["status"] == "error"
    assert payload["data"]["error_type"] == "internal_error"


@pytest.mark.asyncio
async def test_observability_ingestion_failure_does_not_change_response(
    make_client, monkeypatch
):
    async def fake_acompletion(**kwargs):
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    async def fake_post_observability_metric(payload):
        raise RuntimeError("observability down")

    monkeypatch.setenv("OBSERVABILITY_URL", "http://observability.test")
    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main._post_observability_metric", fake_post_observability_metric)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json() == {"id": "chatcmpl-test", "object": "chat.completion"}
