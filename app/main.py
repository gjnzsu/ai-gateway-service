"""
AI Gateway Service - LiteLLM Proxy Server

A minimal FastAPI server that routes LLM requests through LiteLLM.
Provides OpenAI-compatible endpoints: /v1/chat/completions, /v1/models, /health
"""
import asyncio
import copy
import json
import os
import logging
import re
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

import yaml
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import litellm
from litellm import acompletion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def resolve_config_path() -> Path:
    explicit_path = os.environ.get("LITELLM_CONFIG_PATH")
    if explicit_path:
        return Path(explicit_path)

    container_path = Path("/app/config.yaml")
    if container_path.exists():
        return container_path

    return Path(__file__).resolve().parents[1] / "config.yaml"


def _extract_env_var_reference(value):
    if isinstance(value, str) and value.startswith("os.environ/"):
        return value.split("/", 1)[1]
    return None


def _request_id_from(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _consumer_from(request: Request) -> str:
    return request.headers.get("x-consumer-service") or "unknown"


def _consumer_policies():
    return config.get("consumer_policies", {})


def _policy_for_consumer(consumer: str):
    policies = _consumer_policies()
    return policies.get(consumer) or policies.get("default") or {
        "mode": "log_only",
        "allowed_models": available_models,
    }


def _evaluate_consumer_policy(consumer: str, model):
    policy = _policy_for_consumer(consumer)
    allowed_models = policy.get("allowed_models", [])
    allowed = model in allowed_models
    return {
        "mode": "log_only",
        "allowed": allowed,
        "reason": "model_allowed" if allowed else "model_not_allowed",
    }


def _security_checks_config():
    return config.get("security_checks", {})


def _message_text_from(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "\n".join(text_parts)

    return ""


def _chat_message_text(messages):
    text_parts = []
    for message in messages or []:
        if isinstance(message, dict):
            text = _message_text_from(message.get("content"))
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def _evaluate_security_checks(messages):
    security_config = _security_checks_config()
    message_text = _chat_message_text(messages)
    lowered_text = message_text.lower()
    flags = []

    for pattern in security_config.get("prompt_injection_patterns", []):
        if isinstance(pattern, str) and pattern.lower() in lowered_text:
            flags.append("prompt_injection")
            break

    for pattern in security_config.get("sensitive_data_patterns", []):
        try:
            if isinstance(pattern, str) and re.search(pattern, message_text):
                flags.append("sensitive_data")
                break
        except re.error:
            logger.warning("Invalid security sensitive_data pattern ignored: %s", pattern)

    return {
        "mode": security_config.get("mode", "log_only"),
        "allowed": True,
        "reason": "security_signal_detected" if flags else "no_security_signal",
        "flags": flags,
        "action": "none",
    }


def _security_mode() -> str:
    mode = str(_security_checks_config().get("mode", "log_only")).lower().strip()
    if mode == "audit":
        return "log_only"
    if mode in {"log_only", "mask", "enforce"}:
        return mode
    return "log_only"


def _masking_enabled() -> bool:
    return _security_mode() in {"mask", "enforce"}


def _enforce_enabled() -> bool:
    return _security_mode() == "enforce"


def _redact_sensitive_text(text: str) -> tuple[str, bool]:
    redacted = text
    changed = False
    for pattern in _security_checks_config().get("sensitive_data_patterns", []):
        if not isinstance(pattern, str):
            continue
        try:
            next_redacted = re.sub(pattern, "[REDACTED:sensitive_data]", redacted)
        except re.error:
            logger.warning("Invalid security sensitive_data pattern ignored: %s", pattern)
            continue
        if next_redacted != redacted:
            changed = True
            redacted = next_redacted
    return redacted, changed


def _redact_content(content):
    if isinstance(content, str):
        return _redact_sensitive_text(content)
    if isinstance(content, list):
        changed = False
        redacted_parts = []
        for part in content:
            if isinstance(part, dict):
                redacted_part = dict(part)
                if isinstance(redacted_part.get("text"), str):
                    redacted_text, part_changed = _redact_sensitive_text(
                        redacted_part["text"]
                    )
                    redacted_part["text"] = redacted_text
                    changed = changed or part_changed
                redacted_parts.append(redacted_part)
            elif isinstance(part, str):
                redacted_text, part_changed = _redact_sensitive_text(part)
                redacted_parts.append(redacted_text)
                changed = changed or part_changed
            else:
                redacted_parts.append(part)
        return redacted_parts, changed
    return content, False


def _redact_messages(messages):
    redacted_messages = []
    changed = False
    for message in messages or []:
        if not isinstance(message, dict):
            redacted_messages.append(message)
            continue
        redacted_message = dict(message)
        redacted_content, content_changed = _redact_content(
            redacted_message.get("content")
        )
        redacted_message["content"] = redacted_content
        changed = changed or content_changed
        redacted_messages.append(redacted_message)
    return redacted_messages, changed


def _response_as_dict(response):
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    return None


def _response_message_contents(response) -> list[str]:
    response_dict = _response_as_dict(response)
    if not response_dict:
        return []
    contents = []
    for choice in response_dict.get("choices", []) or []:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if isinstance(message, dict):
            text = _message_text_from(message.get("content"))
            if text:
                contents.append(text)
    return contents


def _response_has_blocked_content(response) -> bool:
    combined = "\n".join(_response_message_contents(response)).lower()
    if not combined:
        return False
    for pattern in _security_checks_config().get("response_block_patterns", []):
        if isinstance(pattern, str) and pattern.lower() in combined:
            return True
    return False


def _redact_response(response):
    response_dict = _response_as_dict(response)
    if not response_dict:
        return response, False
    redacted_response = copy.deepcopy(response_dict)
    changed = False
    for choice in redacted_response.get("choices", []) or []:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if isinstance(message, dict):
            redacted_content, content_changed = _redact_content(message.get("content"))
            message["content"] = redacted_content
            changed = changed or content_changed
    return redacted_response, changed


def _safety_error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _reliability_config():
    return config.get("reliability", {})


def _provider_timeout_seconds():
    return float(_reliability_config().get("timeout_seconds", 30))


def _retry_config():
    return _reliability_config().get("retry", {})


def _max_attempts():
    return int(_retry_config().get("max_attempts", 1))


def _retry_backoff_seconds():
    return float(_retry_config().get("backoff_seconds", 0))


def _circuit_config():
    return _reliability_config().get("circuit_breaker", {})


def _circuit_enabled():
    return bool(_circuit_config().get("enabled", False))


def _failure_threshold():
    return int(_circuit_config().get("failure_threshold", 3))


def _circuit_cooldown_seconds():
    return float(_circuit_config().get("cooldown_seconds", 30))


def _fallback_aliases_for(model_alias):
    return _reliability_config().get("fallbacks", {}).get(model_alias, [])


_circuit_breakers = {}


def _circuit_for(resolved_model):
    return _circuit_breakers.setdefault(
        resolved_model,
        {
            "state": "closed",
            "failure_count": 0,
            "opened_at": None,
        },
    )


def _open_circuit(resolved_model, opened_at=None):
    circuit = _circuit_for(resolved_model)
    circuit["state"] = "open"
    circuit["failure_count"] = _failure_threshold()
    circuit["opened_at"] = time.time() if opened_at is None else opened_at


def _can_call_model(resolved_model):
    if not _circuit_enabled():
        return True

    circuit = _circuit_for(resolved_model)
    if circuit["state"] != "open":
        return True

    opened_at = circuit.get("opened_at") or 0
    if time.time() - opened_at >= _circuit_cooldown_seconds():
        circuit["state"] = "half_open"
        return True

    return False


def _record_model_success(resolved_model):
    if not _circuit_enabled():
        return

    circuit = _circuit_for(resolved_model)
    circuit["state"] = "closed"
    circuit["failure_count"] = 0
    circuit["opened_at"] = None


def _record_model_failure(resolved_model):
    if not _circuit_enabled():
        return

    circuit = _circuit_for(resolved_model)
    if circuit["state"] == "half_open":
        _open_circuit(resolved_model)
        return

    circuit["failure_count"] += 1
    if circuit["failure_count"] >= _failure_threshold():
        _open_circuit(resolved_model)


def _candidate_model_aliases(model_alias):
    candidates = [model_alias]
    for fallback_alias in _fallback_aliases_for(model_alias):
        if fallback_alias not in candidates:
            candidates.append(fallback_alias)
    return candidates


async def _call_provider_with_reliability(*, model_alias, messages, stream, extra_kwargs):
    primary_resolved_model = model_alias_to_litellm_model.get(model_alias, model_alias)
    last_error = None
    attempt_count = 0

    for candidate_alias in _candidate_model_aliases(model_alias):
        resolved_model = model_alias_to_litellm_model.get(candidate_alias, candidate_alias)
        if not _can_call_model(resolved_model):
            continue

        for attempt_number in range(_max_attempts()):
            attempt_count += 1
            try:
                response = await asyncio.wait_for(
                    acompletion(
                        model=resolved_model,
                        messages=messages,
                        stream=stream,
                        **extra_kwargs,
                    ),
                    timeout=_provider_timeout_seconds(),
                )
                _record_model_success(resolved_model)
                return response, {
                    "selected_model_alias": candidate_alias,
                    "selected_resolved_model": resolved_model,
                    "fallback_from_model": (
                        primary_resolved_model
                        if resolved_model != primary_resolved_model
                        else None
                    ),
                    "attempt_count": attempt_count,
                    "circuit_state": _circuit_for(resolved_model)["state"]
                    if _circuit_enabled()
                    else "disabled",
                }
            except Exception as exc:
                last_error = exc
                _record_model_failure(resolved_model)
                if attempt_number < _max_attempts() - 1:
                    await asyncio.sleep(_retry_backoff_seconds())

    if last_error:
        raise last_error
    raise RuntimeError("No available provider model candidates")


def _usage_from_response(response):
    usage = None
    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)

    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif not isinstance(usage, dict):
        usage = dict(usage)

    return {
        "prompt_tokens": usage.get("prompt_tokens") or 0,
        "completion_tokens": usage.get("completion_tokens") or 0,
        "total_tokens": usage.get("total_tokens") or 0,
    }


def _provider_and_model_from(resolved_model):
    if isinstance(resolved_model, str) and "/" in resolved_model:
        provider, model = resolved_model.split("/", 1)
        return provider, model
    return "unknown", resolved_model or "unknown"


def _observability_url():
    return os.environ.get("OBSERVABILITY_URL")


def _observability_service_name():
    return os.environ.get("OBSERVABILITY_SERVICE_NAME", "ai-gateway-service")


def _observability_timeout_seconds():
    return float(os.environ.get("OBSERVABILITY_TIMEOUT_SECONDS", "2"))


def _build_llm_call_metric(
    *,
    request_id: str,
    resolved_model,
    started_at: float,
    status: str,
    error_type=None,
    usage=None,
):
    provider, model = _provider_and_model_from(resolved_model)
    usage = usage or {}
    return {
        "service_name": _observability_service_name(),
        "metric_type": "llm_call",
        "trace_id": request_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens") or 0,
            "completion_tokens": usage.get("completion_tokens") or 0,
            "duration_seconds": max(time.perf_counter() - started_at, 0),
            "status": status,
            "error_type": error_type,
        },
    }


