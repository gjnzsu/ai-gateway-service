# Security Screening

## ADDED Requirements

### Requirement: Chat completion requests are security screened

The gateway SHALL evaluate chat completion message content against configured security checks before provider calls.

#### Scenario: Clean request

- **WHEN** a chat completion request contains no configured security signals
- **THEN** the gateway SHALL log security metadata with no flags
- **AND** the request SHALL continue to the provider

#### Scenario: Prompt injection signal

- **WHEN** a chat completion request contains a configured prompt-injection phrase
- **THEN** the gateway SHALL log a `prompt_injection` security flag
- **AND** the request SHALL continue to the provider

#### Scenario: Sensitive data signal

- **WHEN** a chat completion request contains a configured sensitive-data pattern
- **THEN** the gateway SHALL log a `sensitive_data` security flag
- **AND** the request SHALL continue to the provider

### Requirement: Security screening remains non-breaking

Security screening SHALL NOT require existing consumers to send new headers or change request shape.

#### Scenario: Existing consumer request shape

- **WHEN** `ai-market-studio` sends an existing OpenAI-compatible chat completion request
- **THEN** the response shape SHALL be preserved
- **AND** the structured log SHALL include security metadata

### Requirement: Prompt content is not logged

The gateway SHALL NOT add full prompt or response content to structured chat completion logs as part of security screening.

#### Scenario: Security signal is logged

- **WHEN** a risky request is logged
- **THEN** the structured log SHALL include security flags
- **AND** it SHALL NOT include raw message content
