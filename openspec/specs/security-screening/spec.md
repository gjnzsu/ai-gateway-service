# security-screening Specification

## Purpose
TBD - created by archiving change add-log-only-security-screening. Update Purpose after archive.
## Requirements
### Requirement: Chat completion requests are security screened

The gateway SHALL evaluate chat completion message content against configured security checks before provider calls and apply the configured guardrail mode.

#### Scenario: Clean request

- **WHEN** a chat completion request contains no configured security signals
- **THEN** the gateway SHALL log security metadata with no flags
- **AND** the request SHALL continue to the provider

#### Scenario: Prompt injection signal in log-only mode

- **WHEN** a chat completion request contains a configured prompt-injection phrase
- **AND** `security_checks.mode` is `log_only` or `audit`
- **THEN** the gateway SHALL log a `prompt_injection` security flag
- **AND** the request SHALL continue to the provider

#### Scenario: Prompt injection signal in enforce mode

- **WHEN** a chat completion request contains a configured prompt-injection phrase
- **AND** `security_checks.mode` is `enforce`
- **THEN** the gateway SHALL return a `prompt_safety_violation` error
- **AND** the provider SHALL NOT be called

#### Scenario: Sensitive data signal in mask mode

- **WHEN** a chat completion request contains a configured sensitive-data pattern
- **AND** `security_checks.mode` is `mask` or `enforce`
- **THEN** the gateway SHALL mask the matching value before the provider call

### Requirement: Security screening remains non-breaking

Security screening SHALL NOT require existing consumers to send new headers or change request shape.

#### Scenario: Existing consumer request shape

- **WHEN** `ai-market-studio` sends an existing OpenAI-compatible chat completion request
- **THEN** successful response shape SHALL be preserved
- **AND** the structured log SHALL include security metadata

### Requirement: Prompt content is not logged

The gateway SHALL NOT add full prompt or response content to structured chat completion logs as part of security screening.

#### Scenario: Security signal is logged

- **WHEN** a risky request is logged
- **THEN** the structured log SHALL include security flags
- **AND** it SHALL NOT include raw message content

