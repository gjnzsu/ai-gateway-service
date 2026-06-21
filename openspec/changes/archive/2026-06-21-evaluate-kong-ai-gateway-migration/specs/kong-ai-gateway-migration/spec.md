# Kong AI Gateway Migration

## ADDED Requirements

### Requirement: Default Kong POC remains non-breaking

The default Kong POC SHALL continue to proxy existing AI gateway service paths to `ai-gateway-service` without requiring new consumer headers, auth credentials, or request shape changes.

#### Scenario: Existing gateway routes are preserved

- **WHEN** the default Kong declarative config is loaded
- **THEN** `/v1`, `/health`, and `/readiness` SHALL route to `http://ai-gateway-service:4000`
- **AND** the `/v1` route SHALL preserve the original path
- **AND** the default config SHALL NOT enable the `ai-proxy` plugin

### Requirement: Kong AI Proxy experiment is isolated

The service SHALL provide an opt-in Kong AI Proxy experiment that is separate from the default Kong POC.

#### Scenario: Experiment uses separate compose and config files

- **WHEN** the Kong AI Proxy experiment is started
- **THEN** it SHALL load a separate declarative config file
- **AND** it SHALL expose an experiment-specific route path
- **AND** it SHALL NOT replace the default `docker-compose.kong.yml` behavior

### Requirement: Migration decision boundary is documented

The repository SHALL document which responsibilities are candidates for Kong migration and which remain in `ai-gateway-service`.

#### Scenario: Operator evaluates migration scope

- **WHEN** an operator reads the migration documentation
- **THEN** they SHALL see Kong-owned candidates
- **AND** they SHALL see service-owned responsibilities
- **AND** they SHALL see risks and prerequisites before production migration
