## Why

The gateway now has a stable foundation and structured request logs. A Kong POC can validate the intended architecture where Kong owns generic API gateway concerns while `ai-gateway-service` continues to own AI-specific model/provider behavior.

## What Changes

- Add an optional local Kong Gateway DB-less POC configuration.
- Route `/v1/*`, `/health`, and `/readiness` through Kong to `ai-gateway-service`.
- Add low-risk Kong plugins for request correlation and local POC rate limiting.
- Document how to run and verify the POC.
- Preserve direct access to `ai-gateway-service` for existing consumers.

## Capabilities

### New Capabilities
- `kong-gateway-poc`: Optional Kong Gateway front door for local/prototype validation.

### Modified Capabilities

## Impact

- Adds `kong/` declarative configuration and a local Docker Compose file.
- Adds tests that validate the Kong POC configuration shape.
- Does not change Kubernetes production manifests.
- Does not require `ai-market-studio` or related services to change base URLs, headers, auth, or request bodies.
