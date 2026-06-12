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
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


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
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=None,
            resolved_model=None,
            status_code=400,
            started_at=started_at,
            error_type="validation_error",
        )
        raise HTTPException(status_code=400, detail="model is required")

    # Resolve model alias to LiteLLM model name (e.g. deepseek-chat -> deepseek/deepseek-chat)
    resolved_model = model_alias_to_litellm_model.get(model, model)

    if not messages:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=400,
            started_at=started_at,
            error_type="validation_error",
        )
        raise HTTPException(status_code=400, detail="messages is required")

    # Pass through extra kwargs (temperature, top_p, etc.)
    extra_kwargs = {k: v for k, v in body.items() if k not in ("model", "messages", "stream")}

    try:
        if stream:
            # Streaming response - LiteLLM returns proper SSE chunks
            response = await acompletion(model=resolved_model, messages=messages, stream=True, **extra_kwargs)
            _log_chat_completion(
                request_id=request_id,
                consumer=consumer,
                model=model,
                resolved_model=resolved_model,
                status_code=200,
                started_at=started_at,
            )
            return StreamingResponse(
                _stream_response(response),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            response = await acompletion(model=resolved_model, messages=messages, **extra_kwargs)
            _log_chat_completion(
                request_id=request_id,
                consumer=consumer,
                model=model,
                resolved_model=resolved_model,
                status_code=200,
                started_at=started_at,
                usage=_usage_from_response(response),
            )
            return response

    except litellm.exceptions.BadRequestError as e:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=400,
            started_at=started_at,
            error_type="bad_request",
        )
        raise HTTPException(status_code=400, detail=str(e))
    except litellm.exceptions.AuthenticationError as e:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=401,
            started_at=started_at,
            error_type="authentication_error",
        )
        raise HTTPException(status_code=401, detail=str(e))
    except litellm.exceptions.RateLimitError as e:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=429,
            started_at=started_at,
            error_type="rate_limit",
        )
        raise HTTPException(status_code=429, detail=str(e))
    except litellm.exceptions.APIError as e:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=500,
            started_at=started_at,
            error_type="api_error",
        )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        _log_chat_completion(
            request_id=request_id,
            consumer=consumer,
            model=model,
            resolved_model=resolved_model,
            status_code=500,
            started_at=started_at,
            error_type="internal_error",
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
