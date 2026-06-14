# Design

## Scope

Phase 4.5 adds a comparison and experiment layer, not a traffic migration. The current production-oriented path remains:

```text
consumer -> Kong optional POC -> ai-gateway-service -> model provider
```

The new experiment path is:

```text
consumer -> Kong AI Proxy experiment -> OpenAI-compatible provider
```

## Decisions

### Keep Default Kong POC Unchanged

`kong/kong.yml` remains the default local POC. It proxies `/v1`, `/health`, and `/readiness` to `ai-gateway-service`. This protects existing consumers and keeps the current architecture testable.

### Add Separate AI Proxy Experiment

`kong/kong-ai-proxy-experiment.yml` is intentionally separate from `kong/kong.yml`. It is loaded only by `docker-compose.kong-ai.yml`.

The experiment uses Kong's `ai-proxy` plugin with an OpenAI-compatible chat route. This validates plugin wiring and lets us compare Kong-native AI proxying against the service-owned routing layer.

### Migration Boundary

Good candidates for Kong:

- Request authentication and consumer identity.
- Generic rate limiting and quotas.
- Request IDs and edge-level logging.
- Simple AI Proxy routing where one route maps directly to one provider model.

Keep in `ai-gateway-service` for now:

- Model alias catalog and compatibility for existing OpenAI-style consumers.
- Provider fallback and circuit breaker policy.
- Observability ingestion into the existing AI observability service.
- Consumer model policy evaluation.
- Cost and usage normalization across providers.

## Risks

- Kong AI plugin availability and capabilities vary by Kong Gateway version and plugin packaging.
- Secret injection for declarative AI plugin config must be productionized before real use.
- Moving fallback or policy too early would duplicate logic and create inconsistent behavior.
- Direct provider calls through Kong can bypass gateway-owned observability and policy unless explicitly rebuilt.

## Rollout

1. Keep `docker-compose.kong.yml` as the stable POC.
2. Add `docker-compose.kong-ai.yml` as an opt-in experiment.
3. Evaluate plugin support and behavior locally.
4. Only migrate a responsibility after tests and dashboards prove parity.
