## Why

The gateway now centralizes AI traffic, observability, Kong POC routing, and log-only consumer policy. The next production requirement is resilience: provider failures should not repeatedly degrade the gateway or every caller.

## What Changes

- Add configurable timeout for provider calls.
- Add retry with bounded attempts and short backoff.
- Add fallback routing from one model alias to another.
- Add in-memory circuit breaker state per resolved provider model.
- Add passive half-open probing after cooldown.
- Add reliability metadata to structured logs.

## Capabilities

### New Capabilities
- `provider-reliability`: Timeout, retry, fallback, and circuit breaker behavior for provider model calls.

### Modified Capabilities

## Impact

- Affects `config.yaml`, `app/main.py`, tests, and README.
- Preserves existing request/response shape.
- Does not add persistent circuit state, background probes, cross-pod coordination, or enforcement changes.
- Keeps streaming support limited to provider-call setup; mid-stream provider failures are out of scope for this phase.
