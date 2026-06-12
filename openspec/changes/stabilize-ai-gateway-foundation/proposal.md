## Why

The AI gateway is a good MVP shape, but it currently has foundation issues that make local development, automated testing, streaming, and readiness checks unreliable. Fixing these now gives later observability, Kong, policy, and reliability phases a trustworthy base.

## What Changes

- Load `config.yaml` reliably in both local development and container runtime.
- Make `/readiness` reflect required runtime configuration instead of always returning ready.
- Fix streaming chat completion forwarding so `stream` is not passed twice.
- Replace live `localhost:4000` tests with in-process FastAPI tests.
- Add repository hygiene for Python cache files.
- Clean README encoding and clarify local development, readiness, and secret handling.

## Capabilities

### New Capabilities
- `gateway-foundation`: Stable local/runtime startup, health/readiness semantics, OpenAI-compatible model listing and chat forwarding, streaming support, and testable service behavior.

### Modified Capabilities

## Impact

- Affects `app/main.py`, tests, README, and repository hygiene files.
- Does not change the public API paths.
- Does not add new providers or change configured model aliases.
- Does not introduce Kong yet; it prepares the service for a later Kong POC.
