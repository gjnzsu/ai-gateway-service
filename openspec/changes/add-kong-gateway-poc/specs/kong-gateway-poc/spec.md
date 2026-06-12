## ADDED Requirements

### Requirement: Kong POC is optional and non-breaking
The Kong POC SHALL be opt-in and SHALL NOT change the existing direct `ai-gateway-service` endpoint behavior.

#### Scenario: Direct gateway remains available
- **WHEN** developers run the service without the Kong POC
- **THEN** the gateway remains available on `localhost:4000` with existing endpoints

#### Scenario: Existing consumers are not forced to migrate
- **WHEN** `ai-market-studio` continues using the existing gateway address
- **THEN** no new headers, auth, request body fields, or base URL changes are required by this phase

### Requirement: Kong routes OpenAI-compatible paths to the gateway
The Kong POC SHALL route `/v1`, `/health`, and `/readiness` requests to `ai-gateway-service` without stripping the request path.

#### Scenario: Chat completion path is preserved
- **WHEN** a client calls Kong at `/v1/chat/completions`
- **THEN** the upstream gateway receives `/v1/chat/completions`

#### Scenario: Health path is preserved
- **WHEN** a client calls Kong at `/health`
- **THEN** the upstream gateway receives `/health`

### Requirement: Kong POC uses DB-less declarative configuration
The Kong POC SHALL run without a Kong database and SHALL load a declarative configuration file.

#### Scenario: Docker Compose starts Kong DB-less
- **WHEN** Docker Compose starts the Kong POC
- **THEN** Kong has `KONG_DATABASE=off` and a `KONG_DECLARATIVE_CONFIG` path

### Requirement: Kong POC includes safe API gateway controls
The Kong POC SHALL demonstrate non-auth API gateway controls that do not break existing request compatibility.

#### Scenario: Request correlation is enabled
- **WHEN** traffic flows through Kong
- **THEN** Kong is configured to support request correlation headers

#### Scenario: Local rate limiting is enabled
- **WHEN** traffic flows through Kong
- **THEN** Kong applies a generous local rate limit suitable for POC validation
