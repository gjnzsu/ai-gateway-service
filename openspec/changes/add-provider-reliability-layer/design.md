## Context

`ai-gateway-service` routes model aliases to provider-qualified LiteLLM models. Provider failures currently pass through the request path directly. A production gateway should bound latency, retry transient failures, avoid repeatedly calling unhealthy providers, and optionally fallback to a cheaper or alternate model.

This phase implements a minimal reliability layer inside the gateway because provider/model health is AI-specific. Kong can protect the gateway service, but it does not know whether `openai/gpt-4o-mini` or `deepseek/deepseek-chat` is unhealthy.

## Goals / Non-Goals

**Goals:**
- Bound provider call latency with `asyncio.wait_for`.
- Retry failed provider calls a configured number of times.
- Fallback by model alias after primary model attempts fail or its circuit is open.
- Track in-memory circuit breaker state per resolved provider model.
- Use passive half-open probing after cooldown.
- Log reliability metadata: selected model, attempt count, fallback source, and circuit state.
- Preserve OpenAI-compatible request and response behavior.

**Non-Goals:**
- Cross-pod shared circuit breaker state.
- Background active health probes.
- Provider-specific health endpoints.
- Persistent failure history.
- Advanced retry classification.
- Mid-stream recovery after chunks have started flowing.
- Kong circuit breaker configuration.

## Decisions

1. **Circuit key is resolved provider model.**
   - Example: `openai/gpt-4o-mini`.
   - This avoids marking all OpenAI traffic unhealthy when only one model route is failing.

2. **Fallback config uses consumer-facing aliases.**
   - Example: `gpt-4o -> gpt-4o-mini`.
   - Operators reason in the same model names consumers use.

3. **Passive half-open probe.**
   - When cooldown expires, the next real request is allowed as a probe.
   - Success closes the circuit; failure opens it again.
   - This avoids background probes that cost provider quota.

4. **Retry is simple and bounded.**
   - `max_attempts` includes the first attempt.
   - Backoff is fixed in this phase.
   - This is intentionally conservative; later phases can add exponential backoff and error classification.

5. **Fallback happens before returning final error.**
   - If the primary model fails or its circuit is open, configured fallback aliases are tried in order.
   - If all candidates fail, the gateway returns the existing mapped error behavior.

## Risks / Trade-offs

- [Risk] In-memory circuit state differs per pod. -> Mitigation: acceptable first phase; cross-pod state can be added only if real traffic proves the need.
- [Risk] Fallback model quality may differ. -> Mitigation: fallback mapping is explicit and visible in logs.
- [Risk] Retrying can increase cost/latency. -> Mitigation: bounded attempts and timeout.
- [Risk] Streaming failures after stream starts cannot fallback cleanly. -> Mitigation: this phase only handles failures before the stream response is returned.
