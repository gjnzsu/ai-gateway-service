## Why

The gateway emits structured logs, but the existing `ai-sre-observability` service already provides LLM metrics ingestion, Prometheus aggregation, cost calculation, and Grafana dashboards. The gateway should send LLM call metrics into that existing path before adding policy features that need measurable decisions.

## What Changes

- Add optional metric ingestion from `ai-gateway-service` to `ai-sre-observability` `/ingest`.
- Send LLM call metrics for successful and failed chat completions when ingestion is configured.
- Use `X-Request-ID` / generated request ID as the observability trace ID.
- Keep ingestion fail-open so LLM responses are not impacted if observability is unavailable.
- Document how the gateway integrates with existing Prometheus/Grafana dashboards.

## Capabilities

### New Capabilities
- `observability-service-integration`: Optional LLM metric ingestion into the existing AI SRE observability service.

### Modified Capabilities

## Impact

- Affects `app/main.py`, tests, README, Docker/Kubernetes runtime configuration.
- Uses existing `httpx` dependency.
- Does not add a native `/metrics` endpoint to `ai-gateway-service`.
- Does not require `ai-market-studio` or related consumers to change requests.
