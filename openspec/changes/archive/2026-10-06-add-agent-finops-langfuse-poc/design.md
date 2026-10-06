## Context

Kong forwards OpenAI-compatible traffic to the custom FastAPI gateway. The gateway uses LiteLLM SDK 1.52.3, custom reliability logic, and fail-open SRE ingestion. AI Market Studio uses AsyncOpenAI and a bounded non-streaming tool loop. Its current X-Request-ID is shared across loop calls, so it is unsuitable as a unique generation identity. Current usage normalization retains only three totals.

## Goals / Non-Goals

**Goals:** explain estimated USD LLM spend per pilot run and model call; retain accurate attribution under concurrent runs; expose incomplete accounting; keep telemetry independent of inference availability.

**Non-Goals:** streaming accounting, embeddings, prompt capture, agent success evaluation, whole-run lifecycle tracking, tool/infrastructure costs, budget enforcement, invoice reconciliation, gateway replacement, production deployment.

## Decisions

1. Keep the current inference path. Add a dedicated gateway telemetry adapter using Langfuse Python SDK 4.17.0 and matching web/worker backend v4.50.0 images pinned by digest. The source v4.51.0 release did not have a matching published web image during verification, so the latest verified matching pair is used. Explicit instrumentation around the provider attempt boundary gives control over retries and metadata without assuming compatibility of legacy LiteLLM callbacks. An isolated SDK/exporter check verified explicit trace IDs, metadata-only observations, known cost attributes, and omission of automatic-pricing fields for unknown costs. The dependency set is compatible with the installed Pydantic 2 and httpx 0.28.1; no blanket LiteLLM upgrade is required.

2. Use optional `X-AI-Agent-ID` and `X-AI-Run-ID`. The pilot sets agent ID `market-briefing-agent` and generates a fresh UUID run ID at each workflow invocation, including failed invocations. A conversation can contain multiple runs. Propagate immutable per-run context to each LLM request, including injected-client paths. Do not mutate a shared client's default headers. Existing request IDs remain correlation data. The gateway generates a unique call ID for every HTTP call and unique attempt IDs for each actual provider invocation. Optional `X-AI-Step-ID` provides a caller-supplied step label.

3. Enable telemetry only through explicit configuration and pilot consumer selection. Invalid or incomplete attribution produces a diagnostic and an unattributed call record, never a fabricated complete run identity. Existing requests remain accepted. Bound and validate header values; no raw values or credentials in diagnostics. Attributed runs map to deterministic valid Langfuse trace IDs derived from application, agent, and run identity. Each provider attempt is a generation observation with unique identity; metadata preserves gateway call grouping. Run identifiers remain in trace metadata, not Prometheus labels. Validate the selected SDK's explicit trace propagation before implementation.

4. Choose one monetary calculation authority: the gateway cost adapter. Use the actual selected provider/model and original usage details, including cache details where supplied, with a verified price mapping. Export explicit input/output cost and USD total to Langfuse; avoid independently recomputing the same spend in two places. Record pricing source/version and cost status. If pricing is unsupported or usage is absent, omit numeric cost and mark it unknown. A known zero is distinct. Verify explicit unknown-cost behavior in Langfuse before claiming totals: any automatic backend inference must not silently turn unknown records into trusted estimates.

5. Capture response usage immediately after provider completion, before response safety processing, so a billed response rejected by guardrails is still represented. Track actual attempts, selected models, sanitized error class, and timings. Failed attempts lacking usage remain unknown; timeouts cannot establish provider billing. Sum only unique known costs, show missing-usage/pricing counts, and describe totals as estimated observed spend. Disable content capture, including automatic SDK capture and exception payloads containing provider content. Provider timestamps and duration are authoritative metadata; queued Langfuse observation timestamps represent export processing because the public SDK cannot set a past start timestamp.

6. Export in the background with bounded buffering and bounded shutdown flush. Initialization, serialization, queue saturation, or export errors must not fail or hang model calls. Surface diagnostic warnings or counters without high-cardinality labels. The POC accepts possible telemetry loss during crashes; durable delivery is deferred.

7. Self-host Langfuse as a separate isolated local stack using the official deployment topology and pinned compatible versions. Store project credentials outside tracked files. Supporting services are deployment dependencies, not part of agent LLM spend. Kubernetes deployment is a subsequent explicit activity, not implicit in preparing this experiment.

## Risks / Trade-offs

- Unknown provider charges on timeouts → label run totals incomplete; do not promise invoice parity.
- Old LiteLLM dependency and newer model aliases → verify pilot pricing/response support with a controlled compatibility spike.
- SDK/backend schema changes → pin a tested combination and document versions.
- Export loss → bounded diagnostics and reconciliation of expected versus exported calls.
- Concurrent run contamination → per-invocation context and overlapping-run tests.
- Existing Market Studio cost counters → Langfuse and SRE are parallel views; never sum their totals as independent spend.
- Self-hosting complexity → isolated official local stack; evaluate resources before rollout.

## Migration Plan

Resolve compatibility and pricing spikes, provision the isolated backend, add disabled-by-default gateway instrumentation, and coordinate a separate Market Studio attribution change. Enable only the pilot consumer and run a market-briefing scenario twice, then with overlapping runs. Verify model responses during a Langfuse outage. Roll back by disabling telemetry and removing pilot header propagation; provider routing and SRE ingestion continue unchanged.

## Open Questions

- The matching v4.50.0 web/worker pair, digest-pinned supporting services, health endpoint, and live metadata-only ingestion are runtime-verified. The v4.50.0 expanded observation API returned HTTP 502, so local smoke verification uses aggregate ClickHouse queries until an upstream-compatible API version is available.
- Keep Market Studio's configured `gpt-5.4`. Installed LiteLLM 1.52.3 resolves its explicit OpenAI route; pricing comes from a versioned gateway mapping rather than LiteLLM's mutable remote price map. Provider-response compatibility still requires a bounded live smoke test.
- The Market Studio companion header propagation is implemented and tested in its separate worktree. A real provider-backed market-briefing invocation remains a controlled rollout check; the live telemetry smoke used synthetic gateway attempt records and incurred no model cost.

## Compatibility Sources

- Langfuse SDK and cost behavior: https://github.com/langfuse/langfuse-python/blob/v4.17.0/langfuse/_client/client.py and https://langfuse.com/docs/observability/features/token-and-cost-tracking
- Self-host topology and v4 compatibility: https://github.com/langfuse/langfuse/blob/v4.51.0/docker-compose.yml and https://langfuse.com/self-hosting/upgrade/upgrade-guides/upgrade-v3-to-v4
- Pilot pricing: https://developers.openai.com/api/docs/models/gpt-5.4
