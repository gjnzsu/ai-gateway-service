## Why

The gateway now has a stable foundation, but operators still cannot reliably answer who called which model, how long it took, whether it failed, or how many tokens were used. Adding additive observability now prepares the service for cost tracking, policy, Kong correlation, and production incident response.

## What Changes

- Add request correlation IDs for chat completion requests.
- Accept optional consumer identity from `X-Consumer-Service` without requiring it.
- Emit structured JSON logs for chat completion requests.
- Include model alias, resolved provider model, HTTP status, error type, latency, and token usage when available.
- Preserve existing OpenAI-compatible request and response behavior for current consumers.

## Capabilities

### New Capabilities
- `gateway-observability`: Structured request logging and correlation for AI gateway traffic.

### Modified Capabilities

## Impact

- Affects `app/main.py`, tests, and README observability notes.
- Does not change existing endpoints, model aliases, or required request headers.
- Does not add Kong, metrics export, persistent storage, dashboards, quotas, or billing.
- Current consumers such as `ai-market-studio` continue calling the gateway as before.
