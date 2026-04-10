# AI Gateway Service

**Single entry point for all AI model calls across the platform.**

Instead of each service managing its own API keys and provider SDKs, all LLM requests route through this gateway. One place to manage keys, monitor usage, and swap models — without changing a line of client code.

## What it does

- **Unified OpenAI-compatible API** — existing services call `/v1/chat/completions` just like normal. No SDK migration needed.
- **Multi-provider routing** — automatically routes to OpenAI or DeepSeek based on the model name.
- **Centralized key management** — API keys live in Kubernetes secrets, injected at runtime. No keys in code or config files.
- **Observability-ready** — every request emits structured logs for tracing and metrics (OpenTelemetry hooks available for future dashboards).

## Endpoint

| Environment | URL |
|-------------|-----|
| **GKE (internal)** | `http://ai-gateway.ai-gateway.svc.cluster.local` |
| **Local dev** | `http://localhost:4000` |

> **Note:** The gateway is deployed as a ClusterIP service (internal-only). It is designed to be consumed by other services within the GKE cluster. To expose it externally, change the Service type to `LoadBalancer` in `k8s/service.yaml`.

## Available Models

| Model | Provider | Use case |
|-------|----------|----------|
| `gpt-4o` | OpenAI | High-capability general purpose |
| `gpt-4o-mini` | OpenAI | Fast, cost-effective tasks |
| `deepseek-chat` | DeepSeek | Reasoning-heavy workloads, cost savings |

## Quick Start

### Consumer service migration

To migrate an existing service to use the gateway, update its environment variables:

```bash
# Before (direct to OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# After (via AI Gateway)
OPENAI_BASE_URL=http://ai-gateway.ai-gateway.svc.cluster.local/v1
# API key is managed by the gateway — no need to set it in your service
```

The service keeps calling `https://api.openai.com/v1/chat/completions` in its code — just point `OPENAI_BASE_URL` at the gateway.

### Local development

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export DEEPSEEK_API_KEY=sk-...
python -m app.main
```

### Health checks

```bash
curl http://ai-gateway.ai-gateway.svc.cluster.local/health        # {"status": "ok"}
curl http://ai-gateway.ai-gateway.svc.cluster.local/readiness     # checks downstream connectivity
curl http://ai-gateway.ai-gateway.svc.cluster.local/v1/models     # lists available models
```

### Test a chat completion

```bash
curl -X POST http://ai-gateway.ai-gateway.svc.cluster.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say hello in 3 words"}]
  }'
```

## Deployment

### GKE (already deployed)

```bash
# Verify
kubectl -n ai-gateway get pods
kubectl -n ai-gateway get svc

# Update keys (if needed)
kubectl -n ai-gateway patch secret ai-gateway-secrets \
  --patch '{"stringData":{"OPENAI_API_KEY":"sk-...","DEEPSEEK_API_KEY":"sk-..."}}'

# Rolling restart to pick up new keys
kubectl -n ai-gateway rollout restart deployment/ai-gateway
```

### Redeploy after code changes

```bash
# Build and push via Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# Rolling restart
kubectl -n ai-gateway rollout restart deployment/ai-gateway
kubectl -n ai-gateway rollout status deployment/ai-gateway
```

## Configuration

Model routing is defined in `config.yaml`:

```yaml
model_list:
  - model_name: gpt-4o           # consumer-facing name
    litellm_params:
      model: openai/gpt-4o      # provider-qualified name
      api_key: os.environ/OPENAI_API_KEY
  - model_name: deepseek-chat
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
```

To add a new model, add an entry here and redeploy. No code changes needed.

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  ai-market-studio   │────▶│  AI Gateway      │────▶│  OpenAI     │
│  (consumer service) │     │  ClusterIP:80    │     │             │
└─────────────────────┘     └──────────────────┘     └─────────────┘
                                   │
                                   │ (model routing by name prefix)
                                   ▼
                             ┌─────────────┐
                             │  DeepSeek   │
                             └─────────────┘
```

## File structure

```
ai-gateway-service/
├── app/
│   ├── __init__.py
│   └── main.py           # Custom FastAPI + LiteLLM proxy server
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_routing.py
├── k8s/
│   ├── namespace.yaml     # ai-gateway namespace
│   ├── deployment.yaml    # 2 replicas, resource limits, probes
│   ├── service.yaml      # ClusterIP :80
│   └── secret.yaml        # API keys (injected at runtime)
├── config.yaml            # Model routing config
├── requirements.txt       # Python dependencies
├── Dockerfile
├── cloudbuild.yaml       # GCP Cloud Build CI/CD
└── README.md
```
