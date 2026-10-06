"""Opt-in, content-free provider attempt accounting."""
import hashlib
import json
import logging
import os
import queue
import re
import secrets
import threading
from pathlib import Path

SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
PRICES = json.loads(Path(__file__).with_name('finops_prices.json').read_text())
logger = logging.getLogger(__name__)


def context(headers):
    values = {k: headers.get('x-ai-' + k + '-id') for k in ('agent', 'run')}
    valid = all(isinstance(v, str) and SAFE.fullmatch(v) for v in values.values())
    call_id = secrets.token_hex(16)
    result = {'application': 'ai-market-studio', 'call_id': call_id, 'attribution_status': 'attributed' if valid else 'unattributed', 'attribution_reason': 'valid' if valid else 'missing_or_invalid_agent_run'}
    if valid:
        result.update(values)
    else:
        logger.warning('finops_unattributed_call')
    request_id = headers.get('x-request-id')
    if isinstance(request_id, str) and SAFE.fullmatch(request_id):
        result['request_id'] = request_id
    step = headers.get('x-ai-step-id')
    if isinstance(step, str) and SAFE.fullmatch(step):
        result['step'] = step
    result['trace_id'] = hashlib.sha256(json.dumps(['ai-market-studio', values['agent'], values['run']] if valid else [call_id], separators=(',', ':')).encode()).hexdigest()[:32]
    return result


def _count(value):
    return type(value) is int and value >= 0


def record(ctx, model, usage, started, ended, status, error_type=None):
    result = {**ctx, 'attempt_id': secrets.token_hex(8), 'actual_model': model, 'provider': model.split('/')[0] if '/' in model else 'unknown', 'status': status, 'provider_started_at': started, 'provider_ended_at': ended, 'duration_ms': max(0, (ended-started)*1000), 'price_version': PRICES['version'], 'price_source': PRICES['source'], 'cost_status': 'unknown', 'usage_details': None, 'cost_details': None}
    result.update(currency='USD', cost_reason='missing_usage', error_type=error_type)
    if hasattr(usage, 'model_dump'):
        usage = usage.model_dump()
    if not isinstance(usage, dict):
        return result
    result['cost_reason'] = 'invalid_usage'
    inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
    input_details = usage.get('prompt_tokens_details')
    output_details = usage.get('completion_tokens_details')
    if input_details is not None and not isinstance(input_details, dict):
        return result
    if output_details is not None and not isinstance(output_details, dict):
        return result
    cached = (input_details or {}).get('cached_tokens', 0)
    reasoning = (output_details or {}).get('reasoning_tokens', 0)
    cached = 0 if cached is None else cached
    reasoning = 0 if reasoning is None else reasoning
    if not all(_count(x) for x in (inp, out, cached, reasoning)) or cached > inp or reasoning > out:
        return result
    result['usage_details'] = {'input': inp-cached, 'cache_read_input_tokens': cached, 'output': out, 'input_cached_tokens': cached, 'output_reasoning_tokens': reasoning, 'total_tokens': inp+out}
    result['token_details'] = {'prompt_tokens': inp, 'completion_tokens': out, 'cached_tokens': cached, 'reasoning_tokens': reasoning}
    result['cost_reason'] = 'unsupported_pricing'
    normalized = model.removeprefix('openai/')
    rates = PRICES['models'].get(normalized)
    if rates is None:
        return result
    im, om = (2, 1.5) if normalized == 'gpt-5.4' and inp > 272000 else (1, 1)
    input_cost = ((inp-cached)*rates['input'] + cached*rates['cached'])*im/1000000
    output_cost = out*rates['output']*om/1000000
    result.update(price_source=rates['source'], cost_status='known', cost_reason='priced', cost_details={'input': input_cost, 'output': output_cost, 'total': input_cost+output_cost}, model=normalized)
    return result


def export_record(client, item):
    obs = client.start_observation(as_type='generation', trace_context={'trace_id': item['trace_id']}, name='gateway-provider-attempt')
    metadata = {k: v for k, v in item.items() if k not in ('cost_details', 'usage_details', 'model')}
    kwargs = {'metadata': metadata}
    if item['usage_details'] is not None:
        # Reasoning is already included in output; do not double-count it.
        kwargs['usage_details'] = {k: item['usage_details'][k] for k in ('input', 'cache_read_input_tokens', 'output')}
    if item['cost_status'] == 'known':
        kwargs.update(model=item['model'], cost_details=item['cost_details'])
    obs.update(**kwargs)
    obs.end()


class Worker:
    def __init__(self, factory, capacity=256):
        self.queue = queue.Queue(maxsize=capacity)
        self.factory = factory
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name='finops-export')
        self.thread.start()

    def submit(self, item):
        if self.stopped.is_set():
            logger.warning('finops_export_worker_stopped')
            return
        try:
            self.queue.put_nowait(json.loads(json.dumps(item, allow_nan=False)))
        except Exception:
            logger.warning('finops_export_dropped')

    def _run(self):
        try:
            client = self.factory()
        except Exception:
            self.stopped.set()
            logger.warning('finops_export_initialization_failed')
            return
        while not self.stopped.is_set() or not self.queue.empty():
            try:
                item = self.queue.get(timeout=.05)
            except queue.Empty:
                continue
            try:
                export_record(client, item)
            except Exception:
                logger.warning('finops_export_failed')
            finally:
                self.queue.task_done()
        try:
            client.flush()
            client.shutdown()
        except Exception:
            logger.warning('finops_export_shutdown_failed')

    def close(self, timeout=1):
        self.stopped.set()
        self.thread.join(timeout=max(0, timeout))
        if self.thread.is_alive():
            logger.warning('finops_export_shutdown_timeout')


worker = None


def initialize():
    global worker
    if os.getenv('AGENT_FINOPS_ENABLED', '').lower() != 'true':
        return
    try:
        # Import and SDK initialization run off the inference/startup thread.
        def factory():
            from langfuse import Langfuse
            return Langfuse(base_url=os.environ['LANGFUSE_BASE_URL'], public_key=os.environ['LANGFUSE_PUBLIC_KEY'], secret_key=os.environ['LANGFUSE_SECRET_KEY'])
        worker = Worker(factory)
    except Exception:
        worker = None
        logger.warning('finops_export_initialization_failed')


def request_context(headers, stream):
    try:
        if os.getenv('AGENT_FINOPS_ENABLED', '').lower() == 'true' and headers.get('x-consumer-service') == 'ai-market-studio' and not stream:
            return context(headers)
    except Exception:
        logger.warning('finops_attribution_failed')
    return None


def capture(ctx, model, response, started, ended, status, error_type=None):
    if ctx is None or worker is None:
        return
    try:
        usage = response.get('usage') if isinstance(response, dict) else getattr(response, 'usage', None)
        worker.submit(record(ctx, model, usage, started, ended, status, error_type))
    except Exception:
        logger.warning('finops_capture_failed')


def shutdown():
    global worker
    if worker is not None:
        try:
            worker.close()
        except Exception:
            pass
        worker = None
