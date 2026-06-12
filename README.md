# AI Gateway Service

Single entry point for AI model calls across the platform.

Instead of each service managing its own provider SDKs and API keys, services call this gateway through an OpenAI-compatible API. The gateway owns model aliases, provider routing, runtime credentials, and future AI-specific controls such as usage tracking, fallback, and policy.

## What It Does

- OpenAI-compatible API: consumers call `/v1/chat/completions` and `/v1/models`.
- Multi-provider routing: model aliases resolve to provider-qualified LiteLLM model names.
- Centralized key management: provider API keys are injected through runtime environment variables.
- Kubernetes-ready deployment: manifests are provided for an internal ClusterIP service.

## Endpoints

| Environment | URL |
| --- | --- |
| GKE internal | `http://ai-gateway.ai-gateway.svc.cluster.local` |
| Local dev | `http://localhost:4000` |

The Kubernetes service is internal-only by default. To expose it externally, update `k8s/service.yaml` and add the appropriate security controls before deployment.

## Available Models

| Model alias | Provider model | Use case |
| --- | --- | --- |
| `gpt-4o` | `openai/gpt-4o` | High-capability general purpose |
| `gpt-4o-mini` | `openai/gpt-4o-mini` | Fast, cost-effective tasks |
| `deepseek-chat` | `deepseek/deepseek-chat` | Cost-sensitive chat workloads |

## Local Development

```powershell
python -m pip install -r requirements.txt
$env:OPENAI_API_KEY = "sk-..."
$env:DEEPSEEK_API_KEY = "sk-..."
python -m app.main
```

The app loads configuration in this order:

1. `LITELLM_CONFIG_PATH`, when set
2. `/app/config.yaml`, when running in the container
3. local repository `config.yaml`

## Health And Readiness

```powershell
curl.exe http://localhost:4000/health
curl.exe http://localhost:4000/readiness
curl.exe http://localhost:4000/v1/models
```

`/health` checks process liveness and returns `{"status": "ok"}`.

`/readiness` checks whether every API key environment variable referenced by `config.yaml` is set. It does not call downstream model providers.

When keys are missing, readiness returns HTTP 503:

```json
{
  "status": "not_ready",
  "missing_env_vars": ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"]
}
```

## Chat Completion Example

```powershell
curl.exe -X POST http://localhost:4000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say hello in 3 words"}]
  }'
```

## Consumer Service Migration

Existing OpenAI-compatible clients can point their base URL at the gateway:

```text
OPENAI_BASE_URL=http://ai-gateway.ai-gateway.svc.cluster.local/v1
```

Consumer services do not need direct provider API keys when calls go through the gateway.

## Observability

Each `/v1/chat/completions` request emits one structured JSON log event with metadata such as:

- `request_id`
- `consumer`
- `model`
- `resolved_model`
- `status_code`
- `latency_ms`
- `error_type`
- `usage`, when the provider response includes token usage

Clients can send `X-Request-ID` to correlate logs across services. If it is absent, the gateway generates one.

Clients can send `X-Consumer-Service` to identify the calling service. If it is absent, the gateway logs `consumer` as `unknown`.

These headers are optional. Existing consumers, including `ai-market-studio`, can continue using the same OpenAI-compatible request shape.

## Configuration

Model routing is defined in `config.yaml`:

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: deepseek-chat
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
```

To add a model, add a new `model_list` entry and redeploy.

## Kubernetes Deployment

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl -n ai-gateway create secret generic ai-gateway-secrets `
  --from-literal=OPENAI_API_KEY="sk-..." `
  --from-literal=DEEPSEEK_API_KEY="sk-..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Use `k8s/secret.yaml.template` only as a local reference. Do not commit real secrets.

To rotate keys:

```powershell
kubectl -n ai-gateway patch secret ai-gateway-secrets `
  --patch '{"stringData":{"OPENAI_API_KEY":"sk-...","DEEPSEEK_API_KEY":"sk-..."}}'
kubectl -n ai-gateway rollout restart deployment/ai-gateway
```

## Build And Redeploy

```powershell
gcloud builds submit --config=cloudbuild.yaml
kubectl -n ai-gateway rollout restart deployment/ai-gateway
kubectl -n ai-gateway rollout status deployment/ai-gateway
```

## Tests

```powershell
python -m pip install -r requirements.txt
pytest -q
```

The tests run against the FastAPI app in-process. They do not require a local Uvicorn server or real provider credentials.

## Architecture

```text
consumer service
      |
      v
ai-gateway-service
      |
      +-- openai/gpt-4o
      +-- openai/gpt-4o-mini
      +-- deepseek/deepseek-chat
```

Future production phases may place Kong Gateway in front of this service:

```text
consumer service -> Kong Gateway -> ai-gateway-service -> model providers
```

Kong would own generic API gateway concerns such as auth, rate limiting, ingress routing, and request IDs. This service would continue to own AI-specific concerns such as model aliases, provider routing, cost tracking, fallback, and governance.

## File Structure

```text
ai-gateway-service/
  app/
    __init__.py
    main.py
  tests/
    conftest.py
    test_config.py
    test_health.py
    test_routing.py
  k8s/
    namespace.yaml
    deployment.yaml
    service.yaml
    secret.yaml.template
  openspec/
    changes/
      stabilize-ai-gateway-foundation/
  config.yaml
  requirements.txt
  Dockerfile
  cloudbuild.yaml
  README.md
```
