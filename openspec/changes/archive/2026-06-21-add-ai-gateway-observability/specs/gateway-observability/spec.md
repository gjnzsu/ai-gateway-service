## ADDED Requirements

### Requirement: Chat requests emit structured observability logs
The gateway SHALL emit one structured JSON log event for each `/v1/chat/completions` request.

#### Scenario: Successful request is logged
- **WHEN** a non-streaming chat completion request succeeds
- **THEN** the gateway logs request ID, consumer, model alias, resolved provider model, HTTP status, latency, and token usage when available

#### Scenario: Failed request is logged
- **WHEN** a chat completion request fails with a mapped LiteLLM error or validation error
- **THEN** the gateway logs request ID, consumer, model alias when available, resolved provider model when available, HTTP status, latency, and error type

### Requirement: Request IDs are propagated or generated
The gateway SHALL use `X-Request-ID` when provided and SHALL generate a request ID when it is absent.

#### Scenario: Client request ID is reused
- **WHEN** a client sends `X-Request-ID`
- **THEN** the structured log uses that value as `request_id`

#### Scenario: Missing request ID is generated
- **WHEN** a client does not send `X-Request-ID`
- **THEN** the structured log includes a non-empty generated `request_id`

### Requirement: Consumer identity is optional
The gateway SHALL record `X-Consumer-Service` when provided and SHALL default consumer identity to `unknown` when absent.

#### Scenario: Consumer header is recorded
- **WHEN** a client sends `X-Consumer-Service`
- **THEN** the structured log uses that value as `consumer`

#### Scenario: Consumer header is absent
- **WHEN** a client does not send `X-Consumer-Service`
- **THEN** the request still succeeds and the structured log uses `unknown` as `consumer`

### Requirement: Existing consumers remain compatible
The gateway SHALL NOT require new headers or request fields for existing OpenAI-compatible chat completion calls.

#### Scenario: Existing request shape still works
- **WHEN** a client sends the existing `model` and `messages` request body without observability headers
- **THEN** the gateway returns the upstream response unchanged except for existing FastAPI serialization
