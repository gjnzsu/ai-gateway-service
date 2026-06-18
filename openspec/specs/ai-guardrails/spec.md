# ai-guardrails Specification

## Purpose
TBD - created by archiving change add-configurable-ai-guardrails. Update Purpose after archive.
## Requirements
### Requirement: Request PII is masked before provider calls
The gateway SHALL mask configured sensitive-data patterns in chat request messages before calling a provider when guardrails run in `mask` or `enforce` mode.

#### Scenario: Mask mode redacts API key
- **WHEN** a chat request contains text matching a configured sensitive-data pattern
- **AND** `security_checks.mode` is `mask`
- **THEN** the provider request contains a redacted value instead of the raw sensitive value

### Requirement: Prompt safety can block provider calls
The gateway SHALL reject prompts matching configured prompt-injection patterns before provider calls when guardrails run in `enforce` mode.

#### Scenario: Enforce mode blocks prompt injection
- **WHEN** a chat request contains a configured prompt-injection phrase
- **AND** `security_checks.mode` is `enforce`
- **THEN** the gateway returns HTTP 400 with error code `prompt_safety_violation`
- **AND** the provider is not called

### Requirement: Response safety protects non-streaming responses
The gateway SHALL apply configured response guardrails to non-streaming provider responses before returning them to consumers.

#### Scenario: Response PII is masked
- **WHEN** a non-streaming provider response contains text matching a configured sensitive-data pattern
- **AND** `security_checks.mode` is `mask`
- **THEN** the gateway returns the response with the sensitive value redacted

#### Scenario: Unsafe response is blocked
- **WHEN** a non-streaming provider response contains a configured response safety phrase
- **AND** `security_checks.mode` is `enforce`
- **THEN** the gateway returns HTTP 502 with error code `response_safety_violation`

### Requirement: Guardrail decisions are logged safely
The gateway SHALL log guardrail decisions without logging raw prompt, response, or sensitive values.

#### Scenario: Guardrail action logged
- **WHEN** a guardrail masks or blocks content
- **THEN** the structured chat completion log includes mode, flags, and action
- **AND** the structured log does not include raw message content

