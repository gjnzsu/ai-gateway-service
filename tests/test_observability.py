import json
import logging

import pytest


def _chat_log_payloads(caplog):
    payloads = []
    for record in caplog.records:
        try:
            payload = json.loads(record.getMessage())
        except json.JSONDecodeError:
            continue
        if payload.get("event") == "chat_completion":
            payloads.append(payload)
    return payloads


@pytest.mark.asyncio
async def test_chat_completion_logs_structured_success_fields(
    make_client, monkeypatch, caplog
):
    async def fake_acompletion(**kwargs):
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
            },
        }

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={
                "X-Request-ID": "req-ai-market-001",
                "X-Consumer-Service": "ai-market-studio",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["request_id"] == "req-ai-market-001"
    assert payload["consumer"] == "ai-market-studio"
    assert payload["model"] == "gpt-4o-mini"
    assert payload["resolved_model"] == "openai/gpt-4o-mini"
    assert payload["status_code"] == 200
    assert payload["error_type"] is None
    assert payload["latency_ms"] >= 0
    assert payload["usage"] == {
        "prompt_tokens": 12,
        "completion_tokens": 5,
        "total_tokens": 17,
    }


@pytest.mark.asyncio
async def test_chat_completion_without_observability_headers_remains_compatible(
    make_client, monkeypatch, caplog
):
    upstream_response = {"id": "chatcmpl-test", "object": "chat.completion"}

    async def fake_acompletion(**kwargs):
        return upstream_response

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json() == upstream_response
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["request_id"]
    assert payload["consumer"] == "unknown"


@pytest.mark.asyncio
async def test_streaming_chat_completion_logs_metadata(make_client, monkeypatch, caplog):
    async def fake_acompletion(*, model, messages, stream=False, **kwargs):
        async def chunks():
            yield {"choices": [{"delta": {"content": "hello"}}]}

        return chunks()

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Consumer-Service": "ai-market-studio"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    assert "data: [DONE]" in response.text
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["consumer"] == "ai-market-studio"
    assert payload["model"] == "gpt-4o-mini"
    assert payload["resolved_model"] == "openai/gpt-4o-mini"
    assert payload["status_code"] == 200
    assert payload["usage"] is None


@pytest.mark.asyncio
async def test_chat_completion_validation_error_logs_structured_failure(
    make_client, caplog
):
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Request-ID": "req-validation-001"},
            json={"messages": [{"role": "user", "content": "hello"}]},
        )

    assert response.status_code == 400
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["request_id"] == "req-validation-001"
    assert payload["consumer"] == "unknown"
    assert payload["model"] is None
    assert payload["resolved_model"] is None
    assert payload["status_code"] == 400
    assert payload["error_type"] == "validation_error"
    assert payload["latency_ms"] >= 0
