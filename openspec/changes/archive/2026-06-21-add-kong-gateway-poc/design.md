## Context

Kong should be evaluated as an API gateway layer in front of the existing AI gateway, not as an immediate replacement. The safest first step is a local DB-less POC using declarative configuration, because it avoids a database dependency and keeps all POC behavior in source-controlled files.

Kong documentation describes DB-less mode as using in-memory entities loaded from a declarative YAML/JSON configuration file. Declarative configuration version `3.0` is the current format for recent route path behavior.

## Goals / Non-Goals

**Goals:**
- Provide a local Kong POC that can run with Docker Compose.
- Route traffic from Kong port `8000` to `ai-gateway-service` port `4000`.
- Keep `/v1/models`, `/v1/chat/completions`, `/health`, and `/readiness` paths unchanged when accessed through Kong.
- Add correlation-friendly request ID behavior at the Kong layer.
- Add a conservative local rate limit plugin for POC demonstration only.
- Document that the POC is optional and non-breaking.

**Non-Goals:**
- Deploy Kong to GKE.
- Add mandatory auth, JWT, OIDC, API keys, or consumer enforcement.
- Replace the FastAPI/LiteLLM gateway.
- Enable Kong AI Gateway plugins or Auto-RAG.
- Change `ai-market-studio` configuration.

## Decisions

1. **Use Kong DB-less mode.**
   - `KONG_DATABASE=off` and `KONG_DECLARATIVE_CONFIG=/kong/declarative/kong.yml`.
   - This keeps the POC small and avoids PostgreSQL.
   - Alternative considered: traditional Kong with database. That is better for some production setups but heavier for a POC.

2. **Use a separate `docker-compose.kong.yml`.**
   - The existing direct local development path remains unchanged.
   - Developers opt in by running the Kong compose file.
   - Alternative considered: modify the main Dockerfile or Kubernetes manifests. That would increase risk for current consumers.

3. **Use route path preservation.**
   - Kong will route `/v1`, `/health`, and `/readiness` to the gateway without stripping paths.
   - This preserves OpenAI-compatible paths and health endpoints.

4. **Keep plugins non-enforcing for compatibility-sensitive behavior.**
   - Request correlation and local rate limiting are acceptable for POC.
   - Auth is intentionally excluded from this phase because requiring credentials would be a breaking change.

## Risks / Trade-offs

- [Risk] Rate limiting could surprise local testers. -> Mitigation: document it as POC-only and set a generous local limit.
- [Risk] Docker image tags drift over time. -> Mitigation: use a 3.x Kong image family and keep this as a POC, not a production manifest.
- [Risk] Kong request ID header behavior may differ by plugin/version. -> Mitigation: `ai-gateway-service` already generates request IDs if none are provided.
- [Risk] POC does not prove GKE ingress behavior. -> Mitigation: GKE/Kong Ingress Controller remains a future phase after local validation.
