import asyncio
import importlib
import json

import pytest


def module():
    spec = importlib.util.find_spec('app.finops')
    assert spec is not None, 'FinOps module is missing'
    return importlib.import_module('app.finops')


def test_attribution_and_unique_calls():
    f = module()
    h = {'x-ai-agent-id': 'writer', 'x-ai-run-id': 'run-1'}
    a, b = f.context(h), f.context(h)
    assert a['trace_id'] == b['trace_id'] and len(a['trace_id']) == 32
    assert a['call_id'] != b['call_id']
    assert f.context({'x-ai-agent-id': 'unsafe secret!', 'x-ai-run-id': 'r'})['attribution_status'] == 'unattributed'
    assert 'unsafe secret!' not in json.dumps(f.context({'x-ai-agent-id': 'unsafe secret!', 'x-ai-run-id': 'r'}))


def test_cache_and_long_context_cost():
    f = module()
    usage = {'prompt_tokens': 300000, 'completion_tokens': 1000, 'prompt_tokens_details': {'cached_tokens': 100000}, 'completion_tokens_details': {'reasoning_tokens': 700}}
    r = f.record(f.context({}), 'openai/gpt-5.4', usage, 1, 2, 'success')
    assert abs(r['cost_details']['total'] - 1.0725) < 1e-12
    assert r['usage_details']['input_cached_tokens'] == 100000
    assert r['usage_details']['output_reasoning_tokens'] == 700
    assert r['cost_status'] == 'known'


def test_unknown_usage_never_zero():
    f = module()
    for usage in [None, {}, {'prompt_tokens': -1, 'completion_tokens': 1}, {'prompt_tokens': True, 'completion_tokens': 1}]:
        r = f.record(f.context({}), 'openai/gpt-5.4', usage, 1, 2, 'error')
        assert r['cost_details'] is None and r['cost_status'] == 'unknown'
    assert f.record(f.context({}), 'custom/model', {'prompt_tokens': 1, 'completion_tokens': 1}, 1, 2, 'success')['cost_details'] is None


def test_export_unknown_omits_model_and_cost():
    f = module()
    calls = []
    class Observation:
        def update(self, **kw): calls.append(kw)
        def end(self, **kw): calls.append(kw)
    class Client:
        def start_observation(self, **kw):
            calls.append(kw)
            return Observation()
    f.export_record(Client(), f.record(f.context({}), 'custom/model', None, 1, 2, 'error'))
    assert 'model' not in calls[1] and 'cost_details' not in calls[1]
    assert calls[1]['metadata']['actual_model'] == 'custom/model'

@pytest.mark.asyncio
async def test_provider_attempts_concurrent_calls(make_client, monkeypatch):
    f = module()
    records = []
    class Sink:
        def submit(self, item): records.append(item)
    monkeypatch.setenv('AGENT_FINOPS_ENABLED', 'true')
    monkeypatch.setattr(f, 'worker', Sink())
    async def provider(**kw):
        await asyncio.sleep(0)
        if kw['model'] == 'openai/gpt-4o':
            raise RuntimeError('PRIVATE ERROR SECRET')
        return {'id': 'ok', 'usage': {'prompt_tokens': 10, 'completion_tokens': 5}, 'choices': [{'message': {'content': 'PRIVATE RESPONSE'}}]}
    monkeypatch.setattr('app.main.acompletion', provider)
    monkeypatch.setattr('app.main._retry_backoff_seconds', lambda: 0)
    headers = {'x-consumer-service': 'ai-market-studio', 'x-ai-agent-id': 'writer', 'x-ai-run-id': 'same', 'x-request-id': 'repeated'}
    async with make_client() as client:
        responses = await asyncio.gather(*(client.post('/v1/chat/completions', headers=headers, json={'model': 'gpt-4o', 'messages': [{'role': 'user', 'content': 'PRIVATE PROMPT'}]}) for _ in range(2)))
    assert all(r.status_code == 200 for r in responses)
    assert len(records) == 6
    assert len({r['trace_id'] for r in records}) == 1
    assert len({r['call_id'] for r in records}) == 2
    assert len({r['attempt_id'] for r in records}) == 6
    assert sum(r['cost_status'] == 'known' for r in records) == 2
    assert 'PRIVATE' not in json.dumps(records)


def test_worker_outage_and_queue_fail_open():
    f = module()
    worker = f.Worker(lambda: (_ for _ in ()).throw(RuntimeError('backend unavailable')), capacity=1)
    worker.submit({'safe': 1})
    worker.submit({'safe': 2})
    worker.submit({'bad': object()})
    worker.close(.05)
    assert worker.queue.qsize() <= 1


