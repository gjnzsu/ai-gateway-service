from unittest.mock import AsyncMock

import pytest

import app.main as gateway


@pytest.mark.asyncio
async def test_embeddings_preserves_vectors_usage_and_attribution(make_client, monkeypatch):
    payload = {'object': 'list', 'model': 'text-embedding-3-small',
               'data': [{'index': 0, 'object': 'embedding', 'embedding': [0.1, 0.2]}],
               'usage': {'prompt_tokens': 2, 'total_tokens': 2}}
    provider = AsyncMock(return_value=payload)
    metric = AsyncMock()
    monkeypatch.setattr(gateway.litellm, 'aembedding', provider)
    monkeypatch.setattr(gateway, '_send_observability_metric', metric)
    async with make_client() as client:
        response = await client.post('/v1/embeddings', json={
            'model': 'text-embedding-3-small', 'input': ['hello'], 'encoding_format': 'float'},
            headers={'x-consumer-service': 'ai-rag-service', 'x-request-id': 'rag-123'})
    assert response.status_code == 200
    assert response.json() == payload
    assert provider.call_args.kwargs['model'] == 'openai/text-embedding-3-small'
    assert provider.call_args.kwargs['input'] == ['hello']
    assert metric.call_args.kwargs['request_id'] == 'rag-123'
    assert metric.call_args.kwargs['attribution']['consumer'] == 'ai-rag-service'


@pytest.mark.asyncio
@pytest.mark.parametrize('body', [
    {'model': 'text-embedding-3-small', 'input': []},
    {'model': 'unknown-model', 'input': ['hello']},
    {'model': 'text-embedding-3-small', 'input': ['hello'], 'api_base': 'https://evil.invalid'},
    {'model': 'text-embedding-3-small', 'input': ['hello'], 'encoding_format': {}},
    {'model': 'text-embedding-3-small', 'input': ['hello'], 'dimensions': True},
])
async def test_embeddings_rejects_invalid_input_before_provider(make_client, monkeypatch, body):
    provider = AsyncMock()
    monkeypatch.setattr(gateway.litellm, 'aembedding', provider)
    async with make_client() as client:
        response = await client.post('/v1/embeddings', json=body)
    assert response.status_code == 400
    provider.assert_not_called()


@pytest.mark.asyncio
async def test_embeddings_failure_does_not_fallback_or_leak(make_client, monkeypatch):
    provider = AsyncMock(side_effect=RuntimeError('secret-provider-key'))
    monkeypatch.setattr(gateway.litellm, 'aembedding', provider)
    async with make_client() as client:
        response = await client.post('/v1/embeddings', json={
            'model': 'text-embedding-3-small', 'input': ['hello']})
    assert response.status_code == 502
    assert 'secret-provider-key' not in response.text
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_service_token_rejects_before_provider(make_client, monkeypatch):
    monkeypatch.setenv('AI_GATEWAY_SERVICE_TOKEN', 'gateway-secret')
    provider = AsyncMock(return_value={'object': 'list', 'data': []})
    monkeypatch.setattr(gateway.litellm, 'aembedding', provider)
    body = {'model': 'text-embedding-3-small', 'input': ['hello']}
    async with make_client() as client:
        denied = await client.post('/v1/embeddings', json=body)
        assert denied.status_code == 401
        provider.assert_not_called()
        allowed = await client.post('/v1/embeddings', json=body,
                                   headers={'authorization': 'Bearer gateway-secret'})
    assert allowed.status_code == 200


def test_openai_sdk_embedding_contract(monkeypatch):
    import httpx
    from openai import OpenAI
    from fastapi.testclient import TestClient

    provider = AsyncMock(return_value={
        'object': 'list', 'model': 'text-embedding-3-small',
        'data': [{'object': 'embedding', 'index': 0, 'embedding': [0.1, 0.2]}],
        'usage': {'prompt_tokens': 1, 'total_tokens': 1}})
    monkeypatch.setattr(gateway.litellm, 'aembedding', provider)
    monkeypatch.setenv('AI_GATEWAY_SERVICE_TOKEN', 'gateway-secret')
    with TestClient(gateway.app) as gateway_client:
        def dispatch(request):
            return gateway_client.request(request.method, request.url.path,
                                          content=request.content, headers=dict(request.headers))

        with OpenAI(base_url='http://gateway.test/v1', api_key='gateway-secret',
                    http_client=httpx.Client(transport=httpx.MockTransport(dispatch))) as client:
            result = client.embeddings.create(model='text-embedding-3-small', input=['hello'])
    assert result.data[0].embedding == [0.1, 0.2]
    assert result.usage.total_tokens == 1
    assert provider.call_args.kwargs['encoding_format'] == 'base64'
