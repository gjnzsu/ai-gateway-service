# Design

## Scope

Phase 6 adds an isolated Kong route:

```text
consumer -> Kong /kong-guard/v1 -> ai-prompt-guard pass-through -> ai-gateway-service
```

The default path remains:

```text
consumer -> Kong /v1 -> ai-gateway-service
```

## Kong Prompt Guard Mode

Kong AI Prompt Guard is primarily an allow/block plugin. Because the requested first step is log/eval-only, this phase does not configure deny patterns. The plugin is attached to the experiment route with a broad allow pattern:

```yaml
allow_patterns:
  - "(?s).*"
deny_patterns: []
```

This validates plugin availability, route attachment, request parsing compatibility, and operational overhead without blocking traffic.

`ai-gateway-service.security_checks` remains the source of normalized security signal logs during this phase.

## Rollout

1. Keep `docker-compose.kong.yml` and `kong/kong.yml` unchanged.
2. Add `docker-compose.kong-guard.yml` and `kong/kong-prompt-guard-evaluation.yml`.
3. Expose the experiment on `localhost:8200`.
4. Forward `/kong-guard/v1/*` to `ai-gateway-service` as `/v1/*`.

## Risks

- If the local Kong image does not include `ai-prompt-guard`, the experiment will fail at Kong startup.
- This phase does not produce Kong-side security detections because no deny rules are active.
- Prompt body parsing can add latency and memory overhead for large prompts.

## Next Decision

After confirming plugin availability and overhead, decide whether to enable deny patterns on only the experiment route, then compare Kong rejection behavior with gateway-service log-only security signals.
