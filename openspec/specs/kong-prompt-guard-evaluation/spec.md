# kong-prompt-guard-evaluation Specification

## Purpose
TBD - created by archiving change add-kong-prompt-guard-evaluation. Update Purpose after archive.
## Requirements
### Requirement: Default Kong POC remains unchanged

The default Kong POC SHALL NOT enable AI Prompt Guard on the existing `/v1`, `/health`, or `/readiness` routes.

#### Scenario: Default config is loaded

- **WHEN** `kong/kong.yml` is inspected
- **THEN** it SHALL NOT include the `ai-prompt-guard` plugin
- **AND** it SHALL continue forwarding `/v1` to `ai-gateway-service`

### Requirement: Prompt Guard evaluation is isolated

The repository SHALL provide an opt-in Kong Prompt Guard evaluation route that is separate from the default Kong POC.

#### Scenario: Evaluation compose is used

- **WHEN** `docker-compose.kong-guard.yml` is used
- **THEN** Kong SHALL load `kong/kong-prompt-guard-evaluation.yml`
- **AND** the experiment route SHALL use `/kong-guard/v1`
- **AND** the route SHALL forward to `ai-gateway-service`

### Requirement: Prompt Guard does not block in this phase

The Prompt Guard evaluation route SHALL attach `ai-prompt-guard` without deny patterns.

#### Scenario: Prompt Guard config is inspected

- **WHEN** the experiment declarative config is inspected
- **THEN** `ai-prompt-guard` SHALL have a pass-through allow pattern
- **AND** `deny_patterns` SHALL be empty

