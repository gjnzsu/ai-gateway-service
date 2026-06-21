## Context

Phase 0 made the gateway testable and corrected readiness/streaming behavior. The next production need is request-level observability that can support debugging, cost analysis, and later Kong correlation without changing existing client behavior.

The gateway already logs a simple request line, but it is not structured and does not capture request IDs, consumer identity, latency, status, errors, or token usage.

## Goals / Non-Goals

**Goals:**
- Emit one structured JSON log event per chat completion request.
- Generate a request ID when the client does not provide one.
- Reuse a client-provided `X-Request-ID` when present.
- Accept optional `X-Consumer-Service` and default to `unknown` when absent.
- Log usage fields from LiteLLM responses when available.
- Keep existing endpoints, model aliases, and OpenAI-compatible request/response behavior stable.

**Non-Goals:**
- Require auth or new headers from existing consumers.
- Add persistent usage storage, billing, dashboards, Prometheus metrics, or OpenTelemetry spans.
- Log prompt or response bodies.
- Change provider routing or error mapping.
- Add Kong configuration.

## Decisions

1. **Use standard JSON logs first.**
   - The app will emit a JSON string through the existing Python logger.
   - This avoids new dependencies and works with container log collection.
   - Alternative considered: add a structured logging library. That is unnecessary for this first observability slice.

2. **Observe optional headers without enforcing them.**
   - `X-Request-ID` is reused when present.
   - `X-Consumer-Service` is captured when present and defaults to `unknown`.
   - Existing clients remain compatible because no new headers are mandatory.

3. **Log after request completion or failure.**
   - Successful non-streaming requests log after LiteLLM returns.
   - Streaming requests log after the stream has been created, with usage unavailable unless the provider includes it before completion in a later enhancement.
   - Errors log in the same exception branches that currently map LiteLLM errors to HTTP responses.

4. **Do not log prompt or response content.**
   - Phase 1 logs metadata only: request ID, consumer, model, provider model, status, latency, error type, and usage.
   - Prompt/response audit logging belongs in a later governance phase with explicit retention and redaction rules.

## Risks / Trade-offs

- [Risk] Streaming usage is not captured at completion time. -> Mitigation: log streaming metadata now; full streaming usage can be added later if providers expose it consistently.
- [Risk] JSON log strings can drift without tests. -> Mitigation: add tests that parse log payloads and verify required fields.
- [Risk] Logging code could interfere with response compatibility. -> Mitigation: compatibility tests assert no-header requests still return the same response body shape.
