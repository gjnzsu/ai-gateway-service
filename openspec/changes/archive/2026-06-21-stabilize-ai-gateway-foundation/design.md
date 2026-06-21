## Context

The service is a compact FastAPI/LiteLLM gateway with OpenAI-compatible endpoints. The current implementation works as a skeleton, but local imports depend on a container-only config path, readiness always reports success, tests require an external server on `localhost:4000`, and streaming forwards duplicate `stream` arguments to LiteLLM.

Phase 0 prepares the gateway for later production features and the Kong POC by making the existing behavior reliable, testable, and explicit.

## Goals / Non-Goals

**Goals:**
- Keep the public endpoint surface unchanged.
- Make local and container config loading deterministic.
- Make readiness report whether required API key environment variables are present for configured providers.
- Fix streaming request forwarding.
- Make tests run in-process without a live server or real provider credentials.
- Document local development and secret handling accurately.

**Non-Goals:**
- Add Kong Gateway configuration.
- Add cost tracking, quotas, fallback, circuit breakers, RAG, or provider health checks.
- Change provider/model aliases.
- Validate real downstream provider connectivity from readiness.

## Decisions

1. **Resolve config path with a local fallback.**
   - The service will honor `LITELLM_CONFIG_PATH` first.
   - If unset, it will use `/app/config.yaml` when present, otherwise the repository `config.yaml`.
   - Alternative considered: require `LITELLM_CONFIG_PATH` for local dev. That is explicit but brittle and easy to forget.

2. **Readiness checks configuration and required environment variables.**
   - The endpoint will return `200` when all API key env vars referenced by configured models are set.
   - It will return `503` with missing variable names when required env vars are absent.
   - Alternative considered: call each provider from readiness. That is expensive, can consume quota, and can make Kubernetes readiness depend on third-party latency.

3. **In-process tests use ASGI transport.**
   - Tests will import the FastAPI app and exercise endpoints directly through `httpx.ASGITransport`.
   - Provider calls will be monkeypatched at the gateway boundary where needed.
   - Alternative considered: start Uvicorn for tests. That is slower and more fragile for unit-level behavior.

4. **Request pass-through excludes gateway-owned fields.**
   - `model`, `messages`, and `stream` are handled by the gateway and excluded from extra LiteLLM kwargs.
   - This prevents duplicate `stream` arguments while preserving pass-through fields such as `temperature`, `top_p`, and `max_tokens`.

## Risks / Trade-offs

- [Risk] Readiness can pass even if provider credentials are invalid. -> Mitigation: this phase only guarantees configuration readiness; provider connectivity belongs in a later reliability/observability phase.
- [Risk] Import-time config loading still makes tests sensitive to environment state. -> Mitigation: tests set `LITELLM_CONFIG_PATH` before importing the app.
- [Risk] README cleanup could drift from deployment reality. -> Mitigation: keep changes focused on commands and behavior verified by the code.
