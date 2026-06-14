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


@pytest.fixture(autouse=True)
def clear_circuit_state():
    import app.main

    app.main._circuit_breakers.clear()
    yield
    app.main._circuit_breakers.clear()


@pytest.mark.asyncio
async def test_provider_retry_succeeds(make_client, monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise RuntimeError("transient provider failure")
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main.asyncio.sleep", fake_sleep)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert calls == ["openai/gpt-4o-mini", "openai/gpt-4o-mini"]


@pytest.mark.asyncio
async def test_primary_failure_falls_back_to_configured_model(make_client, monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs["model"])
        if kwargs["model"] == "openai/gpt-4o":
            raise RuntimeError("primary unavailable")
        return {"id": "fallback-response", "object": "chat.completion"}

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main.asyncio.sleep", fake_sleep)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == "fallback-response"
    assert calls == [
        "openai/gpt-4o",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
    ]


@pytest.mark.asyncio
async def test_open_circuit_skips_primary_and_uses_fallback(make_client, monkeypatch):
    import app.main

    calls = []
    app.main._open_circuit("openai/gpt-4o")

    async def fake_acompletion(**kwargs):
        calls.append(kwargs["model"])
        return {"id": "fallback-response", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert calls == ["openai/gpt-4o-mini"]


@pytest.mark.asyncio
async def test_half_open_success_closes_circuit(make_client, monkeypatch):
    import app.main

    app.main._open_circuit("openai/gpt-4o-mini", opened_at=0)

    async def fake_acompletion(**kwargs):
        return {"id": "probe-success", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main.time.time", lambda: 999999)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert app.main._circuit_breakers["openai/gpt-4o-mini"]["state"] == "closed"


@pytest.mark.asyncio
async def test_half_open_failure_reopens_circuit(make_client, monkeypatch):
    import app.main

    app.main._open_circuit("openai/gpt-4o-mini", opened_at=0)

    async def fake_acompletion(**kwargs):
        raise RuntimeError("probe failed")

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.main.time.time", lambda: 999999)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 500
    assert app.main._circuit_breakers["openai/gpt-4o-mini"]["state"] == "open"


@pytest.mark.asyncio
async def test_reliability_metadata_is_logged_for_fallback(
    make_client, monkeypatch, caplog
):
    async def fake_acompletion(**kwargs):
        if kwargs["model"] == "openai/gpt-4o":
            raise RuntimeError("primary unavailable")
        return {"id": "fallback-response", "object": "chat.completion"}

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    monkeypatch.setattr("app.main.asyncio.sleep", fake_sleep)
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["resolved_model"] == "openai/gpt-4o-mini"
    assert payload["reliability"]["fallback_from_model"] == "openai/gpt-4o"
    assert payload["reliability"]["attempt_count"] == 3
    assert payload["reliability"]["circuit_state"] == "closed"


@pytest.mark.asyncio
async def test_existing_ai_market_studio_request_shape_still_works(
    make_client, monkeypatch
):
    async def fake_acompletion(**kwargs):
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Consumer-Service": "ai-market-studio"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json() == {"id": "chatcmpl-test", "object": "chat.completion"}
