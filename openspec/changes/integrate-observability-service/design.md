## Context

`ai-sre-observability` exposes `POST /ingest` and converts `llm_call` payloads into Prometheus metrics such as `llm_requests_total`, `llm_tokens_total`, `llm_request_duration_seconds`, `llm_errors_total`, and cost counters. Prometheus scrapes the observability service, and Grafana dashboards already query those aggregated metrics.

`ai-gateway-service` already has request IDs, consumer labels, resolved model metadata, latency, status, and usage extraction. Phase 1.5 connects that data to the existing ingestion endpoint.

## Goals / Non-Goals

**Goals:**
- Send `llm_call` metrics to `ai-sre-observability` when `OBSERVABILITY_URL` is configured.
- Do nothing when `OBSERVABILITY_URL` is unset.
- Use `request_id` as `trace_id`.
- Map resolved model names such as `openai/gpt-4o-mini` into provider `openai` and model `gpt-4o-mini`.
- Send prompt and completion tokens when usage is available; default missing token counts to zero.
- Fail open on ingestion errors and log the failure.
- Keep existing response behavior unchanged.

**Non-Goals:**
- Add a native `/metrics` endpoint to the gateway.
- Add OpenTelemetry.
- Add Loki, Promtail, or a Grafana log backend.
- Store metrics locally.
- Retry/batch observability ingestion.
- Block or slow user responses when observability is unavailable.

## Decisions

1. **Direct async POST instead of SDK dependency.**
   - The gateway already depends on `httpx`.
   - Avoiding a local sibling-repo SDK dependency keeps Docker and deployment simpler.
   - Later, if the SDK is packaged and versioned, we can replace the local sender.

2. **Fire-and-observe inline but fail open.**
   - The first implementation awaits one short-timeout POST after the provider call.
   - Any failure is logged and swallowed.
   - This avoids background task lifecycle complexity while keeping user-facing behavior safe.

3. **Environment-based configuration.**
   - `OBSERVABILITY_URL` enables ingestion.
   - `OBSERVABILITY_SERVICE_NAME` defaults to `ai-gateway-service`.
   - `OBSERVABILITY_TIMEOUT_SECONDS` defaults to `2`.

4. **Existing Grafana dashboards are reused for metrics.**
   - The current LLM Cost & Usage dashboard should show gateway data once ingestion is active.
   - A log dashboard is deferred unless a log backend such as Loki is present.

## Risks / Trade-offs

- [Risk] Inline ingestion adds a small amount of latency. -> Mitigation: short timeout and fail-open behavior; batching can be a later optimization.
- [Risk] Streaming responses do not have final token usage. -> Mitigation: send zero tokens for streaming metadata in this phase; richer streaming usage can be added later.
- [Risk] Provider/model parsing may be incomplete for unusual names. -> Mitigation: split on the first `/`; otherwise use provider `unknown`.