async def _post_observability_metric(payload):
    observability_url = _observability_url()
    if not observability_url:
        return

    async with httpx.AsyncClient(timeout=_observability_timeout_seconds()) as client:
        response = await client.post(
            f"{observability_url.rstrip('/')}/ingest",
            json=payload,
        )
        response.raise_for_status()


async def _send_observability_metric(**kwargs):
    if not _observability_url():
        return

    payload = _build_llm_call_metric(**kwargs)
    try:
        await _post_observability_metric(payload)
    except Exception as exc:
        logger.warning("Failed to send observability metric: %s", exc)


def _log_chat_completion(
    *,
    request_id: str,
    consumer: str,
    model,
    resolved_model,
    status_code: int,
    started_at: float,
    error_type=None,
    usage=None,
    policy_decision=None,
    security_decision=None,
    reliability=None,
):
    payload = {
        "event": "chat_completion",
        "request_id": request_id,
        "consumer": consumer,
        "model": model,
        "resolved_model": resolved_model,
        "status_code": status_code,
        "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
        "error_type": error_type,
        "usage": usage,
    }
    if policy_decision:
        payload["policy_mode"] = policy_decision["mode"]
        payload["policy_allowed"] = policy_decision["allowed"]
        payload["policy_reason"] = policy_decision["reason"]
    if security_decision:
        payload["security_mode"] = security_decision["mode"]
        payload["security_allowed"] = security_decision["allowed"]
        payload["security_reason"] = security_decision["reason"]
        payload["security_flags"] = security_decision["flags"]
        payload["security_action"] = security_decision.get("action", "none")
    if reliability:
        payload["reliability"] = reliability
    logger.info(json.dumps(payload, sort_keys=True))


