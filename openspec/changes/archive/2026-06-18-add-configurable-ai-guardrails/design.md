## Context

`ai-gateway-service` currently evaluates request messages against configured security checks and logs compact metadata. The current mode is non-breaking and log-only. The next step is to use the same boundary to mask PII and block high-confidence prompt or response safety violations.

## Goals / Non-Goals

**Goals:**

- Keep guardrails local to `ai-gateway-service`.
- Support deterministic masking and enforcement with config.
- Avoid logging raw sensitive values.
- Preserve OpenAI-compatible success responses.

**Non-Goals:**

- Do not add external classifier services in this phase.
- Do not change Kong OSS configuration.
- Do not support streaming response mutation in this first pass.

## Decisions

- Reuse `security_checks` config instead of adding a parallel settings tree.
- Treat `log_only` and `audit` as observe-only aliases.
- Treat `mask` as request/response PII redaction without prompt-injection blocking.
- Treat `enforce` as prompt-injection blocking plus response unsafe-output blocking, while still masking PII.
- Return machine-readable OpenAI-style error bodies with `prompt_safety_violation` or `response_safety_violation`.

## Risks / Trade-offs

- Regex false positives can mask benign text -> keep patterns configurable and conservative.
- Streaming response masking is deferred -> document that response guardrails apply to non-streaming responses first.
- Existing config has user edits -> preserve existing `gpt-5.4` and consumer policy changes.
