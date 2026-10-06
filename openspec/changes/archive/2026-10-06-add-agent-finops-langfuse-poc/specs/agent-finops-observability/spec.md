## ADDED Requirements

### Requirement: Optional pilot instrumentation
The gateway SHALL support explicitly enabled non-streaming chat telemetry for the pilot consumer and SHALL preserve existing consumer behavior and SRE telemetry when disabled. Streaming and embeddings SHALL remain outside this cost experiment.

#### Scenario: Existing consumer without new headers
- **WHEN** an existing consumer calls the gateway with telemetry disabled
- **THEN** its response and existing telemetry behavior remain unchanged

#### Scenario: Streaming request
- **WHEN** a request streams its response
- **THEN** it is excluded from this POC's cost accounting and is not recorded as a measured zero-cost call

### Requirement: Run attribution and unique call identity
The pilot contract SHALL use a stable agent ID and a fresh run ID per workflow execution. All calls within that execution SHALL carry the same run identity. Gateway call and provider attempt identities SHALL be distinct from caller request correlation IDs. Missing or invalid attribution SHALL remain explicitly unattributed without blocking inference.

#### Scenario: Concurrent executions
- **WHEN** two runs of the same agent overlap and each performs several calls
- **THEN** observations belong only to their respective runs and every call and attempt has a unique identity

#### Scenario: Reused request correlation
- **WHEN** several calls share X-Request-ID
- **THEN** they remain separate cost observations under the shared agent run

#### Scenario: Missing run header
- **WHEN** an enabled pilot call lacks a valid run ID
- **THEN** telemetry identifies the call as unattributed and emits a bounded diagnostic

### Requirement: Usage and estimated cost
Telemetry SHALL preserve available provider token details, actual provider/model, attempt timing and outcome, pricing source/version, currency USD, and estimated cost status. Missing usage or pricing SHALL be unknown rather than zero. Totals SHALL sum unique known observation costs and identify incomplete accounting.

#### Scenario: Priced successful response
- **WHEN** a non-streaming provider response has usage and supported verified pricing
- **THEN** its explicit estimated cost matches the configured price calculation and is attributed to the actual selected model

#### Scenario: Unknown usage or pricing
- **WHEN** usage is absent or pricing is unsupported
- **THEN** numeric cost remains unset, the reason is recorded, and the run is identifiable as incompletely accounted

#### Scenario: Retry followed by fallback
- **WHEN** a provider attempt fails and a fallback succeeds
- **THEN** both attempts are distinguishable in the same run and absent failure usage is not fabricated

#### Scenario: Response rejected by guardrails
- **WHEN** a completed provider response is blocked by response safety policy
- **THEN** its available usage and estimated provider cost remain recorded despite the failed gateway outcome

### Requirement: Content-free fail-open export
The gateway SHALL export monitoring records to a separately self-hosted Langfuse backend without prompts, responses, credentials, or raw provider error payloads. Export and initialization failures SHALL preserve inference and SHALL produce diagnostics. Background buffering and shutdown flushing SHALL be bounded.

#### Scenario: Backend unavailable
- **WHEN** Langfuse is unavailable during successful model calls
- **THEN** callers receive normal model responses and export failures are visible through diagnostics

#### Scenario: Payload inspection
- **WHEN** a telemetry record is serialized
- **THEN** it contains attribution and usage metadata without prompt/response content or credentials

### Requirement: Pilot acceptance evidence
The POC SHALL document the tested backend/SDK/model/pricing configuration and verify separate and overlapping market-briefing runs against known gateway call counts and expected price calculations. Mock-based deterministic validation SHALL precede a bounded real-model smoke test. Completion SHALL distinguish recorded run spend from full agent lifecycle or invoice reconciliation.

#### Scenario: Pilot evaluation
- **WHEN** two repeated executions and overlapping executions are inspected in Langfuse
- **THEN** their agent/run attribution, unique call records, known-cost totals, and missing-data indicators reconcile with captured test evidence
