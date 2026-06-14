# Add Log-Only Security Screening

## Why

The gateway is becoming the central point for AI traffic. Before enforcing security controls, operators need visibility into risky requests such as prompt-injection attempts and accidental sensitive-data submission.

## What Changes

- Add configurable request security screening in log-only mode.
- Detect configured prompt-injection and sensitive-data patterns in chat messages.
- Add security decision fields to structured chat completion logs.
- Preserve existing request and response behavior for all consumers.

## Non-Goals

- Do not block requests in this phase.
- Do not redact or mutate prompts.
- Do not add mandatory auth, JWT, API keys, or Kong consumer mapping.
- Do not store full prompt or response content in logs.

## Impact

Existing consumers, including `ai-market-studio`, continue using the same OpenAI-compatible request shape. Security screening only adds log metadata.
