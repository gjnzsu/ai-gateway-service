"""
AI Gateway Service - LiteLLM Proxy Server

A minimal FastAPI server that routes LLM requests through LiteLLM.
Provides OpenAI-compatible endpoints: /v1/chat/completions, /v1/models, /health
"""
import os
import yaml
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import litellm
from litellm import acompletion

# Load config.yaml
config_path = os.environ.get("LITELLM_CONFIG_PATH", "/app/config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Build model alias -> litellm model mapping (e.g. deepseek-chat -> deepseek/deepseek-chat)
model_list = config.get("model_list", [])
model_alias_to_litellm_model = {m["model_name"]: m["litellm_params"]["model"] for m in model_list}
available_models = list(model_alias_to_litellm_model.keys())


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
    body = await request.json()
    model = body.get("model")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    if not model:
        raise HTTPException(status_code=400, detail="model is required")
    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    # Resolve model alias to LiteLLM model name (e.g. deepseek-chat -> deepseek/deepseek-chat)
    resolved_model = model_alias_to_litellm_model.get(model, model)

    # Pass through extra kwargs (temperature, top_p, etc.)
    extra_kwargs = {k: v for k, v in body.items() if k not in ("model", "messages")}

    try:
        if stream:
            # Streaming response - LiteLLM returns proper SSE chunks
            response = await acompletion(model=resolved_model, messages=messages, stream=True, **extra_kwargs)
            return StreamingResponse(
                _stream_response(response),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            response = await acompletion(model=resolved_model, messages=messages, **extra_kwargs)
            return response

    except litellm.exceptions.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except litellm.exceptions.AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except litellm.exceptions.RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except litellm.exceptions.APIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
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
