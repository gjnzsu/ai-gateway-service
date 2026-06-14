# Evaluate Kong AI Gateway Migration

## Why

Kong Gateway is already being evaluated as a front-door API gateway for the AI gateway service. Kong OSS also exposes AI Gateway-style plugins, so we need a low-risk experiment to determine which AI gateway responsibilities can move into Kong and which should stay in `ai-gateway-service`.

## What Changes

- Add an isolated Kong AI Proxy experiment configuration.
- Add a separate Docker Compose file for the experiment so the existing Kong POC remains unchanged.
- Document a migration decision matrix for Kong-owned versus service-owned responsibilities.
- Add tests that prove the default Kong POC remains non-breaking and the AI Proxy experiment is opt-in.

## Non-Goals

- Do not route production or existing local traffic through Kong AI Proxy.
- Do not remove model alias routing, observability ingestion, policy logging, fallback, or circuit breaker logic from `ai-gateway-service`.
- Do not introduce mandatory auth or new required headers for existing consumers.

## Impact

Existing consumers, including `ai-market-studio`, continue using the current OpenAI-compatible gateway endpoint. The Kong AI Proxy path is isolated for local evaluation only.
