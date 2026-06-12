"""
AI Gateway Service - LiteLLM Proxy Server

A minimal FastAPI server that routes LLM requests through LiteLLM.
Provides OpenAI-compatible endpoints: /v1/chat/completions, /v1/models, /health
"""
import json
import os
import logging
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
        )
        raise HTTPException(status_code=400, detail="messages is required")

    # Pass through extra kwargs (temperature, top_p, etc.)
    extra_kwargs = {k: v for k, v in body.items() if k not in ("model", "messages", "stream")}

    try:
        if stream:
            # Streaming response - LiteLLM returns proper SSE chunks
            response = await acompletion(model=resolved_model, messages=messages, stream=True, **extra_kwargs)
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
            )
            return StreamingResponse(
                _stream_response(response),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            response = await acompletion(model=resolved_model, messages=messages, **extra_kwargs)
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
