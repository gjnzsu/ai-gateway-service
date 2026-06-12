## 1. Compatibility Tests

- [x] 1.1 Add a no-header chat completion compatibility test for existing consumers
- [x] 1.2 Add tests proving optional request ID and consumer headers do not affect response shape

## 2. Structured Logging

- [x] 2.1 Add failing tests for successful request structured log fields
- [x] 2.2 Add failing tests for generated request IDs and default consumer identity
- [x] 2.3 Add failing tests for error structured log fields
- [x] 2.4 Implement structured JSON log helper
- [x] 2.5 Implement request ID and consumer extraction
- [x] 2.6 Emit logs for successful non-streaming, streaming, validation, and LiteLLM error paths

## 3. Documentation And Verification

- [x] 3.1 Update README with observability behavior and compatibility note
- [x] 3.2 Run the full test suite and strict OpenSpec validation
