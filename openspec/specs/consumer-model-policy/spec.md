# consumer-model-policy Specification

## Purpose
TBD - created by archiving change add-consumer-model-policy. Update Purpose after archive.
## Requirements
### Requirement: Consumer policies are loaded from config
The gateway SHALL load consumer model policies from `config.yaml`.

#### Scenario: Default policy exists
- **WHEN** config defines `consumer_policies.default`
- **THEN** the gateway uses it for unknown or missing consumers

#### Scenario: Named consumer policy exists
- **WHEN** config defines a named consumer policy
- **THEN** the gateway uses it for matching `X-Consumer-Service` values

### Requirement: Policy evaluation is log-only
The gateway SHALL evaluate policy decisions without blocking requests in this phase.

#### Scenario: Disallowed model still proceeds
- **WHEN** a consumer requests a model outside its allowlist
- **THEN** the gateway logs the request as not allowed by policy and still forwards the request

### Requirement: Policy decisions are logged
The gateway SHALL include policy decision fields in structured chat completion logs.

#### Scenario: Allowed model decision is logged
- **WHEN** a consumer requests an allowed model
- **THEN** the structured log includes `policy_mode`, `policy_allowed=true`, and `policy_reason=model_allowed`

#### Scenario: Disallowed model decision is logged
- **WHEN** a consumer requests a model outside its allowlist
- **THEN** the structured log includes `policy_mode`, `policy_allowed=false`, and `policy_reason=model_not_allowed`

### Requirement: Existing consumers remain compatible
The gateway SHALL NOT require consumers to send new headers or change request shapes for policy evaluation.

#### Scenario: Missing consumer header still works
- **WHEN** a client sends a valid chat completion request without `X-Consumer-Service`
- **THEN** the gateway evaluates the default policy and preserves the normal response

#### Scenario: ai-market-studio still works
- **WHEN** `ai-market-studio` sends existing OpenAI-compatible requests
- **THEN** the gateway preserves the normal response and logs policy decision metadata

