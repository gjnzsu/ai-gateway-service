# Add Kong Prompt Guard Evaluation

## Why

Kong should start owning selected AI-specific gateway behavior at the edge, but existing consumers must not be impacted. The first safe step is to validate Kong AI Prompt Guard plugin wiring on an isolated route without enabling blocking behavior.

## What Changes

- Add an opt-in Kong Prompt Guard evaluation compose file.
- Add a separate Kong declarative config with an experiment route.
- Attach `ai-prompt-guard` to the experiment route in pass-through evaluation mode.
- Document that enforcement is not enabled in this phase.
- Add tests proving the default Kong POC remains unchanged.

## Non-Goals

- Do not enable blocking prompt guard rules on the default `/v1` route.
- Do not migrate `ai-market-studio` traffic.
- Do not remove `ai-gateway-service.security_checks`.
- Do not log raw prompt content in Kong.

## Impact

Existing production and local default paths remain unchanged. Operators can run the experiment route to validate Kong AI plugin availability and request compatibility before any enforcement migration.
