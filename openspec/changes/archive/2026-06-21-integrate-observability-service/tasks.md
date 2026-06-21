## 1. Tests

- [x] 1.1 Add tests proving ingestion is skipped when `OBSERVABILITY_URL` is unset
- [x] 1.2 Add tests for successful non-streaming `llm_call` ingestion payloads
- [x] 1.3 Add tests for streaming success metrics with zero token usage
- [x] 1.4 Add tests for provider error metrics
- [x] 1.5 Add tests proving ingestion failures fail open

## 2. Implementation

- [x] 2.1 Add provider/model parsing helper
- [x] 2.2 Add observability payload builder
- [x] 2.3 Add optional async ingestion helper using `httpx`
- [x] 2.4 Call ingestion helper from success, streaming, and error paths
- [x] 2.5 Add deployment env var placeholders for observability integration

## 3. Documentation And Verification

- [x] 3.1 Update README with observability service integration and Grafana dashboard notes
- [x] 3.2 Run full tests and strict OpenSpec validation
- [x] 3.3 Commit Phase 1.5 separately
