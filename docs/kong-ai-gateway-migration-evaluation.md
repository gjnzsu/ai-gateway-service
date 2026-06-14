# Kong AI Gateway Migration Evaluation

Phase 4.5 evaluates Kong AI Gateway capabilities without moving existing traffic.

## Current Stable Path

```text
consumer -> ai-gateway-service -> model provider
consumer -> Kong POC -> ai-gateway-service -> model provider
```

The stable Kong POC uses `docker-compose.kong.yml` and `kong/kong.yml`. It forwards existing `/v1`, `/health`, and `/readiness` paths to `ai-gateway-service`.

## Experiment Path

```text
consumer -> Kong AI Proxy experiment -> OpenAI
```

The experiment uses:

- `docker-compose.kong-ai.yml`
- `kong/kong-ai-proxy-experiment.yml`
- Route: `/kong-ai/v1/chat/completions`
- Plugin: `ai-proxy`
- Provider: `openai`
- Model: `gpt-4o-mini`

This path is intentionally separate from the default POC. It is for local validation of Kong AI Proxy behavior and migration fit.

## Migration Boundary

| Capability | Recommended owner now | Reason |
| --- | --- | --- |
| Edge routing | Kong | Standard API gateway concern. |
| Request ID propagation | Kong | Works well at ingress and is already in the POC. |
| Generic rate limiting | Kong | Mature gateway-level traffic control. |
| Auth and consumer identity | Kong, later phase | Good gateway responsibility, but enabling it now would break current consumers. |
| Simple one-route-to-one-model proxying | Kong experiment | Kong AI Proxy can handle this, but parity must be proven first. |
| Model alias catalog | `ai-gateway-service` | Existing consumers depend on service-level aliases. |
| Provider fallback | `ai-gateway-service` | Current logic is model-aware and tied to service reliability metadata. |
| Circuit breaker | `ai-gateway-service` | Current implementation tracks provider model health and half-open probes. |
| Observability ingestion | `ai-gateway-service` | Already integrated with the existing AI observability service. |
| Consumer model policy | `ai-gateway-service` | Current phase is log-only and depends on request context. |
| Cost and usage normalization | `ai-gateway-service` | Needs cross-provider normalization and integration with existing metrics. |

## Production Prerequisites Before Migration

- Verify the target Kong Gateway image includes the required AI plugin version.
- Decide whether the deployment uses OSS Kong Gateway, Kong Gateway Enterprise, or Konnect.
- Replace local environment-secret templating with the production secret mechanism.
- Prove request and response compatibility against current consumers.
- Prove observability parity, including request count, latency, errors, tokens, and cost labels.
- Decide whether Kong AI Proxy should call providers directly or continue forwarding through `ai-gateway-service`.

## Local Experiment

Set an OpenAI key and start the isolated compose file:

```powershell
$env:OPENAI_API_KEY = "sk-..."
docker compose -f docker-compose.kong-ai.yml up
```

Send a chat completion request:

```powershell
curl.exe -X POST http://localhost:8100/kong-ai/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [{"role": "user", "content": "Say hello in 3 words"}]
  }'
```

The model is configured in Kong as `gpt-4o-mini`. Kong AI Proxy rejects a different request model unless dynamic model routing is explicitly configured.

## Decision

Do not migrate existing `ai-market-studio` or platform traffic in Phase 4.5.

Use this experiment to validate whether Kong should own simple AI proxying and edge controls. Keep the gateway service as the system of record for model aliases, reliability, policy, and observability until a later phase proves functional parity.
