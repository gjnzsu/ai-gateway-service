## Why

The gateway now knows consumer identity and sends metrics. The next step is to evaluate which consumers are using which models, before enforcing restrictions. Log-only model policy gives visibility without risking current consumers such as `ai-market-studio`.

## What Changes

- Add optional consumer model policy configuration.
- Evaluate requested model aliases against per-consumer allowlists.
- Default unknown consumers to a safe default policy.
- Add policy decision fields to structured logs.
- Keep policy in `log_only` mode for this phase, so requests are never blocked.

## Capabilities

### New Capabilities
- `consumer-model-policy`: Log-only per-consumer model policy evaluation for chat completions.

### Modified Capabilities

## Impact

- Affects `config.yaml`, `app/main.py`, tests, and README.
- Does not require new headers.
- Does not change endpoints, request bodies, response bodies, or model aliases.
- Does not enforce/block requests in this phase.
