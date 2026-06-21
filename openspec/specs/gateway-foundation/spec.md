# gateway-foundation Specification

## Purpose
TBD - created by archiving change stabilize-ai-gateway-foundation. Update Purpose after archive.
## Requirements
### Requirement: Config loads in local and container environments
The gateway SHALL load model configuration from `LITELLM_CONFIG_PATH` when set, otherwise from `/app/config.yaml` when present, otherwise from the repository `config.yaml`.

#### Scenario: Local fallback config is used
- **WHEN** the gateway starts outside the container without `LITELLM_CONFIG_PATH`
- **THEN** it loads the repository `config.yaml`

#### Scenario: Explicit config path is used
- **WHEN** `LITELLM_CONFIG_PATH` points to a config file
- **THEN** the gateway loads that config file

### Requirement: Health endpoint reports process liveness
The gateway SHALL expose `/health` and return `{"status": "ok"}` when the process is running.

#### Scenario: Health request succeeds
- **WHEN** a client requests `GET /health`
- **THEN** the gateway returns HTTP 200 with status `ok`

### Requirement: Readiness reflects required provider configuration
The gateway SHALL expose `/readiness` and return ready only when every required API key environment variable referenced by configured models is present.

#### Scenario: Required keys are present
- **WHEN** all configured provider API key environment variables are set
- **THEN** `GET /readiness` returns HTTP 200 with status `ready`

#### Scenario: Required keys are missing
- **WHEN** one or more configured provider API key environment variables are missing
- **THEN** `GET /readiness` returns HTTP 503 and lists the missing variables

### Requirement: Models endpoint lists configured aliases
The gateway SHALL expose `/v1/models` and return OpenAI-compatible model objects for configured model aliases.

#### Scenario: Models request succeeds
- **WHEN** a client requests `GET /v1/models`
- **THEN** the response contains `gpt-4o`, `gpt-4o-mini`, and `deepseek-chat`

### Requirement: Chat completions forward to resolved provider model
The gateway SHALL expose `/v1/chat/completions`, validate required request fields, resolve configured model aliases to provider-qualified LiteLLM models, and preserve supported pass-through request fields.

#### Scenario: Missing model is rejected
- **WHEN** a client posts a chat completion request without `model`
- **THEN** the gateway returns HTTP 400

#### Scenario: Missing messages are rejected
- **WHEN** a client posts a chat completion request without `messages`
- **THEN** the gateway returns HTTP 400

#### Scenario: Non-streaming request uses resolved model
- **WHEN** a client posts a non-streaming request for `gpt-4o-mini`
- **THEN** LiteLLM is called with `openai/gpt-4o-mini`

#### Scenario: Streaming request passes stream once
- **WHEN** a client posts a streaming request
- **THEN** LiteLLM is called with `stream=True` exactly once and the gateway returns server-sent event chunks ending with `[DONE]`