# Load config.yaml
config_path = resolve_config_path()
with open(config_path, encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Build model alias -> litellm model mapping (e.g. deepseek-chat -> deepseek/deepseek-chat)
model_list = config.get("model_list", [])
model_alias_to_litellm_model = {m["model_name"]: m["litellm_params"]["model"] for m in model_list}
available_models = list(model_alias_to_litellm_model.keys())
required_env_vars = sorted(
    {
        env_var
        for model_config in model_list
        for env_var in [
            _extract_env_var_reference(
                model_config.get("litellm_params", {}).get("api_key")
            )
        ]
        if env_var
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"AI Gateway starting with models: {available_models}")
    yield


app = FastAPI(title="AI Gateway", lifespan=lifespan)

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/readiness")
async def readiness():
    missing_env_vars = [
        env_var for env_var in required_env_vars if not os.environ.get(env_var)
    ]
    if missing_env_vars:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "missing_env_vars": missing_env_vars,
            },
        )
    return {"status": "ready"}


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible /v1/models endpoint"""
    return {
        "object": "list",
        "data": [
            {"id": model_name, "object": "model", "created": 1700000000, "owned_by": "ai-gateway"}
            for model_name in available_models
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible /v1/chat/completions endpoint.
    Routes to the appropriate provider based on model name.
    """
    started_at = time.perf_counter()
    request_id = _request_id_from(request)
    consumer = _consumer_from(request)
    body = await request.json()
    model = body.get("model")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    security_decision = _evaluate_security_checks(messages)

    if not model:
        policy_decision = _evaluate_consumer_policy(consumer, None)
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=None,
            resolved_model=None,
            status_code=400,
            started_at=started_at,
            error_type="validation_error",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=400, detail="model is required")

    # Resolve model alias to LiteLLM model name (e.g. deepseek-chat -> deepseek/deepseek-chat)
    resolved_model = model_alias_to_litellm_model.get(model, model)
    policy_decision = _evaluate_consumer_policy(consumer, model)

    if not messages:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=400,
            started_at=started_at,
            error_type="validation_error",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=400, detail="messages is required")

    if _enforce_enabled() and "prompt_injection" in security_decision["flags"]:
        security_decision = {
            **security_decision,
            "allowed": False,
            "action": "blocked",
        }
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=400,
            started_at=started_at,
            error_type="prompt_safety_violation",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        return _safety_error_response(
            400,
            "prompt_safety_violation",
            "Prompt rejected by AI gateway safety policy.",
        )

    provider_messages = messages
    if _masking_enabled():
        provider_messages, messages_redacted = _redact_messages(messages)
        if messages_redacted:
            security_decision = {**security_decision, "action": "masked"}

    # Pass through extra kwargs (temperature, top_p, etc.)
    extra_kwargs = {k: v for k, v in body.items() if k not in ("model", "messages", "stream")}

    try:
        if stream:
            # Streaming response - LiteLLM returns proper SSE chunks
            response, reliability = await _call_provider_with_reliability(
                model_alias=model,
                messages=provider_messages,
                stream=True,
                extra_kwargs=extra_kwargs,
            )
            resolved_model = reliability["selected_resolved_model"]
            await _send_observability_metric(
                request_id=request_id,
                resolved_model=resolved_model,
                started_at=started_at,
                status="success",
            )
            _log_chat_completion(
                request_id=request_id,
                consumer=consumer,
                model=model,
                resolved_model=resolved_model,
                status_code=200,
                started_at=started_at,
                policy_decision=policy_decision,
                security_decision=security_decision,
                reliability=reliability,
            )
            return StreamingResponse(
                _stream_response(response),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            response, reliability = await _call_provider_with_reliability(
                model_alias=model,
                messages=provider_messages,
                stream=False,
                extra_kwargs=extra_kwargs,
            )
            resolved_model = reliability["selected_resolved_model"]
            if _enforce_enabled() and _response_has_blocked_content(response):
                security_decision = {
                    **security_decision,
                    "allowed": False,
                    "reason": "response_safety_violation",
                    "action": "blocked",
                }
                await _send_observability_metric(
                    request_id=request_id,
                    resolved_model=resolved_model,
                    started_at=started_at,
                    status="error",
                    error_type="response_safety_violation",
                )
                _log_chat_completion(
                    request_id=request_id,
                    consumer=consumer,
                    model=model,
                    resolved_model=resolved_model,
                    status_code=502,
                    started_at=started_at,
                    error_type="response_safety_violation",
                    policy_decision=policy_decision,
                    security_decision=security_decision,
                    reliability=reliability,
                )
                return _safety_error_response(
                    502,
                    "response_safety_violation",
                    "Model response blocked by AI gateway safety policy.",
                )
            if _masking_enabled():
                response, response_redacted = _redact_response(response)
                if response_redacted:
                    security_decision = {**security_decision, "action": "masked"}
            usage = _usage_from_response(response)
            await _send_observability_metric(
                request_id=request_id,
                resolved_model=resolved_model,
                started_at=started_at,
                status="success",
                usage=usage,
            )
            _log_chat_completion(
                request_id=request_id,
                consumer=consumer,
                model=model,
                resolved_model=resolved_model,
                status_code=200,
                started_at=started_at,
                usage=usage,
                policy_decision=policy_decision,
                security_decision=security_decision,
                reliability=reliability,
            )
            return response

    except litellm.exceptions.BadRequestError as e:
        await _send_observability_metric(
            request_id=request_id,
            resolved_model=resolved_model,
            started_at=started_at,
            status="error",
            error_type="bad_request",
        )
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=400,
            started_at=started_at,
            error_type="bad_request",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=400, detail=str(e))
    except litellm.exceptions.AuthenticationError as e:
        await _send_observability_metric(
            request_id=request_id,
            resolved_model=resolved_model,
            started_at=started_at,
            status="error",
            error_type="authentication_error",
        )
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=401,
            started_at=started_at,
            error_type="authentication_error",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=401, detail=str(e))
    except litellm.exceptions.RateLimitError as e:
        await _send_observability_metric(
            request_id=request_id,
            resolved_model=resolved_model,
            started_at=started_at,
            status="error",
            error_type="rate_limit",
        )
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=429,
            started_at=started_at,
            error_type="rate_limit",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=429, detail=str(e))
    except litellm.exceptions.APIError as e:
        await _send_observability_metric(
            request_id=request_id,
            resolved_model=resolved_model,
            started_at=started_at,
            status="error",
            error_type="api_error",
        )
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=500,
            started_at=started_at,
            error_type="api_error",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        await _send_observability_metric(
            request_id=request_id,
            resolved_model=resolved_model,
            started_at=started_at,
            status="error",
            error_type="internal_error",
        )
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=500,
            started_at=started_at,
            error_type="internal_error",
            policy_decision=policy_decision,
            security_decision=security_decision,
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


async def _stream_response(response):
    """Yield SSE chunks from a streaming LiteLLM response"""
    async for chunk in response:
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