def test_malformed_details_and_safe_request_metadata():
    f = module()
    ctx = f.context({'x-request-id': 'request-1'})
    assert ctx.get('request_id') == 'request-1'
    r = f.record(ctx, 'openai/gpt-4o', {'prompt_tokens': 10, 'completion_tokens': 2, 'prompt_tokens_details': 'SECRET'}, 1, 2, 'success')
    assert r['cost_details'] is None and r['cost_reason'] == 'invalid_usage'
    for malformed in ('', False):
        usage = {'prompt_tokens': 10, 'completion_tokens': 2, 'prompt_tokens_details': {'cached_tokens': malformed}}
        assert f.record(ctx, 'openai/gpt-4o', usage, 1, 2, 'success')['cost_reason'] == 'invalid_usage'
        usage = {'prompt_tokens': 10, 'completion_tokens': 2, 'completion_tokens_details': {'reasoning_tokens': malformed}}
        assert f.record(ctx, 'openai/gpt-4o', usage, 1, 2, 'success')['cost_reason'] == 'invalid_usage'
    assert f.record(ctx, 'openai/gpt-4o', None, 1, 2, 'error')['cost_reason'] == 'missing_usage'


@pytest.mark.asyncio
async def test_guardrail_still_accounts_billed_usage(make_client, monkeypatch):
    f = module()
    records = []
    class Sink:
        def submit(self, item): records.append(item)
    monkeypatch.setenv('AGENT_FINOPS_ENABLED', 'true')
    monkeypatch.setattr(f, 'worker', Sink())
    monkeypatch.setattr('app.main._enforce_enabled', lambda: True)
    monkeypatch.setattr('app.main._response_has_blocked_content', lambda response: True)
    async def provider(**kw):
        return {'usage': {'prompt_tokens': 10, 'completion_tokens': 2}}
    monkeypatch.setattr('app.main.acompletion', provider)
    async with make_client() as client:
        response = await client.post('/v1/chat/completions', headers={'x-consumer-service': 'ai-market-studio'}, json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': 'hello'}]})
    assert response.status_code == 502
    assert len(records) == 1 and records[0]['cost_status'] == 'known'


def test_disabled_stream_and_other_consumers_excluded(monkeypatch):
    f = module()
    h = {'x-consumer-service': 'ai-market-studio'}
    monkeypatch.delenv('AGENT_FINOPS_ENABLED', raising=False)
    assert f.request_context(h, False) is None
    monkeypatch.setenv('AGENT_FINOPS_ENABLED', 'true')
    assert f.request_context(h, True) is None
    assert f.request_context({'x-consumer-service': 'other'}, False) is None


def test_worker_failure_diagnostics_do_not_disclose_exception(caplog):
    f = module()
    worker = f.Worker(lambda: (_ for _ in ()).throw(RuntimeError('PRIVATE CREDENTIAL')), capacity=1)
    worker.close(.2)
    assert 'finops_export_initialization_failed' in caplog.text
    assert 'PRIVATE CREDENTIAL' not in caplog.text


def test_model_and_usage_validation_fail_closed_for_cost():
    f = module()
    ctx = f.context({})
    usage = {'prompt_tokens': 10, 'completion_tokens': 2}
    assert f.record(ctx, 'custom/gpt-4o', usage, 1, 2, 'success')['cost_details'] is None
    for details in ['SECRET', [], 1]:
        assert f.record(ctx, 'openai/gpt-4o', {**usage, 'completion_tokens_details': details}, 1, 2, 'success')['cost_reason'] == 'invalid_usage'
    result = f.record(ctx, 'openai/gpt-4o', usage, 1, 2, 'success')
    assert result['currency'] == 'USD'
    assert result['usage_details']['total_tokens'] == 12


@pytest.mark.asyncio
async def test_provider_error_type_safe_and_run_isolation(make_client, monkeypatch):
    f = module()
    records = []
    class Sink:
        def submit(self, item): records.append(item)
    monkeypatch.setenv('AGENT_FINOPS_ENABLED', 'true')
    monkeypatch.setattr(f, 'worker', Sink())
    monkeypatch.setattr('app.main._retry_backoff_seconds', lambda: 0)
    async def provider(**kw):
        await asyncio.sleep(0)
        raise RuntimeError('PRIVATE EXCEPTION')
    monkeypatch.setattr('app.main.acompletion', provider)
    async with make_client() as client:
        await asyncio.gather(*(client.post('/v1/chat/completions', headers={'x-consumer-service': 'ai-market-studio', 'x-ai-agent-id': 'writer', 'x-ai-run-id': run}, json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': 'PRIVATE PROMPT'}]}) for run in ['run-a', 'run-b']))
    assert {r['run'] for r in records} == {'run-a', 'run-b'}
    assert len({r['trace_id'] for r in records}) == 2
    assert all(r['error_type'] == 'RuntimeError' for r in records)
    assert 'PRIVATE' not in json.dumps(records)
