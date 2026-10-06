## Why

The POC agent owner needs to explain estimated LLM spend per execution and identify contributing calls. Existing gateway token metrics identify applications but do not group model calls into agent runs; AI Market Studio's bounded, non-streaming workflow is the first pilot.

## What Changes

- Add optional agent/run attribution and unique gateway call/attempt identities for non-streaming chat completions.
- Export usage, actual provider/model, estimated monetary cost, timing, and errors to self-hosted Langfuse without recording prompt or response content.
- Preserve detailed provider token usage needed for pricing and explicitly distinguish missing usage or pricing from zero spend.
- Provide an isolated local self-hosted Langfuse experiment and document its dependency, credential, and verification requirements.
- Define the companion AI Market Studio integration: stable agent identity, fresh run identity per workflow invocation, shared across all its LLM calls.
- Preserve existing routing, guardrails, responses, and SRE telemetry. Streaming accounting, embeddings, tool/infrastructure cost, budget enforcement, invoice reconciliation, run lifecycle tracking, and LiteLLM Proxy migration are excluded.

## Capabilities

### New Capabilities

- `agent-finops-observability`: Optional gateway telemetry for attributable non-streaming LLM usage and estimated cost, with an AI Market Studio pilot contract and self-hosted Langfuse validation.

### Modified Capabilities

None. Existing SRE ingestion and streaming requirements remain unchanged.

## Impact

- Gateway: `app/main.py`, a dedicated telemetry module, dependencies, optional environment configuration, tests, and POC documentation/deployment assets.
- Companion repository: AI Market Studio workflow entry and attribution headers require a separate coordinated change; this repository's artifacts define that contract without editing the companion project.
- Runtime: a separately hosted Langfuse backend and its supporting services, with server-side project credentials.
- Existing consumers can omit the new headers and keep Langfuse disabled. This experiment does not verify or alter live deployments.
