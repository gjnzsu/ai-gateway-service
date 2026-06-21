## ADDED Requirements

### Requirement: Observability ingestion is optional
The gateway SHALL send metrics to the observability service only when `OBSERVABILITY_URL` is configured.

#### Scenario: Ingestion disabled by default
- **WHEN** `OBSERVABILITY_URL` is unset
- **THEN** chat completion requests proceed without attempting metric ingestion

#### Scenario: Ingestion enabled by environment
- **WHEN** `OBSERVABILITY_URL` is set
- **THEN** the gateway sends chat completion metrics to `${OBSERVABILITY_URL}/ingest`

### Requirement: Successful LLM calls emit llm_call metrics
The gateway SHALL emit `llm_call` metrics for successful chat completion requests.

#### Scenario: Non-streaming success metric includes token usage
- **WHEN** a non-streaming chat completion succeeds and the provider response includes usage
- **THEN** the metric includes provider, model, prompt tokens, completion tokens, duration, status `success`, and trace ID

#### Scenario: Streaming success metric is emitted without token usage
- **WHEN** a streaming chat completion starts successfully
- **THEN** the metric includes provider, model, zero token counts, duration, status `success`, and trace ID

### Requirement: Failed LLM calls emit error metrics
The gateway SHALL emit `llm_call` metrics for mapped provider or internal chat completion failures when a model is available.

#### Scenario: Provider error metric includes error type
- **WHEN** a provider call fails
- **THEN** the metric includes status `error` and the mapped error type

### Requirement: Ingestion failures do not affect gateway responses
The gateway SHALL fail open when observability ingestion fails.

#### Scenario: Observability service is unavailable
- **WHEN** metric ingestion raises an exception or returns an error
- **THEN** the original chat completion response or mapped error response is preserved

### Requirement: Metrics align with existing observability service schema
The gateway SHALL send payloads compatible with the existing `MetricIngestRequest` and `LLMCallData` schemas.

#### Scenario: Payload shape is compatible
- **WHEN** the gateway sends a metric
- **THEN** the payload includes `service_name`, `metric_type`, `trace_id`, `timestamp`, and `data` with `provider`, `model`, `prompt_tokens`, `completion_tokens`, `duration_seconds`, `status`, and `error_type`
