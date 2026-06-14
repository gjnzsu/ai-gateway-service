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

When `OBSERVABILITY_URL` is configured, the gateway also sends `llm_call` metrics to the existing AI SRE observability service:

```text
ai-gateway-service -> ai-sre-observability /ingest -> /metrics -> Prometheus -> Grafana
```

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OBSERVABILITY_URL` | unset | Enables metric ingestion when set, for example `http://ai-sre-observability.default.svc.cluster.local:8080` |
| `OBSERVABILITY_SERVICE_NAME` | `ai-gateway-service` | Service label used in Prometheus/Grafana metrics |
| `OBSERVABILITY_TIMEOUT_SECONDS` | `2` | Short timeout for fail-open metric ingestion |

Metric ingestion is fail-open. If the observability service is unavailable, chat completion responses are preserved and the gateway logs a warning.

The existing Grafana LLM Cost & Usage dashboard can show gateway request count, latency, token usage, errors, and cost after metrics reach `ai-sre-observability`. A Grafana log dashboard would require a log backend such as Loki; this repo currently emits structured JSON logs but does not provision Loki.

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

## Consumer Model Policy

Consumer model policy is currently **log-only**. The gateway evaluates requested model aliases against configured consumer allowlists and adds the result to structured logs, but it does not block requests.

Policy is keyed by `X-Consumer-Service`. If the header is missing or unknown, the `default` policy is used.

Example:

```yaml
consumer_policies:
  default:
    mode: log_only
    allowed_models:
      - gpt-4o-mini
      - deepseek-chat

  ai-market-studio:
    mode: log_only
    allowed_models:
      - gpt-4o
      - gpt-4o-mini
      - deepseek-chat
```

Structured logs include:

- `policy_mode`
- `policy_allowed`
- `policy_reason`

This phase is intentionally non-breaking. Enforcement, quotas, budgets, auth, and Kong consumer mapping are later phases.

## Security Screening

Security screening is currently **log-only**. The gateway evaluates chat message content against configured prompt-injection phrases and sensitive-data regex patterns, then adds the result to structured logs. It does not block, redact, or mutate requests.

Example configuration:

```yaml
security_checks:
  mode: log_only
  prompt_injection_patterns:
    - ignore previous instructions
    - reveal system prompt
  sensitive_data_patterns:
    - "(?i)api[_ -]?key\\s*[:=]\\s*[^\\s]+"
```

Structured logs include:

- `security_mode`
- `security_allowed`
- `security_reason`
- `security_flags`

Possible flags:

- `prompt_injection`
- `sensitive_data`

The gateway does not add raw prompt or response content to structured logs for this feature. Pattern matching is intentionally conservative and can produce false positives or false negatives. Enforcement, redaction, audit retention, external classifiers, and Kong-based auth are later phases.

## Provider Reliability

Provider reliability is configured in `config.yaml` under `reliability`.

```yaml
reliability:
  timeout_seconds: 30
  retry:
    max_attempts: 2
    backoff_seconds: 0.1
  circuit_breaker:
    enabled: true
    failure_threshold: 2
    cooldown_seconds: 30
  fallbacks:
    gpt-4o:
      - gpt-4o-mini
```

Behavior:

- Provider calls are wrapped with a timeout.
- Failed provider calls are retried with bounded attempts.
- Configured fallback aliases are tried when the primary model fails or its circuit is open.
- Circuit breaker state is tracked per resolved provider model, for example `openai/gpt-4o`.
- After cooldown, the next real request becomes the half-open probe.
- Successful probes close the circuit; failed probes reopen it.

Structured chat completion logs include reliability metadata when available:

```json
{
  "reliability": {
    "selected_model_alias": "gpt-4o-mini",
    "selected_resolved_model": "openai/gpt-4o-mini",
    "fallback_from_model": "openai/gpt-4o",
    "attempt_count": 3,
    "circuit_state": "closed"
  }
}
```

Current limits:

- Circuit breaker state is in-memory per gateway pod.
- There is no cross-pod shared circuit state.
- There are no background health probes.
- Streaming fallback only applies before the stream response starts.
- Retry classification is intentionally simple and bounded.

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

## Kong Gateway POC

The Kong POC is optional and local-only. It does not change the direct gateway path on `localhost:4000`, and it does not require existing consumers to send new headers or auth credentials.

Run the POC:

```powershell
docker compose -f docker-compose.kong.yml up --build
```

Kong listens on `localhost:8000` and forwards to `ai-gateway-service` on `localhost:4000`.

Verify proxy routing:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/readiness
curl.exe http://localhost:8000/v1/models
```

Test a chat completion through Kong:

```powershell
curl.exe -X POST http://localhost:8000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "X-Consumer-Service: ai-market-studio" `
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say hello in 3 words"}]
  }'
```

The POC uses Kong DB-less mode with declarative config in `kong/kong.yml`. It enables request correlation via `X-Request-ID` and a generous local rate limit for demonstration. Auth is intentionally not enabled in this phase because that would be a breaking change for current consumers.

## Kong AI Gateway Experiment

Phase 4.5 adds an isolated Kong AI Proxy experiment. It does not change the default Kong POC and does not affect existing `ai-market-studio` traffic.

Run the experiment:

```powershell
$env:OPENAI_API_KEY = "sk-..."
docker compose -f docker-compose.kong-ai.yml up
```

Kong listens on `localhost:8100` for the experiment route:

```powershell
curl.exe -X POST http://localhost:8100/kong-ai/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [{"role": "user", "content": "Say hello in 3 words"}]
  }'
```

The experiment uses Kong's `ai-proxy` plugin with `route_type: llm/v1/chat`, provider `openai`, and model `gpt-4o-mini`. The API key is injected through `DECK_OPENAI_API_KEY` from the local `OPENAI_API_KEY` environment variable.

Use [docs/kong-ai-gateway-migration-evaluation.md](docs/kong-ai-gateway-migration-evaluation.md) for the migration boundary and decision matrix. Current recommendation: keep model aliases, provider fallback, circuit breaker, observability ingestion, consumer policy, and usage normalization in `ai-gateway-service`; evaluate Kong for edge routing, request IDs, generic rate limiting, auth, and simple one-route-to-one-model AI proxying.

## Kong Prompt Guard Evaluation

Phase 6 adds an isolated Kong AI Prompt Guard evaluation route. The default `/v1` Kong POC remains unchanged.

Run the experiment:

```powershell
docker compose -f docker-compose.kong-guard.yml up --build
```

Kong listens on `localhost:8200` for the experiment route:

```powershell
curl.exe http://localhost:8200/kong-guard/v1/models
```

The experiment attaches `ai-prompt-guard` to `/kong-guard/v1` with a pass-through allow pattern and no deny patterns. This validates plugin availability and request compatibility without blocking traffic. Use [docs/kong-prompt-guard-evaluation.md](docs/kong-prompt-guard-evaluation.md) for details and migration limits.

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
  kong/
    kong.yml
    kong-ai-proxy-experiment.yml
    kong-prompt-guard-evaluation.yml
  openspec/
    changes/
      stabilize-ai-gateway-foundation/
      add-ai-gateway-observability/
      add-kong-gateway-poc/
      integrate-observability-service/
      add-consumer-model-policy/
      add-provider-reliability-layer/
      evaluate-kong-ai-gateway-migration/
      add-log-only-security-screening/
      add-kong-prompt-guard-evaluation/
  config.yaml
  docker-compose.kong.yml
  docker-compose.kong-ai.yml
  docker-compose.kong-guard.yml
  requirements.txt
  Dockerfile
  cloudbuild.yaml
  README.md
```
