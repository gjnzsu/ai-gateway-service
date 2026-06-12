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
async def test_allowed_model_policy_is_logged(make_client, monkeypatch, caplog):
    async def fake_acompletion(**kwargs):
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    caplog.set_level(logging.INFO, logger="app.main")

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
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["policy_mode"] == "log_only"
    assert payload["policy_allowed"] is True
    assert payload["policy_reason"] == "model_allowed"


@pytest.mark.asyncio
async def test_disallowed_model_policy_is_logged_but_not_enforced(
    make_client, monkeypatch, caplog
):
    async def fake_acompletion(**kwargs):
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"X-Consumer-Service": "unknown-limited-service"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["policy_mode"] == "log_only"
    assert payload["policy_allowed"] is False
    assert payload["policy_reason"] == "model_not_allowed"


@pytest.mark.asyncio
async def test_missing_consumer_uses_default_policy(make_client, monkeypatch, caplog):
    async def fake_acompletion(**kwargs):
        return {"id": "chatcmpl-test", "object": "chat.completion"}

    monkeypatch.setattr("app.main.acompletion", fake_acompletion)
    caplog.set_level(logging.INFO, logger="app.main")

    async with make_client() as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    payload = _chat_log_payloads(caplog)[-1]
    assert payload["consumer"] == "unknown"
    assert payload["policy_mode"] == "log_only"
    assert payload["policy_allowed"] is True
    assert payload["policy_reason"] == "model_allowed"


@pytest.mark.asyncio
async def test_ai_market_studio_existing_request_shape_still_works(
    make_client, monkeypatch
):
    upstream_response = {"id": "chatcmpl-test", "object": "chat.completion"}

    async def fake_acompletion(**kwargs):
        return upstream_response

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
    assert response.json() == upstream_response
