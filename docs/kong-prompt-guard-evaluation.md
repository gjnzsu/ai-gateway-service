# Kong Prompt Guard Evaluation

Phase 6 starts moving AI-specific gateway behavior toward Kong without changing existing traffic.

## Stable Path

```text
consumer -> Kong /v1 -> ai-gateway-service -> provider
```

The stable path still uses `docker-compose.kong.yml` and `kong/kong.yml`. It does not enable AI Prompt Guard.

## Experiment Path

```text
consumer -> Kong /kong-guard/v1 -> ai-prompt-guard pass-through -> ai-gateway-service -> provider
```

The experiment uses:

- `docker-compose.kong-guard.yml`
- `kong/kong-prompt-guard-evaluation.yml`
- Route: `/kong-guard/v1`
- Plugin: `ai-prompt-guard`

## Why Pass-Through

Kong AI Prompt Guard is an allow/block plugin. This phase is log/eval-only, so the active experiment route does not configure deny patterns:

```yaml
allow_patterns:
  - "(?s).*"
deny_patterns: []
```

This validates that Kong can load the plugin, attach it to an isolated route, parse compatible chat traffic, and forward to `ai-gateway-service` without introducing blocking behavior.

`ai-gateway-service.security_checks` remains the source of normalized security signal logs in this phase.

## Local Run

```powershell
docker compose -f docker-compose.kong-guard.yml up --build
```

Verify proxy routing:

```powershell
curl.exe http://localhost:8200/kong-guard/v1/models
```

Send a chat completion request:

```powershell
curl.exe -X POST http://localhost:8200/kong-guard/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "X-Consumer-Service: ai-market-studio" `
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Say hello in 3 words"}]
  }'
```

## Migration Decision

Kong can start owning AI-specific edge behavior in this order:

1. Plugin availability and request compatibility on an isolated route.
2. Pass-through prompt guard overhead measurement.
3. Experiment-route blocking with deny patterns.
4. Production-route enforcement only after compatibility and observability parity are proven.

Do not move `ai-market-studio` traffic to Prompt Guard enforcement yet.

## Known Limits

- This phase does not produce Kong-side risk classifications.
- If the local Kong image does not include `ai-prompt-guard`, Kong startup will fail for the experiment compose only.
- Prompt-body parsing can add latency and memory overhead for large requests.
- Raw prompt content must not be added to Kong logs.
